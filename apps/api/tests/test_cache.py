"""Tests for the in-memory TTL cache (app/caching/cache.py)."""

import time

from app.caching.cache import cache_get, cache_set, normalize_key


def test_normalize_key_strips_and_lowercases():
    assert normalize_key("  What Is The Refund Rate?  ") == "what is the refund rate?"


def test_cache_get_miss_returns_none():
    assert cache_get("test-namespace", normalize_key("a question nothing has ever cached")) is None


def test_cache_set_then_get_round_trips():
    key = normalize_key("  What is the return window?  ")
    cache_set("test-namespace", key, {"answer": "30 days"}, ttl_seconds=60)
    assert cache_get("test-namespace", key) == {"answer": "30 days"}


def test_cache_is_namespaced():
    key = normalize_key("same question, different endpoints")
    cache_set("namespace-a", key, "value-a", ttl_seconds=60)
    cache_set("namespace-b", key, "value-b", ttl_seconds=60)
    assert cache_get("namespace-a", key) == "value-a"
    assert cache_get("namespace-b", key) == "value-b"


def test_cache_entry_expires_after_ttl():
    key = normalize_key("this entry should expire almost immediately")
    cache_set("test-namespace", key, "will expire", ttl_seconds=0.05)
    assert cache_get("test-namespace", key) == "will expire"
    time.sleep(0.1)
    assert cache_get("test-namespace", key) is None
