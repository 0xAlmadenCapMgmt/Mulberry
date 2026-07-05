"""
Dividend and shareholder-return analysis

Evaluates income characteristics: yield, payout sustainability, dividend
growth, and a Gordon growth model valuation for established payers.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DividendAssessment:
    """Results from dividend analysis"""
    score: float                     # 0-100
    rating: str                      # Strong Payer / Reliable / Modest / None
    pays_dividend: bool
    dividend_yield: float
    payout_ratio: float              # dividends paid / net income
    dividend_cagr_5y: float
    consecutive_years: int
    ddm_value: float                 # Gordon growth value, 0 when N/A
    checks: Dict[str, Any] = field(default_factory=dict)


class DividendAnalyzer:
    """
    Dividend scoring engine.

    Four checks (total 100 points):
    1. Yield                (25) — meaningful current income
    2. Payout sustainability (30) — earnings comfortably cover the dividend
    3. Dividend growth      (25) — payout compounding over 5 years
    4. Track record         (20) — consecutive years of payments

    Non-payers score 0 and are marked rating "None"; the composite scorer
    reweights so non-payers are not penalized on overall score.
    """

    REQUIRED_RETURN = 0.09  # discount rate for the Gordon growth model
    MAX_DDM_GROWTH = 0.06   # cap perpetual dividend growth assumption

    def analyze(
        self,
        info_metrics: Dict[str, Any],
        cashflow_annual: List[Dict[str, Any]],
        dividends_series=None,
    ) -> DividendAssessment:
        dividend_yield = float(info_metrics.get("dividend_yield", 0) or 0)
        # yfinance sometimes reports yield as percent (e.g. 2.5) instead of 0.025
        if dividend_yield > 1:
            dividend_yield /= 100

        price = float(info_metrics.get("price", 0) or 0)
        eps = float(info_metrics.get("eps", 0) or 0)
        consecutive_years = int(info_metrics.get("dividend_years", 0) or 0)

        annual_dividends = self._annual_dividends(dividends_series)
        dividend_cagr = self._dividend_cagr(annual_dividends)
        payout_ratio = self._payout_ratio(cashflow_annual)

        pays_dividend = dividend_yield > 0 or bool(annual_dividends)

        if not pays_dividend:
            return DividendAssessment(
                score=0.0,
                rating="None",
                pays_dividend=False,
                dividend_yield=0.0,
                payout_ratio=0.0,
                dividend_cagr_5y=0.0,
                consecutive_years=0,
                ddm_value=0.0,
                checks={
                    "no_dividend": {
                        "pass": False,
                        "value": "No dividend",
                        "target": "—",
                        "description": "Company does not pay a dividend",
                    }
                },
            )

        checks = {}
        score = 0.0

        pts = self._scale(dividend_yield, low=0.005, high=0.04, max_pts=25)
        checks["yield"] = {
            "pass": dividend_yield >= 0.02,
            "value": dividend_yield,
            "target": ">= 2%",
            "description": "Dividend yield",
        }
        score += pts

        # Sweet spot: payout between 20% and 60% of earnings
        if 0 < payout_ratio <= 0.6:
            pts = 30.0
        elif payout_ratio <= 0.8:
            pts = 18.0
        elif payout_ratio <= 1.0:
            pts = 8.0
        else:
            pts = 0.0
        checks["payout_sustainability"] = {
            "pass": 0 < payout_ratio <= 0.6,
            "value": payout_ratio,
            "target": "<= 60% of earnings",
            "description": "Payout ratio sustainability",
        }
        score += pts

        pts = self._scale(dividend_cagr, low=0.0, high=0.10, max_pts=25)
        checks["dividend_growth"] = {
            "pass": dividend_cagr >= 0.03,
            "value": dividend_cagr,
            "target": ">= 3%/yr",
            "description": "Dividend growth (5-year CAGR)",
        }
        score += pts

        pts = self._scale(float(consecutive_years), low=0, high=20, max_pts=20)
        checks["track_record"] = {
            "pass": consecutive_years >= 10,
            "value": consecutive_years,
            "target": ">= 10 years",
            "description": "Consecutive years of dividends",
        }
        score += pts

        ddm_value = self._gordon_growth_value(
            annual_dividends, dividend_cagr, price
        )

        score = max(0.0, min(100.0, score))
        rating = self._rating(score)

        logger.debug(f"Dividend score: {score:.0f} ({rating})")

        return DividendAssessment(
            score=score,
            rating=rating,
            pays_dividend=True,
            dividend_yield=dividend_yield,
            payout_ratio=payout_ratio,
            dividend_cagr_5y=dividend_cagr,
            consecutive_years=consecutive_years,
            ddm_value=ddm_value,
            checks=checks,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _annual_dividends(dividends_series) -> List[float]:
        """Total dividends per calendar year, most-recent complete years first."""
        if dividends_series is None or (
            hasattr(dividends_series, "empty") and dividends_series.empty
        ):
            return []
        try:
            by_year = dividends_series.groupby(dividends_series.index.year).sum()
            current_year = datetime.now().year
            complete = by_year[by_year.index < current_year]
            return list(complete.sort_index(ascending=False).values[:6])
        except Exception:
            return []

    @staticmethod
    def _dividend_cagr(annual_dividends: List[float]) -> float:
        if len(annual_dividends) < 2 or annual_dividends[-1] <= 0:
            return 0.0
        try:
            years = len(annual_dividends) - 1
            return (annual_dividends[0] / annual_dividends[-1]) ** (1 / years) - 1
        except Exception:
            return 0.0

    @staticmethod
    def _payout_ratio(cashflow_annual: List[Dict[str, Any]]) -> float:
        """Dividends paid as a share of FCF-adjacent earnings (latest year)."""
        if not cashflow_annual:
            return 0.0
        latest = cashflow_annual[0]
        paid = abs(latest.get("dividendPayout", 0) or 0)
        fcf = latest.get("freeCashFlow", 0) or 0
        return paid / fcf if fcf > 0 else 0.0

    def _gordon_growth_value(
        self,
        annual_dividends: List[float],
        dividend_cagr: float,
        price: float,
    ) -> float:
        """
        Gordon growth model: V = D1 / (r - g).

        Only meaningful for steady payers with growth below the required
        return; returns 0 otherwise.
        """
        if not annual_dividends or price <= 0:
            return 0.0
        d0 = annual_dividends[0]
        g = max(0.0, min(dividend_cagr, self.MAX_DDM_GROWTH))
        if d0 <= 0 or self.REQUIRED_RETURN <= g:
            return 0.0
        return d0 * (1 + g) / (self.REQUIRED_RETURN - g)

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
            return "Strong Payer"
        if score >= 45:
            return "Reliable"
        if score > 0:
            return "Modest"
        return "None"
