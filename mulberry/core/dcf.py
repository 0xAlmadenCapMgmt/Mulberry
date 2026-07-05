"""
Discounted cash flow (DCF) valuation

Two-stage free-cash-flow model with deliberately conservative defaults:
historical FCF growth is capped, terminal growth is held near long-run
GDP growth, and the discount rate defaults to 10%.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DCFValuation:
    """Results from DCF valuation"""
    intrinsic_value_per_share: float   # 0 when not computable
    margin_of_safety: float
    base_fcf: float
    stage1_growth: float
    terminal_growth: float
    discount_rate: float
    projection_years: int
    enterprise_value: float
    equity_value: float
    assumptions: Dict[str, Any] = field(default_factory=dict)
    sensitivity: List[Dict[str, Any]] = field(default_factory=list)


class DCFValuator:
    """
    Two-stage FCF discounted cash flow model.

    Stage 1: `projection_years` of growth at the capped historical FCF CAGR.
    Stage 2: Gordon terminal value at `terminal_growth`.
    Equity value = PV of stage 1 + PV of terminal + cash - total debt.
    """

    DEFAULT_DISCOUNT_RATE = 0.10
    DEFAULT_TERMINAL_GROWTH = 0.025
    MAX_STAGE1_GROWTH = 0.15
    MIN_STAGE1_GROWTH = 0.0
    PROJECTION_YEARS = 5

    def __init__(
        self,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        terminal_growth: float = DEFAULT_TERMINAL_GROWTH,
        projection_years: int = PROJECTION_YEARS,
    ):
        self.discount_rate = discount_rate
        self.terminal_growth = terminal_growth
        self.projection_years = projection_years

    def valuate(
        self,
        fcf_history: List[float],
        shares_outstanding: float,
        current_price: float,
        cash: float = 0.0,
        total_debt: float = 0.0,
    ) -> DCFValuation:
        """
        Run the DCF model.

        Args:
            fcf_history: Annual free cash flow, most-recent first
            shares_outstanding: Diluted shares outstanding
            current_price: Current market price per share
            cash: Cash and equivalents (added to equity value)
            total_debt: Total interest-bearing debt (subtracted)
        """
        base_fcf = self._normalized_base_fcf(fcf_history)

        if base_fcf <= 0 or shares_outstanding <= 0:
            logger.warning("DCF not computable: needs positive FCF and share count")
            return DCFValuation(
                intrinsic_value_per_share=0.0,
                margin_of_safety=-1.0,
                base_fcf=base_fcf,
                stage1_growth=0.0,
                terminal_growth=self.terminal_growth,
                discount_rate=self.discount_rate,
                projection_years=self.projection_years,
                enterprise_value=0.0,
                equity_value=0.0,
                assumptions={"note": "Insufficient positive free cash flow history"},
            )

        stage1_growth = self._capped_growth(fcf_history)

        enterprise_value = self._enterprise_value(
            base_fcf, stage1_growth, self.discount_rate, self.terminal_growth
        )
        equity_value = enterprise_value + cash - total_debt
        value_per_share = max(0.0, equity_value / shares_outstanding)

        margin = (
            (value_per_share - current_price) / value_per_share
            if value_per_share > 0
            else -1.0
        )

        sensitivity = self._sensitivity_grid(
            base_fcf, stage1_growth, cash, total_debt, shares_outstanding
        )

        logger.debug(
            f"DCF value/share: ${value_per_share:.2f} "
            f"(g1={stage1_growth:.1%}, r={self.discount_rate:.1%})"
        )

        return DCFValuation(
            intrinsic_value_per_share=value_per_share,
            margin_of_safety=margin,
            base_fcf=base_fcf,
            stage1_growth=stage1_growth,
            terminal_growth=self.terminal_growth,
            discount_rate=self.discount_rate,
            projection_years=self.projection_years,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            assumptions={
                "base_fcf": base_fcf,
                "stage1_growth": stage1_growth,
                "terminal_growth": self.terminal_growth,
                "discount_rate": self.discount_rate,
                "projection_years": self.projection_years,
                "net_cash_adjustment": cash - total_debt,
            },
            sensitivity=sensitivity,
        )

    # ------------------------------------------------------------------

    def _enterprise_value(
        self,
        base_fcf: float,
        stage1_growth: float,
        discount_rate: float,
        terminal_growth: float,
    ) -> float:
        """PV of projected FCF plus discounted Gordon terminal value."""
        if discount_rate <= terminal_growth:
            return 0.0

        pv_stage1 = 0.0
        fcf = base_fcf
        for year in range(1, self.projection_years + 1):
            fcf *= 1 + stage1_growth
            pv_stage1 += fcf / (1 + discount_rate) ** year

        terminal_fcf = fcf * (1 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / (1 + discount_rate) ** self.projection_years

        return pv_stage1 + pv_terminal

    def _sensitivity_grid(
        self,
        base_fcf: float,
        stage1_growth: float,
        cash: float,
        total_debt: float,
        shares: float,
    ) -> List[Dict[str, Any]]:
        """Per-share value across discount-rate / terminal-growth combinations."""
        grid = []
        for r in (0.08, 0.10, 0.12):
            row = {"discount_rate": r, "values": []}
            for g in (0.02, 0.025, 0.03):
                ev = self._enterprise_value(base_fcf, stage1_growth, r, g)
                per_share = max(0.0, (ev + cash - total_debt) / shares)
                row["values"].append({"terminal_growth": g, "value": per_share})
            grid.append(row)
        return grid

    @staticmethod
    def _normalized_base_fcf(fcf_history: List[float]) -> float:
        """Average of up to the last 3 years of FCF to smooth one-off swings."""
        recent = [f for f in fcf_history[:3] if f != 0]
        if not recent:
            return 0.0
        return sum(recent) / len(recent)

    def _capped_growth(self, fcf_history: List[float]) -> float:
        """Historical FCF CAGR clamped to [MIN, MAX] stage-1 growth."""
        positives = [f for f in fcf_history if f > 0]
        if len(positives) < 2:
            return 0.03  # conservative default when history is thin
        try:
            cagr = (positives[0] / positives[-1]) ** (1 / (len(positives) - 1)) - 1
        except Exception:
            return 0.03
        return max(self.MIN_STAGE1_GROWTH, min(cagr, self.MAX_STAGE1_GROWTH))
