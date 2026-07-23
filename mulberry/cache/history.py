"""Score-history persistence.

Records one snapshot of the composite and lens scores per symbol per calendar
day, so single-name reports can show how a score has evolved across runs and
screens can be compared over time. Stored as one small JSON file per symbol
under ``.cache/history/``.

Honors ``MULBERRY_DISABLE_CACHE=1`` (used by the test suite) so tests never
write into the project directory unless they opt in explicitly.
"""

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ScoreHistory:
    """One JSON file per symbol; one entry per calendar day (latest wins)."""

    def __init__(self, history_dir=None, disabled: Optional[bool] = None):
        if history_dir is None:
            from ..utils.config import config
            history_dir = config.cache_dir / "history"
        self.history_dir = Path(history_dir)
        if disabled is None:
            disabled = os.getenv("MULBERRY_DISABLE_CACHE") == "1"
        self._disabled = disabled
        if not self._disabled:
            self.history_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str) -> Path:
        safe = symbol.upper().replace("/", "_").replace("\\", "_")
        return self.history_dir / f"{safe}.json"

    def record(self, symbol: str, snapshot: Dict[str, Any]) -> None:
        """Append today's snapshot, replacing any earlier entry from today."""
        if self._disabled:
            return
        entry = {"date": date.today().isoformat(), **snapshot}
        try:
            entries = self.load(symbol)
            entries = [e for e in entries if e.get("date") != entry["date"]]
            entries.append(entry)
            entries.sort(key=lambda e: e.get("date", ""))
            with open(self._path(symbol), "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=1)
        except Exception as e:
            logger.warning(f"Failed to record score history for {symbol}: {e}")

    def load(self, symbol: str) -> List[Dict[str, Any]]:
        """All snapshots for a symbol, oldest first; [] when none/disabled."""
        if self._disabled:
            return []
        path = self._path(symbol)
        if not path.exists():
            return []
        try:
            with open(path, encoding="utf-8") as f:
                entries = json.load(f)
            return sorted(entries, key=lambda e: e.get("date", ""))
        except Exception as e:
            logger.warning(f"Failed to read score history for {symbol}: {e}")
            return []


def snapshot_from_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Distill an analysis result into a history snapshot (pure)."""
    composite = analysis.get("frameworks", {}).get("composite")
    return {
        "price": analysis.get("current_price", 0),
        "composite": composite.overall_score if composite else None,
        "recommendation": analysis.get("recommendation", ""),
        "profile": composite.profile if composite else "",
        "lens_scores": dict(composite.lens_scores) if composite else {},
    }
