from __future__ import annotations

import time

import pytest

from scholium.http import DiskCache, TokenBucket


def test_token_bucket_allows_burst_up_to_capacity():
    bucket = TokenBucket(rate_per_second=100.0, burst=3)
    start = time.monotonic()
    for _ in range(3):
        bucket.acquire()
    assert time.monotonic() - start < 0.05  # three tokens available immediately


def test_token_bucket_throttles_beyond_capacity():
    bucket = TokenBucket(rate_per_second=50.0, burst=1)
    bucket.acquire()  # drains the single token
    start = time.monotonic()
    bucket.acquire()  # must wait roughly 1/50s
    assert time.monotonic() - start >= 0.015


def test_token_bucket_rejects_non_positive_rate():
    with pytest.raises(ValueError):
        TokenBucket(rate_per_second=0)


def test_disk_cache_roundtrip(tmp_path):
    cache = DiskCache(tmp_path)
    key = DiskCache.key_for("https://example.org/search", {"q": "diffusion"})
    assert cache.get(key) is None
    cache.set(key, b'{"result": 1}')
    assert cache.get(key) == b'{"result": 1}'


def test_disk_cache_key_for_without_params_is_the_bare_url():
    assert DiskCache.key_for("https://example.org/x") == "https://example.org/x"


def test_disk_cache_different_params_are_different_keys(tmp_path):
    cache = DiskCache(tmp_path)
    k1 = DiskCache.key_for("https://example.org/search", {"q": "a"})
    k2 = DiskCache.key_for("https://example.org/search", {"q": "b"})
    cache.set(k1, b"first")
    cache.set(k2, b"second")
    assert cache.get(k1) == b"first"
    assert cache.get(k2) == b"second"
