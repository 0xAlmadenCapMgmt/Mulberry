"""Tests for the pickle-backed raw-data cache."""

import time

import pandas as pd
import pytest

from mulberry.cache.raw_cache import RawDataCache


@pytest.fixture
def bundle():
    return {
        "info": {"longName": "Test"},
        "history": pd.DataFrame({"Close": [1.0, 2.0, 3.0]}),
    }


def test_set_then_get_roundtrip(tmp_path, bundle, monkeypatch):
    monkeypatch.delenv("MULBERRY_DISABLE_CACHE", raising=False)
    cache = RawDataCache(tmp_path, ttl_seconds=60)
    assert cache.get("AAPL") is None
    cache.set("AAPL", bundle)
    got = cache.get("AAPL")
    assert got is not None
    assert got["info"]["longName"] == "Test"
    assert list(got["history"]["Close"]) == [1.0, 2.0, 3.0]


def test_expired_entry_returns_none(tmp_path, bundle, monkeypatch):
    monkeypatch.delenv("MULBERRY_DISABLE_CACHE", raising=False)
    cache = RawDataCache(tmp_path, ttl_seconds=0)  # everything is instantly stale
    cache.set("MSFT", bundle)
    time.sleep(0.01)
    assert cache.get("MSFT") is None


def test_disabled_cache_is_noop(tmp_path, bundle, monkeypatch):
    monkeypatch.setenv("MULBERRY_DISABLE_CACHE", "1")
    cache = RawDataCache(tmp_path, ttl_seconds=60)
    cache.set("GOOG", bundle)
    assert cache.get("GOOG") is None


def test_clear_removes_files(tmp_path, bundle, monkeypatch):
    monkeypatch.delenv("MULBERRY_DISABLE_CACHE", raising=False)
    cache = RawDataCache(tmp_path, ttl_seconds=60)
    cache.set("AAPL", bundle)
    cache.set("MSFT", bundle)
    assert cache.clear() == 2
    assert cache.get("AAPL") is None
