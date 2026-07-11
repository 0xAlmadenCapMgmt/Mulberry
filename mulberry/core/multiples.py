"""
Relative-valuation multiples

The Graham lens values a company on an absolute basis (Graham number, NCAV,
earnings power). This module adds the enterprise- and cash-flow-based multiples
practitioners actually compare across a sector — EV/EBITDA, EV/Sales, and P/FCF
— which the absolute methods don't capture. Each returns 0.0 when its inputs
aren't available, so the pipeline and report can simply skip unavailable ones.
"""

from typing import Dict
from dataclasses import dataclass


@dataclass
class ValuationMultiples:
    """Enterprise- and cash-flow-based valuation ratios (0.0 when N/A)."""
    ev_ebitda: float = 0.0
    ev_sales: float = 0.0
    p_fcf: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return {"ev_ebitda": self.ev_ebitda, "ev_sales": self.ev_sales, "p_fcf": self.p_fcf}


def compute_valuation_multiples(
    enterprise_value: float,
    ebitda: float,
    revenue: float,
    market_cap: float,
    free_cash_flow: float,
) -> ValuationMultiples:
    """Compute EV/EBITDA, EV/Sales, and P/FCF.

    A ratio is only meaningful when its denominator is positive (a negative
    EBITDA or FCF produces a misleading negative multiple), so those cases
    return 0.0 rather than a number that would rank nonsensically.
    """
    ev_ebitda = enterprise_value / ebitda if enterprise_value > 0 and ebitda > 0 else 0.0
    ev_sales = enterprise_value / revenue if enterprise_value > 0 and revenue > 0 else 0.0
    p_fcf = market_cap / free_cash_flow if market_cap > 0 and free_cash_flow > 0 else 0.0

    return ValuationMultiples(
        ev_ebitda=ev_ebitda,
        ev_sales=ev_sales,
        p_fcf=p_fcf,
    )
