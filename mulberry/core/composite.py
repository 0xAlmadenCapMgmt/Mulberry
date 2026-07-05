"""
Composite multi-framework scoring

Blends the five analysis lenses — value, quality, growth, dividend, and
momentum — into a single weighted score and overall recommendation.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CompositeScore:
    """Blended multi-framework result"""
    overall_score: float             # 0-100
    recommendation: str
    lens_scores: Dict[str, float] = field(default_factory=dict)
    lens_ratings: Dict[str, str] = field(default_factory=dict)
    lens_verdicts: Dict[str, str] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)


class CompositeScorer:
    """
    Weighted blend of the five analysis lenses.

    Default weights favor the price-versus-value question (value + quality
    make up more than half the score) with growth, momentum, and dividends
    as supporting evidence. When a company pays no dividend, that weight is
    redistributed proportionally across the other lenses.
    """

    DEFAULT_WEIGHTS = {
        "value": 0.30,
        "quality": 0.25,
        "growth": 0.20,
        "momentum": 0.15,
        "dividend": 0.10,
    }

    def score(
        self,
        value_margin_of_safety: float,
        dcf_margin_of_safety: float,
        quality,
        growth,
        dividend,
        momentum,
    ) -> CompositeScore:
        """
        Args:
            value_margin_of_safety: Average Graham margin of safety (decimal)
            dcf_margin_of_safety: DCF margin of safety (decimal, -1 when N/A)
            quality: QualityAssessment
            growth: GrowthAssessment
            dividend: DividendAssessment
            momentum: MomentumAssessment
        """
        value_score = self._value_score(value_margin_of_safety, dcf_margin_of_safety)

        lens_scores = {
            "value": value_score,
            "quality": quality.score,
            "growth": growth.score,
            "momentum": momentum.score,
            "dividend": dividend.score,
        }

        lens_ratings = {
            "value": self._value_rating(value_score),
            "quality": quality.rating,
            "growth": growth.rating,
            "momentum": momentum.signal,
            "dividend": dividend.rating,
        }

        lens_verdicts = {
            "value": self._value_verdict(value_margin_of_safety, dcf_margin_of_safety),
            "quality": f"{quality.rating} business — ROE {quality.roe:.0%}, "
                       f"operating margin {quality.operating_margin:.0%}, "
                       f"margins {quality.margin_trend.lower()}",
            "growth": f"{growth.rating} growth — revenue {growth.revenue_cagr:.0%}/yr, "
                      f"EPS {growth.eps_cagr:.0%}/yr"
                      + (f", PEG {growth.peg_ratio:.1f}" if growth.peg_ratio > 0 else ""),
            "momentum": f"{momentum.signal} trend — RSI {momentum.rsi_14:.0f}, "
                        f"{momentum.range_position_52w:.0%} of 52-week range",
            "dividend": (
                f"{dividend.rating} — yield {dividend.dividend_yield:.1%}, "
                f"{dividend.consecutive_years} consecutive years"
                if dividend.pays_dividend
                else "No dividend paid"
            ),
        }

        weights = dict(self.DEFAULT_WEIGHTS)
        if not dividend.pays_dividend:
            # Redistribute the dividend weight so non-payers aren't penalized
            freed = weights.pop("dividend")
            total = sum(weights.values())
            weights = {k: v + freed * v / total for k, v in weights.items()}
            weights["dividend"] = 0.0

        overall = sum(lens_scores[k] * weights.get(k, 0) for k in lens_scores)
        overall = max(0.0, min(100.0, overall))

        recommendation = self._recommendation(overall, value_margin_of_safety)

        logger.info(f"Composite score: {overall:.0f} — {recommendation}")

        return CompositeScore(
            overall_score=overall,
            recommendation=recommendation,
            lens_scores=lens_scores,
            lens_ratings=lens_ratings,
            lens_verdicts=lens_verdicts,
            weights=weights,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _value_score(graham_mos: float, dcf_mos: float) -> float:
        """
        Map margins of safety onto 0-100.

        A margin of 0% maps to 50; +50% or better maps to 100; -50% or
        worse maps to 0. Graham and DCF margins are averaged when both
        are available.
        """
        margins = [m for m in (graham_mos, dcf_mos) if m > -1.0]
        if not margins:
            return 50.0
        avg = sum(margins) / len(margins)
        return max(0.0, min(100.0, 50 + avg * 100))

    @staticmethod
    def _value_rating(score: float) -> str:
        if score >= 80:
            return "Deep Value"
        if score >= 60:
            return "Undervalued"
        if score >= 40:
            return "Fair"
        return "Expensive"

    @staticmethod
    def _value_verdict(graham_mos: float, dcf_mos: float) -> str:
        parts = []
        if graham_mos > -1.0:
            parts.append(f"Graham margin of safety {graham_mos:.0%}")
        if dcf_mos > -1.0:
            parts.append(f"DCF margin of safety {dcf_mos:.0%}")
        return " · ".join(parts) if parts else "Insufficient data for valuation"

    @staticmethod
    def _recommendation(overall: float, value_mos: float) -> str:
        """
        Overall recommendation.

        The composite score drives the call, but a severely negative
        margin of safety caps the recommendation at HOLD — quality and
        momentum alone never justify a BUY at any price.
        """
        if overall >= 75 and value_mos >= 0.15:
            return "STRONG BUY — High conviction across frameworks with a real margin of safety"
        if overall >= 60 and value_mos >= 0:
            return "BUY — Favorable multi-framework profile at a reasonable price"
        if overall >= 60 and value_mos < 0:
            return "HOLD — Strong business, but the price already reflects it"
        if overall >= 40:
            return "HOLD — Mixed signals across frameworks"
        if overall >= 25:
            return "REDUCE — Weak fundamentals with limited valuation support"
        return "AVOID — Unfavorable across most frameworks"
