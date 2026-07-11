"""Tests for the data-confidence assessor."""

import pytest

from mulberry.core import data_quality


def _full_kwargs(**overrides):
    """A fully-populated input set; override individual fields to degrade it."""
    base = dict(
        eps=6.0,
        book_value=20.0,
        shares_outstanding=16.0,
        current_assets=150.0,
        total_liabilities=280.0,
        roe=0.35,
        pe_ratio=25.0,
        earnings_history=[6.0, 5.6, 5.2, 4.9],
        income_annual=[
            {"totalRevenue": 400, "dilutedEPS": 6.0},
            {"totalRevenue": 380, "dilutedEPS": 5.6},
        ],
        cashflow_annual=[{"freeCashFlow": 109}],
        fcf_history=[109, 104, 98],
        history_rows=520,
        pays_dividend=True,
        dividend_years=12,
    )
    base.update(overrides)
    return base


def test_full_data_is_high_confidence():
    result = data_quality.assess(**_full_kwargs())
    assert result.level == "High"
    assert result.score >= 0.8
    assert result.notes == []
    assert result.lenses["value"].missing == []


def test_missing_cashflow_degrades_quality_and_dcf():
    result = data_quality.assess(**_full_kwargs(
        cashflow_annual=[], fcf_history=[]
    ))
    assert result.lenses["dcf"].score < 1.0
    assert result.lenses["quality"].score < 1.0
    assert any("positive free cash flow" in m for m in result.lenses["dcf"].missing)


def test_short_history_degrades_momentum():
    full = data_quality.assess(**_full_kwargs(history_rows=520))
    partial = data_quality.assess(**_full_kwargs(history_rows=60))
    none = data_quality.assess(**_full_kwargs(history_rows=5))
    assert full.lenses["momentum"].score == 1.0
    assert partial.lenses["momentum"].score == 0.5
    assert none.lenses["momentum"].score == 0.0


def test_sparse_data_is_low_confidence():
    result = data_quality.assess(**_full_kwargs(
        eps=0, book_value=0, shares_outstanding=0, current_assets=0,
        total_liabilities=0, roe=0, pe_ratio=0, earnings_history=[],
        income_annual=[], cashflow_annual=[], fcf_history=[],
        history_rows=0, pays_dividend=False, dividend_years=0,
    ))
    assert result.level == "Low"
    assert result.score < 0.5


def test_non_payer_dividend_is_fully_determinable():
    result = data_quality.assess(**_full_kwargs(
        pays_dividend=False, dividend_years=0
    ))
    # A confirmed non-payer is complete data, not missing data
    assert result.lenses["dividend"].score == 1.0
    assert result.lenses["dividend"].missing == []


def test_end_to_end_confidence_present(patch_yfinance):
    import asyncio
    from mulberry.core.stock_analysis import StockAnalyzer
    result = asyncio.run(StockAnalyzer().analyze("TEST"))
    conf = result["data_confidence"]
    assert conf.level in ("High", "Medium", "Low")
    assert 0 <= conf.score <= 1
    assert "value" in conf.lenses
