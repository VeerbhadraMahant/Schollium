"""Shared HTTP plumbing for the API clients: a token-bucket rate limiter and an
on-disk response cache keyed by URL, per plan section 5.2 Day 6 to 8. Retries
with backoff on 429 and 5xx are handled by tenacity at the call site.

Model backends (scholium/models/) use plain httpx with their own retry
decorator; caching a generation call would be wrong, since two calls with the
same prompt are not guaranteed to be idempotent the way a search is.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path


class TokenBucket:
    """A simple, thread-safe token bucket. `acquire()` blocks until a token is
    available, which is what turns "rate_per_second" in config into an actual
    pause between requests rather than a number nobody enforces.
    """

    def __init__(self, rate_per_second: float, *, burst: float | None = None) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        self._rate = rate_per_second
        self._capacity = burst if burst is not None else max(1.0, rate_per_second)
        self._tokens = self._capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._updated
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            time.sleep(wait)


class DiskCache:
    """Cache HTTP response bodies on disk, keyed by a hash of the URL (and, if
    given, the request body). Re-running the same search costs nothing.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._root / f"{digest}.json"

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return bytes.fromhex(payload["body_hex"])

    def set(self, key: str, body: bytes) -> None:
        path = self._path(key)
        path.write_text(json.dumps({"key": key, "body_hex": body.hex()}), encoding="utf-8")

    @staticmethod
    def key_for(url: str, params: dict | None = None) -> str:
        if not params:
            return url
        return url + "?" + json.dumps(params, sort_keys=True)
