"""Shared plumbing every client uses: rate limiting, an on-disk cache keyed by
URL, and retries on 429/5xx. One shape per plan section 5.2 Day 6 to 8: "a
rate limiter, retries with backoff on 429 and 5xx, an on-disk cache keyed by
URL ..., and a cassette test."

Every client accepts an `http_client` so tests can inject a respx-mocked one
(CLAUDE.md: "every function that calls an external API accepts a client
object so tests can inject a recorded one").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from scholium.http import DiskCache, TokenBucket
from scholium.models._retry import http_retry


class ClientSession:
    def __init__(
        self,
        base_url: str,
        *,
        rate_per_second: float = 1.0,
        cache_dir: Path | None = None,
        cache_enabled: bool = True,
        http_client: httpx.Client | None = None,
        max_retries: int = 4,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = http_client or httpx.Client(
            base_url=self.base_url, timeout=timeout, headers=headers or {}
        )
        self._bucket = TokenBucket(rate_per_second)
        self._cache = DiskCache(cache_dir) if cache_enabled and cache_dir is not None else None
        self._max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def _cache_key(self, path: str, params: dict[str, Any] | None) -> str:
        return DiskCache.key_for(f"{self.base_url}{path}", params)

    def _fetch(self, path: str, params: dict[str, Any] | None) -> httpx.Response:
        self._bucket.acquire()

        @http_retry(self._max_retries)
        def _do() -> httpx.Response:
            response = self._client.get(path, params=params)
            response.raise_for_status()
            return response

        return _do()

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        key = self._cache_key(path, params)
        if self._cache is not None:
            cached = self._cache.get(key)
            if cached is not None:
                return json.loads(cached)
        response = self._fetch(path, params)
        if self._cache is not None:
            self._cache.set(key, response.content)
        return response.json()

    def get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        key = self._cache_key(path, params)
        if self._cache is not None:
            cached = self._cache.get(key)
            if cached is not None:
                return cached.decode("utf-8")
        response = self._fetch(path, params)
        if self._cache is not None:
            self._cache.set(key, response.content)
        return response.text
