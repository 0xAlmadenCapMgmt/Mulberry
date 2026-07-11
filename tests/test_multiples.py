"""Golden-value tests for relative-valuation multiples."""

import pytest

from mulberry.core.multiples import compute_valuation_multiples


def test_multiples_basic():
    m = compute_valuation_multiples(
        enterprise_value=1000, ebitda=100, revenue=500,
        market_cap=800, free_cash_flow=40,
    )
    assert m.ev_ebitda == pytest.approx(10.0)   # 1000 / 100
    assert m.ev_sales == pytest.approx(2.0)      # 1000 / 500
    assert m.p_fcf == pytest.approx(20.0)        # 800 / 40


def test_negative_denominator_yields_zero():
    m = compute_valuation_multiples(
        enterprise_value=1000, ebitda=-50, revenue=500,
        market_cap=800, free_cash_flow=-10,
    )
    assert m.ev_ebitda == 0.0   # negative EBITDA -> N/A, not a misleading negative
    assert m.p_fcf == 0.0       # negative FCF -> N/A
    assert m.ev_sales == pytest.approx(2.0)


def test_missing_inputs_zero():
    m = compute_valuation_multiples(0, 100, 0, 0, 0)
    assert m.ev_ebitda == 0.0
    assert m.ev_sales == 0.0
    assert m.p_fcf == 0.0


def test_as_dict():
    m = compute_valuation_multiples(1000, 100, 500, 800, 40)
    assert m.as_dict() == {"ev_ebitda": 10.0, "ev_sales": 2.0, "p_fcf": 20.0}
