"""
Peer-relative scoring

Absolute thresholds are blunt: a 12% operating margin is excellent for a grocer
and mediocre for a software company. This module ranks the target against an
explicit peer set, metric by metric, expressing each as a **percentile** (what
fraction of peers the target beats) plus the peer median for context.

The pure logic here — percentile ranking and comparison — is fully offline and
unit-tested. Fetching each peer's data and building its `MetricSnapshot` is I/O
and lives in the analysis pipeline (`StockAnalyzer`), which already knows how to
fetch and parse a ticker.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import statistics

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetricSpec:
    """Definition of one comparable metric."""
    key: str
    label: str
    higher_is_better: bool
    fmt: str  # "percent" | "multiple"


# The metrics compared across peers, in display order.
METRIC_SPECS: List[MetricSpec] = [
    MetricSpec("gross_margin", "Gross margin", True, "percent"),
    MetricSpec("operating_margin", "Operating margin", True, "percent"),
    MetricSpec("net_margin", "Net margin", True, "percent"),
    MetricSpec("roe", "Return on equity", True, "percent"),
    MetricSpec("revenue_cagr", "Revenue growth", True, "percent"),
    MetricSpec("eps_cagr", "EPS growth", True, "percent"),
    MetricSpec("pe_ratio", "P/E", False, "multiple"),
    MetricSpec("ev_ebitda", "EV/EBITDA", False, "multiple"),
    MetricSpec("ev_sales", "EV/Sales", False, "multiple"),
    MetricSpec("p_fcf", "P/FCF", False, "multiple"),
    MetricSpec("dividend_yield", "Dividend yield", True, "percent"),
    MetricSpec("debt_equity", "Debt / Equity", False, "multiple"),
]


@dataclass
class MetricSnapshot:
    """A ticker's comparable metrics (None = unavailable)."""
    symbol: str
    values: Dict[str, Optional[float]] = field(default_factory=dict)


@dataclass
class PeerMetricResult:
    key: str
    label: str
    higher_is_better: bool
    fmt: str
    target: float
    peer_median: float
    percentile: float   # 0..1 — fraction of peers the target beats
    n_peers: int


@dataclass
class PeerComparison:
    symbol: str
    peer_symbols: List[str] = field(default_factory=list)
    results: List[PeerMetricResult] = field(default_factory=list)
    overall_percentile: float = 0.0   # mean of per-metric percentiles


def percentile_rank(
    value: float, peer_values: List[float], higher_is_better: bool
) -> Optional[float]:
    """Fraction of peers the target beats, in [0, 1].

    A metric where the target is better than every peer scores 1.0; worse than
    every peer scores 0.0; ties count as half. Returns None when there are no
    peer values to compare against.
    """
    if not peer_values:
        return None
    wins = 0.0
    for peer in peer_values:
        if value == peer:
            wins += 0.5
        elif (value > peer) == higher_is_better:
            wins += 1.0
    return wins / len(peer_values)


def compare(target: MetricSnapshot, peers: List[MetricSnapshot]) -> PeerComparison:
    """Rank `target` against `peers` across every metric with enough data."""
    results: List[PeerMetricResult] = []

    for spec in METRIC_SPECS:
        target_val = target.values.get(spec.key)
        if target_val is None:
            continue
        peer_vals = [
            p.values.get(spec.key)
            for p in peers
            if p.values.get(spec.key) is not None
        ]
        peer_vals = [v for v in peer_vals if v is not None]
        if not peer_vals:
            continue

        pct = percentile_rank(target_val, peer_vals, spec.higher_is_better)
        results.append(
            PeerMetricResult(
                key=spec.key,
                label=spec.label,
                higher_is_better=spec.higher_is_better,
                fmt=spec.fmt,
                target=target_val,
                peer_median=statistics.median(peer_vals),
                percentile=pct if pct is not None else 0.0,
                n_peers=len(peer_vals),
            )
        )

    overall = (
        statistics.mean(r.percentile for r in results) if results else 0.0
    )
    logger.debug(
        f"Peer comparison for {target.symbol}: {len(results)} metrics, "
        f"overall percentile {overall:.0%}"
    )
    return PeerComparison(
        symbol=target.symbol,
        peer_symbols=[p.symbol for p in peers],
        results=results,
        overall_percentile=overall,
    )
