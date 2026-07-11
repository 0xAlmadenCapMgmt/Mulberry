"""
Data-confidence scoring

yfinance frequently returns partial data — a missing cash-flow statement, a
blank book value, too little price history. When that happens the analysis
engines fall back to zeros and still emit a precise-looking score. This module
measures how much of each lens's *required input* was actually available, so a
score built on sparse data is visibly flagged rather than silently trusted.

Confidence is about input availability, not pass/fail merit: a great business
and a terrible one can both have High-confidence data.
"""

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class LensConfidence:
    """Input completeness for a single analysis lens."""
    score: float              # 0..1 fraction of required inputs available
    present: int
    total: int
    missing: List[str] = field(default_factory=list)


@dataclass
class DataConfidence:
    """Overall and per-lens data completeness for an analysis."""
    level: str                # High / Medium / Low
    score: float              # 0..1 overall
    lenses: Dict[str, LensConfidence] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


def _lens_from_checks(checks: Dict[str, bool]) -> LensConfidence:
    """Build a LensConfidence from a {input_label: is_present} mapping."""
    total = len(checks)
    present = sum(1 for ok in checks.values() if ok)
    missing = [label for label, ok in checks.items() if not ok]
    score = present / total if total else 1.0
    return LensConfidence(score=score, present=present, total=total, missing=missing)


def assess(
    *,
    eps: float,
    book_value: float,
    shares_outstanding: float,
    current_assets: float,
    total_liabilities: float,
    roe: float,
    pe_ratio: float,
    earnings_history: List[float],
    income_annual: List[dict],
    cashflow_annual: List[dict],
    fcf_history: List[float],
    history_rows: int,
    pays_dividend: bool,
    dividend_years: int,
) -> DataConfidence:
    """Assess input completeness across all lenses.

    Every argument is a primitive already computed by the pipeline, so this
    stays decoupled from the engines and is trivially unit-testable.
    """
    revenue_years = sum(1 for r in income_annual if r.get("totalRevenue", 0) > 0)
    eps_years = sum(1 for r in income_annual if r.get("dilutedEPS", 0) > 0)
    has_fcf = any(f != 0 for f in fcf_history)
    positive_fcf = any(f > 0 for f in fcf_history[:3])

    lenses: Dict[str, LensConfidence] = {}

    # --- Value (Graham) ---
    lenses["value"] = _lens_from_checks({
        "EPS": eps != 0,
        "book value": book_value > 0,
        "shares outstanding": shares_outstanding > 0,
        "current assets": current_assets > 0,
        "total liabilities": total_liabilities > 0,
        "earnings history (3+ yrs)": len([e for e in earnings_history if e > 0]) >= 3,
    })

    # --- Quality ---
    lenses["quality"] = _lens_from_checks({
        "income statement": revenue_years >= 1,
        "return on equity": roe != 0,
        "cash-flow statement": len(cashflow_annual) >= 1,
        "free cash flow": has_fcf,
    })

    # --- Growth ---
    lenses["growth"] = _lens_from_checks({
        "revenue history (2+ yrs)": revenue_years >= 2,
        "EPS history (2+ yrs)": eps_years >= 2,
        "P/E ratio (for PEG)": pe_ratio > 0,
    })

    # --- DCF ---
    lenses["dcf"] = _lens_from_checks({
        "positive free cash flow": positive_fcf,
        "shares outstanding": shares_outstanding > 0,
    })

    # --- Dividend --- (a confirmed non-payer is fully determinable)
    if not pays_dividend:
        lenses["dividend"] = LensConfidence(score=1.0, present=1, total=1, missing=[])
    else:
        lenses["dividend"] = _lens_from_checks({
            "dividend track record": dividend_years > 0,
            "cash-flow statement (payout)": len(cashflow_annual) >= 1,
        })

    # --- Momentum --- graded on how much price history is available
    if history_rows >= 200:
        mom_score, mom_missing = 1.0, []
    elif history_rows >= 50:
        mom_score, mom_missing = 0.5, ["200-day price history"]
    elif history_rows >= 20:
        mom_score, mom_missing = 0.25, ["long-term price history"]
    else:
        mom_score, mom_missing = 0.0, ["price history"]
    lenses["momentum"] = LensConfidence(
        score=mom_score, present=int(mom_score > 0), total=1, missing=mom_missing
    )

    overall = sum(l.score for l in lenses.values()) / len(lenses)
    level = "High" if overall >= 0.8 else "Medium" if overall >= 0.5 else "Low"

    notes: List[str] = []
    for name, lens in lenses.items():
        if lens.missing:
            notes.append(f"{name}: missing {', '.join(lens.missing)}")

    return DataConfidence(level=level, score=overall, lenses=lenses, notes=notes)
