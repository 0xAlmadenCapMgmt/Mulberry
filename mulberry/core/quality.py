"""
Business quality analysis

Evaluates the durability and profitability of the underlying business —
margins, returns on capital, cash conversion, and balance-sheet strength —
independent of the current stock price.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field
import statistics

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QualityAssessment:
    """Results from business quality analysis"""
    score: float                     # 0-100
    rating: str                      # Excellent / Good / Average / Weak
    gross_margin: float
    operating_margin: float
    net_margin: float
    margin_trend: str                # Improving / Stable / Declining
    roe: float
    fcf_conversion: float            # FCF / Net Income
    positive_fcf_years: int
    checks: Dict[str, Any] = field(default_factory=dict)


class QualityAnalyzer:
    """
    Business quality scoring engine.

    Six checks, each worth up to a fixed number of points (total 100):
    1. Gross margin level        (15) — pricing power
    2. Operating margin level    (15) — operating efficiency
    3. Return on equity          (20) — returns on shareholder capital
    4. FCF conversion            (20) — earnings backed by cash
    5. FCF consistency           (15) — positive free cash flow every year
    6. Margin trajectory         (15) — margins stable or improving
    """

    def analyze(
        self,
        info_metrics: Dict[str, Any],
        income_annual: List[Dict[str, Any]],
        cashflow_annual: List[Dict[str, Any]],
    ) -> QualityAssessment:
        margins = self._margin_history(income_annual)
        gross_margin = margins["gross"][0] if margins["gross"] else 0.0
        operating_margin = margins["operating"][0] if margins["operating"] else 0.0
        net_margin = margins["net"][0] if margins["net"] else 0.0
        margin_trend = self._margin_trend(margins["operating"])

        roe = float(info_metrics.get("roe", 0) or 0)
        fcf_conversion, positive_fcf_years = self._fcf_metrics(
            income_annual, cashflow_annual
        )

        checks = {}
        score = 0.0

        pts = self._scale(gross_margin, low=0.20, high=0.50, max_pts=15)
        checks["gross_margin"] = {
            "pass": gross_margin >= 0.30,
            "value": gross_margin,
            "target": ">= 30%",
            "description": "Gross margin (pricing power)",
        }
        score += pts

        pts = self._scale(operating_margin, low=0.05, high=0.25, max_pts=15)
        checks["operating_margin"] = {
            "pass": operating_margin >= 0.12,
            "value": operating_margin,
            "target": ">= 12%",
            "description": "Operating margin (efficiency)",
        }
        score += pts

        pts = self._scale(roe, low=0.05, high=0.25, max_pts=20)
        checks["return_on_equity"] = {
            "pass": roe >= 0.12,
            "value": roe,
            "target": ">= 12%",
            "description": "Return on equity",
        }
        score += pts

        pts = self._scale(fcf_conversion, low=0.4, high=1.0, max_pts=20)
        checks["fcf_conversion"] = {
            "pass": fcf_conversion >= 0.8,
            "value": fcf_conversion,
            "target": ">= 0.8x net income",
            "description": "Free cash flow conversion",
        }
        score += pts

        fcf_years_available = min(len(cashflow_annual), 5) or 1
        fcf_ratio = positive_fcf_years / fcf_years_available
        pts = fcf_ratio * 15
        checks["fcf_consistency"] = {
            "pass": fcf_ratio >= 1.0,
            "value": positive_fcf_years,
            "target": f"{fcf_years_available}/{fcf_years_available} years",
            "description": "Positive free cash flow every year",
        }
        score += pts

        trend_pts = {"Improving": 15, "Stable": 10, "Declining": 0}.get(margin_trend, 5)
        checks["margin_trend"] = {
            "pass": margin_trend in ("Improving", "Stable"),
            "value": margin_trend,
            "target": "Stable or improving",
            "description": "Operating margin trajectory",
        }
        score += trend_pts

        score = max(0.0, min(100.0, score))
        rating = self._rating(score)

        logger.debug(f"Quality score: {score:.0f} ({rating})")

        return QualityAssessment(
            score=score,
            rating=rating,
            gross_margin=gross_margin,
            operating_margin=operating_margin,
            net_margin=net_margin,
            margin_trend=margin_trend,
            roe=roe,
            fcf_conversion=fcf_conversion,
            positive_fcf_years=positive_fcf_years,
            checks=checks,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _scale(value: float, low: float, high: float, max_pts: float) -> float:
        """Linearly scale value in [low, high] to [0, max_pts]."""
        if value <= low:
            return 0.0
        if value >= high:
            return max_pts
        return (value - low) / (high - low) * max_pts

    @staticmethod
    def _margin_history(income_annual: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Margin series, most-recent first."""
        gross, operating, net = [], [], []
        for row in income_annual:
            revenue = row.get("totalRevenue", 0)
            if revenue <= 0:
                continue
            gross.append(row.get("grossProfit", 0) / revenue)
            operating.append(row.get("operatingIncome", 0) / revenue)
            net.append(row.get("netIncome", 0) / revenue)
        return {"gross": gross, "operating": operating, "net": net}

    @staticmethod
    def _margin_trend(operating_margins: List[float]) -> str:
        """Compare most recent operating margin against the prior-years average."""
        if len(operating_margins) < 2:
            return "Unknown"
        latest = operating_margins[0]
        prior_avg = statistics.mean(operating_margins[1:])
        if latest >= prior_avg * 1.05:
            return "Improving"
        if latest <= prior_avg * 0.95:
            return "Declining"
        return "Stable"

    @staticmethod
    def _fcf_metrics(
        income_annual: List[Dict[str, Any]],
        cashflow_annual: List[Dict[str, Any]],
    ) -> tuple:
        """Average FCF/net-income conversion and count of positive-FCF years."""
        conversions = []
        positive_years = 0
        income_by_date = {r["fiscalDateEnding"]: r for r in income_annual}

        for row in cashflow_annual[:5]:
            fcf = row.get("freeCashFlow", 0)
            if fcf > 0:
                positive_years += 1
            income_row = income_by_date.get(row.get("fiscalDateEnding"))
            if income_row:
                net_income = income_row.get("netIncome", 0)
                if net_income > 0:
                    conversions.append(fcf / net_income)

        avg_conversion = statistics.mean(conversions) if conversions else 0.0
        return avg_conversion, positive_years

    @staticmethod
    def _rating(score: float) -> str:
        if score >= 75:
            return "Excellent"
        if score >= 55:
            return "Good"
        if score >= 35:
            return "Average"
        return "Weak"
