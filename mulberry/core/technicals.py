"""
Momentum and technical analysis

Price-trend context for timing awareness: moving averages, RSI,
52-week range position, and trailing returns. This lens is intentionally
lightweight — it frames entry timing, not investment merit.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field

import pandas as pd

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MomentumAssessment:
    """Results from momentum/technical analysis"""
    score: float                     # 0-100
    signal: str                      # Bullish / Neutral / Bearish
    sma_50: float
    sma_200: float
    price_vs_sma50: float            # percent above/below
    price_vs_sma200: float
    golden_cross: Optional[bool]     # None when insufficient history
    rsi_14: float
    range_position_52w: float        # 0 = at low, 1 = at high
    return_3m: float
    return_6m: float
    checks: Dict[str, Any] = field(default_factory=dict)


class MomentumAnalyzer:
    """
    Momentum scoring engine.

    Five checks (total 100 points):
    1. Price above 50-day SMA   (20)
    2. Price above 200-day SMA  (25)
    3. 50-day above 200-day SMA (20) — golden-cross regime
    4. RSI in healthy band      (15) — 40-70, neither washed out nor overbought
    5. Positive 6-month return  (20)
    """

    def analyze(
        self,
        history: Optional[pd.DataFrame],
        info_metrics: Dict[str, Any],
    ) -> MomentumAssessment:
        if history is None or history.empty or "Close" not in history:
            return self._empty()

        closes = history["Close"].dropna()
        if len(closes) < 20:
            return self._empty()

        price = float(closes.iloc[-1])
        sma_50 = float(closes.rolling(50).mean().iloc[-1]) if len(closes) >= 50 else 0.0
        sma_200 = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else 0.0

        price_vs_sma50 = (price / sma_50 - 1) if sma_50 > 0 else 0.0
        price_vs_sma200 = (price / sma_200 - 1) if sma_200 > 0 else 0.0
        golden_cross = (sma_50 > sma_200) if (sma_50 > 0 and sma_200 > 0) else None

        rsi = self._rsi(closes)
        return_3m = self._trailing_return(closes, 63)
        return_6m = self._trailing_return(closes, 126)

        low_52w = float(info_metrics.get("price_52w_low", 0) or 0)
        high_52w = float(info_metrics.get("price_52w_high", 0) or 0)
        if high_52w > low_52w > 0:
            range_position = (price - low_52w) / (high_52w - low_52w)
        else:
            range_position = 0.5

        checks = {}
        score = 0.0

        above_50 = sma_50 > 0 and price > sma_50
        checks["above_sma50"] = {
            "pass": above_50,
            "value": price_vs_sma50,
            "target": "Price > 50-day avg",
            "description": "Short-term trend",
        }
        score += 20 if above_50 else 0

        above_200 = sma_200 > 0 and price > sma_200
        checks["above_sma200"] = {
            "pass": above_200,
            "value": price_vs_sma200,
            "target": "Price > 200-day avg",
            "description": "Long-term trend",
        }
        score += 25 if above_200 else (12 if sma_200 == 0 else 0)

        checks["golden_cross"] = {
            "pass": bool(golden_cross),
            "value": "Yes" if golden_cross else ("N/A" if golden_cross is None else "No"),
            "target": "50-day > 200-day avg",
            "description": "Moving average regime",
        }
        score += 20 if golden_cross else (10 if golden_cross is None else 0)

        healthy_rsi = 40 <= rsi <= 70
        checks["rsi"] = {
            "pass": healthy_rsi,
            "value": rsi,
            "target": "40–70",
            "description": "RSI (14-day)",
        }
        score += 15 if healthy_rsi else (7 if rsi < 40 else 0)

        positive_6m = return_6m > 0
        checks["return_6m"] = {
            "pass": positive_6m,
            "value": return_6m,
            "target": "> 0%",
            "description": "6-month total return",
        }
        score += 20 if positive_6m else 0

        score = max(0.0, min(100.0, score))
        signal = self._signal(score)

        logger.debug(f"Momentum score: {score:.0f} ({signal})")

        return MomentumAssessment(
            score=score,
            signal=signal,
            sma_50=sma_50,
            sma_200=sma_200,
            price_vs_sma50=price_vs_sma50,
            price_vs_sma200=price_vs_sma200,
            golden_cross=golden_cross,
            rsi_14=rsi,
            range_position_52w=range_position,
            return_3m=return_3m,
            return_6m=return_6m,
            checks=checks,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _rsi(closes: pd.Series, period: int = 14) -> float:
        """Wilder-smoothed relative strength index."""
        if len(closes) < period + 1:
            return 50.0
        delta = closes.diff().dropna()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)
        avg_gain = gains.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]
        avg_loss = losses.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100 - 100 / (1 + rs))

    @staticmethod
    def _trailing_return(closes: pd.Series, trading_days: int) -> float:
        if len(closes) <= trading_days:
            return 0.0
        past = float(closes.iloc[-trading_days - 1])
        if past <= 0:
            return 0.0
        return float(closes.iloc[-1]) / past - 1

    @staticmethod
    def _signal(score: float) -> str:
        if score >= 65:
            return "Bullish"
        if score >= 35:
            return "Neutral"
        return "Bearish"

    @staticmethod
    def _empty() -> MomentumAssessment:
        return MomentumAssessment(
            score=50.0,
            signal="Neutral",
            sma_50=0.0,
            sma_200=0.0,
            price_vs_sma50=0.0,
            price_vs_sma200=0.0,
            golden_cross=None,
            rsi_14=50.0,
            range_position_52w=0.5,
            return_3m=0.0,
            return_6m=0.0,
            checks={
                "insufficient_history": {
                    "pass": False,
                    "value": "N/A",
                    "target": "—",
                    "description": "Insufficient price history for technicals",
                }
            },
        )
