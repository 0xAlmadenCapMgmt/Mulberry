"""
Forward-looking context

Every other lens in Mulberry is backward-looking — it reads reported statements
and past prices. This module surfaces the market's *forward* view: analyst
consensus, forward P/E, forward PEG, and price targets, pulled from the yfinance
`info` payload.

This is deliberately kept as *context only*. Estimates are noisy and easily
stale, so they are displayed alongside the analysis but never folded into the
composite score. `has_data` lets the report omit the panel when nothing is
available.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ForwardContext:
    """Analyst/estimate context (all fields optional)."""
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    recommendation_key: str = ""            # e.g. "buy", "hold"
    recommendation_mean: Optional[float] = None   # 1 (strong buy) .. 5 (sell)
    num_analysts: int = 0
    target_mean: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    upside_to_target: Optional[float] = None      # decimal vs current price
    has_data: bool = False
    _fields: Dict[str, Any] = field(default_factory=dict)


def _clean_num(value) -> Optional[float]:
    """Coerce to float, treating None/0/non-numeric as absent."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if num != 0 else None


def extract_forward_context(info: Dict[str, Any], current_price: float = 0.0) -> ForwardContext:
    """Build a ForwardContext from a yfinance `info` dict.

    `current_price` is used to express the mean price target as an upside/downside
    versus today's price; pass 0 to skip that computation.
    """
    forward_pe = _clean_num(info.get("forwardPE"))
    peg = _clean_num(info.get("pegRatio")) or _clean_num(info.get("trailingPegRatio"))
    rec_key = (info.get("recommendationKey") or "").replace("_", " ").strip()
    rec_mean = _clean_num(info.get("recommendationMean"))
    num_analysts = int(info.get("numberOfAnalystOpinions") or 0)
    target_mean = _clean_num(info.get("targetMeanPrice"))
    target_high = _clean_num(info.get("targetHighPrice"))
    target_low = _clean_num(info.get("targetLowPrice"))

    upside = None
    if target_mean and current_price > 0:
        upside = target_mean / current_price - 1

    has_data = any(
        v is not None for v in (forward_pe, peg, rec_mean, target_mean)
    ) or bool(rec_key)

    return ForwardContext(
        forward_pe=forward_pe,
        peg_ratio=peg,
        recommendation_key=rec_key,
        recommendation_mean=rec_mean,
        num_analysts=num_analysts,
        target_mean=target_mean,
        target_high=target_high,
        target_low=target_low,
        upside_to_target=upside,
        has_data=has_data,
    )
