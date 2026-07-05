"""
Growth and GARP (growth-at-a-reasonable-price) analysis

Measures the pace and consistency of revenue and earnings growth and
relates it to the price paid via the PEG ratio, in the spirit of
Peter Lynch's One Up on Wall Street.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GrowthAssessment:
    """Results from growth analysis"""
    score: float                     # 0-100
    rating: str                      # Rapid / Solid / Slow / Stalled
    revenue_cagr: float
    eps_cagr: float
    fcf_cagr: float
    peg_ratio: float                 # 0 when not computable
    lynch_fair_value: float          # EPS x growth-rate PE, 0 when not computable
    growth_consistency: float        # fraction of years with revenue growth
    checks: Dict[str, Any] = field(default_factory=dict)


class GrowthAnalyzer:
    """
    Growth scoring engine.

    Five checks (total 100 points):
    1. Revenue CAGR          (25) — top-line expansion
    2. EPS CAGR              (25) — per-share earnings growth
    3. FCF CAGR              (15) — cash flow growth
    4. Growth consistency    (15) — share of years revenue grew
    5. PEG ratio             (20) — growth priced reasonably (PEG <= 1 ideal)
    """

    # Lynch: a fairly priced stock trades at a P/E about equal to its growth rate
    MAX_LYNCH_GROWTH_PE = 25.0

    def analyze(
        self,
        info_metrics: Dict[str, Any],
        income_annual: List[Dict[str, Any]],
        cashflow_annual: List[Dict[str, Any]],
    ) -> GrowthAssessment:
        revenues = [r["totalRevenue"] for r in income_annual if r.get("totalRevenue", 0) > 0]
        eps_series = [r["dilutedEPS"] for r in income_annual if r.get("dilutedEPS", 0) > 0]
        fcf_series = [r["freeCashFlow"] for r in cashflow_annual if r.get("freeCashFlow", 0) > 0]

        revenue_cagr = self._cagr(revenues)
        eps_cagr = self._cagr(eps_series)
        fcf_cagr = self._cagr(fcf_series)
        consistency = self._consistency(revenues)

        pe_ratio = float(info_metrics.get("pe_ratio", 0) or 0)
        eps = float(info_metrics.get("eps", 0) or 0)

        growth_pct = eps_cagr * 100
        peg_ratio = pe_ratio / growth_pct if pe_ratio > 0 and growth_pct > 0 else 0.0

        # Lynch fair value: P/E equal to earnings growth rate (capped)
        lynch_fair_value = 0.0
        if eps > 0 and growth_pct > 0:
            lynch_fair_value = eps * min(growth_pct, self.MAX_LYNCH_GROWTH_PE)

        checks = {}
        score = 0.0

        pts = self._scale(revenue_cagr, low=0.0, high=0.15, max_pts=25)
        checks["revenue_growth"] = {
            "pass": revenue_cagr >= 0.05,
            "value": revenue_cagr,
            "target": ">= 5%/yr",
            "description": "Revenue CAGR (multi-year)",
        }
        score += pts

        pts = self._scale(eps_cagr, low=0.0, high=0.15, max_pts=25)
        checks["eps_growth"] = {
            "pass": eps_cagr >= 0.05,
            "value": eps_cagr,
            "target": ">= 5%/yr",
            "description": "EPS CAGR (multi-year)",
        }
        score += pts

        pts = self._scale(fcf_cagr, low=0.0, high=0.15, max_pts=15)
        checks["fcf_growth"] = {
            "pass": fcf_cagr >= 0.03,
            "value": fcf_cagr,
            "target": ">= 3%/yr",
            "description": "Free cash flow CAGR",
        }
        score += pts

        pts = consistency * 15
        checks["consistency"] = {
            "pass": consistency >= 0.75,
            "value": consistency,
            "target": ">= 75% of years",
            "description": "Years with revenue growth",
        }
        score += pts

        if peg_ratio > 0:
            # PEG 0.5 or lower earns full points; 2.0 or higher earns none
            pts = self._scale(2.0 - peg_ratio, low=0.0, high=1.5, max_pts=20)
        else:
            pts = 0.0
        checks["peg_ratio"] = {
            "pass": 0 < peg_ratio <= 1.0,
            "value": peg_ratio,
            "target": "<= 1.0",
            "description": "PEG ratio (P/E vs growth)",
        }
        score += pts

        score = max(0.0, min(100.0, score))
        rating = self._rating(score)

        logger.debug(f"Growth score: {score:.0f} ({rating})")

        return GrowthAssessment(
            score=score,
            rating=rating,
            revenue_cagr=revenue_cagr,
            eps_cagr=eps_cagr,
            fcf_cagr=fcf_cagr,
            peg_ratio=peg_ratio,
            lynch_fair_value=lynch_fair_value,
            growth_consistency=consistency,
            checks=checks,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _cagr(series: List[float]) -> float:
        """Compound annual growth rate of a most-recent-first series."""
        if len(series) < 2 or series[-1] <= 0:
            return 0.0
        try:
            years = len(series) - 1
            return (series[0] / series[-1]) ** (1 / years) - 1
        except Exception:
            return 0.0

    @staticmethod
    def _consistency(revenues: List[float]) -> float:
        """Fraction of year-over-year periods with revenue growth."""
        if len(revenues) < 2:
            return 0.0
        growth_years = sum(
            1 for newer, older in zip(revenues, revenues[1:]) if newer > older
        )
        return growth_years / (len(revenues) - 1)

    @staticmethod
    def _scale(value: float, low: float, high: float, max_pts: float) -> float:
        if value <= low:
            return 0.0
        if value >= high:
            return max_pts
        return (value - low) / (high - low) * max_pts

    @staticmethod
    def _rating(score: float) -> str:
        if score >= 70:
            return "Rapid"
        if score >= 45:
            return "Solid"
        if score >= 25:
            return "Slow"
        return "Stalled"
