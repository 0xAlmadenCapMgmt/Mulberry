"""Golden-value tests for the Graham valuation engine."""

import math

import pytest

from mulberry.core.graham import GrahamAnalyzer


@pytest.fixture
def analyzer():
    return GrahamAnalyzer()


# --- Graham Number: sqrt(22.5 * EPS * BVPS) --------------------------------

def test_graham_number_known_value(analyzer):
    # sqrt(22.5 * 5 * 20) = sqrt(2250)
    assert analyzer.graham_number(5.0, 20.0) == pytest.approx(math.sqrt(2250))


def test_graham_number_requires_positive_inputs(analyzer):
    assert analyzer.graham_number(-1.0, 20.0) == 0.0
    assert analyzer.graham_number(5.0, 0.0) == 0.0
    assert analyzer.graham_number(0.0, 0.0) == 0.0


# --- NCAV: (current assets - total liabilities) / shares -------------------

def test_ncav_per_share(analyzer):
    assert analyzer.net_net_working_capital(1000, 400, 100) == pytest.approx(6.0)


def test_ncav_zero_shares(analyzer):
    assert analyzer.net_net_working_capital(1000, 400, 0) == 0.0


# --- Normalized earnings: avg EPS * appropriate P/E ------------------------

def test_normalized_earnings_no_growth(analyzer):
    # avg = 2, conservative P/E = min(12, 8.5) = 8.5 -> 17.0
    assert analyzer.normalized_earnings_value([2, 2, 2, 2], 0.0) == pytest.approx(17.0)


def test_normalized_earnings_growth_capped_at_12(analyzer):
    # 8.5 + 2*(0.05*100) = 18.5, conservative caps at 12 -> avg 3 * 12 = 36
    assert analyzer.normalized_earnings_value([3, 3, 3], 0.05) == pytest.approx(36.0)


def test_normalized_earnings_insufficient_history(analyzer):
    assert analyzer.normalized_earnings_value([1, 2], 0.0) == 0.0
    assert analyzer.normalized_earnings_value([], 0.0) == 0.0


# --- Dividend-adjusted: (EPS * (8.5 + 2g) * 4.4) / Y -----------------------

def test_dividend_adjusted_value(analyzer):
    # (5 * (8.5 + 2*5) * 4.4) / (0.05*100) = (5*18.5*4.4)/5 = 81.4
    assert analyzer.dividend_adjusted_value(5.0, 0.05, 0.05) == pytest.approx(81.4)


def test_dividend_adjusted_requires_positive_eps(analyzer):
    assert analyzer.dividend_adjusted_value(0.0, 0.05, 0.05) == 0.0


def test_dividend_adjusted_zero_yield_uses_fallback(analyzer):
    # Fallback AAA yield = 4.4% -> (5*18.5*4.4)/4.4 = 92.5
    assert analyzer.dividend_adjusted_value(5.0, 0.05, 0.0) == pytest.approx(92.5)


# --- Margin of safety ------------------------------------------------------

def test_margin_of_safety(analyzer):
    assert analyzer.margin_of_safety(100, 70) == pytest.approx(0.30)
    assert analyzer.margin_of_safety(100, 120) == pytest.approx(-0.20)


def test_margin_of_safety_invalid_intrinsic(analyzer):
    assert analyzer.margin_of_safety(0, 50) == -1.0


# --- Defensive checklist ---------------------------------------------------

def test_defensive_checklist_all_pass(analyzer):
    data = {
        "current_ratio": 2.5,
        "debt_equity": 0.3,
        "positive_earnings_years": 10,
        "dividend_years": 25,
        "pe_ratio": 12,
        "pb_ratio": 1.2,
        "market_cap": 5_000_000_000,
    }
    result = analyzer.defensive_investor_checklist(data)
    assert result["summary"]["overall_pass"] is True
    assert result["summary"]["passed"] == 8
    assert result["combined_test"]["pass"] is True  # 12*1.2 = 14.4 <= 22.5


def test_defensive_checklist_all_fail(analyzer):
    data = {
        "current_ratio": 0.5,
        "debt_equity": 3.0,
        "positive_earnings_years": 1,
        "dividend_years": 0,
        "pe_ratio": 40,
        "pb_ratio": 8,
        "market_cap": 100_000_000,
    }
    result = analyzer.defensive_investor_checklist(data)
    assert result["summary"]["overall_pass"] is False
    assert result["summary"]["passed"] == 0


# --- Enterprising checklist ------------------------------------------------

def test_enterprising_net_net_opportunity(analyzer):
    # price 5 < 2/3 * NCAV(10) = 6.67 -> net-net opportunity
    data = {"price": 5.0, "ncav_per_share": 10.0}
    result = analyzer.enterprising_investor_checklist(data)
    assert result["net_net"]["opportunity"] is True


def test_enterprising_no_opportunity_when_expensive(analyzer):
    data = {"price": 50.0, "ncav_per_share": 10.0, "pe_ratio": 30}
    result = analyzer.enterprising_investor_checklist(data)
    assert result["net_net"]["opportunity"] is False


# --- Comprehensive analysis integration ------------------------------------

def test_comprehensive_analysis_produces_recommendation(analyzer):
    result = analyzer.comprehensive_analysis(
        eps=6.0,
        book_value_per_share=20.0,
        current_assets=150.0,
        total_liabilities=280.0,
        shares_outstanding=16.0,
        current_price=150.0,
        earnings_history=[6.0, 5.6, 5.2, 4.9],
        growth_rate=0.05,
        aaa_yield=0.05,
        stock_data={"current_ratio": 1.15, "pe_ratio": 25},
    )
    assert isinstance(result.recommendation, str)
    assert result.graham_number == pytest.approx(math.sqrt(22.5 * 6.0 * 20.0))
    # Expensive name trading well above Graham number -> negative avg margin
    assert result.avg_margin_of_safety < 0
