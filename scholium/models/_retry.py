"""One retry policy shared by every HTTP-backed model backend: retry on
connection errors and 429/5xx, exponential backoff, bounded attempts.
"""

from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


def http_retry(max_attempts: int = 4):
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8.0),
        retry=retry_if_exception(_should_retry),
    )
