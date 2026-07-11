"""Pickle-backed cache for raw yfinance payloads.

The analysis pipeline downloads a bundle of DataFrames (statements, history,
dividends) per ticker. Those don't serialize cleanly as JSON, so this cache
pickles the whole bundle to one file per symbol and honors a TTL based on file
mtime. Iterative single-name research then re-runs instantly instead of
re-hitting Yahoo every time.

Set MULBERRY_DISABLE_CACHE=1 to bypass entirely (used by the test suite).
"""

import os
import pickle
import time
from pathlib import Path
from typing import Optional, Dict, Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RawDataCache:
    """One pickle file per symbol, expired by mtime against a TTL."""

    def __init__(self, cache_dir, ttl_seconds: int):
        self.cache_dir = Path(cache_dir) / "raw"
        self.ttl = ttl_seconds
        self._disabled = os.getenv("MULBERRY_DISABLE_CACHE") == "1"
        if not self._disabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str) -> Path:
        safe = symbol.upper().replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe}.pkl"

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return the cached bundle if present and fresh, else None."""
        if self._disabled:
            return None
        path = self._path(symbol)
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > self.ttl:
            logger.debug(f"Cache expired for {symbol} (age {age:.0f}s > {self.ttl}s)")
            return None
        try:
            with open(path, "rb") as f:
                bundle = pickle.load(f)
            logger.info(f"Cache hit for {symbol} (age {age:.0f}s)")
            return bundle
        except Exception as e:
            logger.warning(f"Failed to read cache for {symbol}: {e}")
            return None

    def set(self, symbol: str, bundle: Dict[str, Any]) -> None:
        if self._disabled:
            return
        path = self._path(symbol)
        try:
            with open(path, "wb") as f:
                pickle.dump(bundle, f)
            logger.debug(f"Cached raw data for {symbol}")
        except Exception as e:
            logger.warning(f"Failed to write cache for {symbol}: {e}")

    def clear(self) -> int:
        """Delete all cached bundles; returns the number removed."""
        if not self.cache_dir.exists():
            return 0
        count = 0
        for path in self.cache_dir.glob("*.pkl"):
            try:
                path.unlink()
                count += 1
            except OSError:
                pass
        return count
