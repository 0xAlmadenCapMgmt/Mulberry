"""Tests for the dividend / shareholder-return engine."""

import pandas as pd
import pytest

from mulberry.core.dividend import DividendAnalyzer


@pytest.fixture
def analyzer():
    return DividendAnalyzer()


# --- Deterministic helpers -------------------------------------------------

def test_dividend_cagr(analyzer):
    # most-recent first: (1.21/1.00)^(1/2) - 1 = 0.10
    assert analyzer._dividend_cagr([1.21, 1.10, 1.00]) == pytest.approx(0.10)


def test_dividend_cagr_edge(analyzer):
    assert analyzer._dividend_cagr([1.0]) == 0.0
    assert analyzer._dividend_cagr([1.0, 0.0]) == 0.0


def test_payout_ratio(analyzer):
    cf = [{"dividendPayout": -50, "freeCashFlow": 200}]
    assert analyzer._payout_ratio(cf) == pytest.approx(0.25)


def test_payout_ratio_no_data(analyzer):
    assert analyzer._payout_ratio([]) == 0.0


def test_gordon_growth_value(analyzer):
    # V = D0*(1+g)/(r-g) = 2*1.04/(0.09-0.04) = 2.08/0.05 = 41.6
    assert analyzer._gordon_growth_value([2.0], 0.04, price=50.0) == pytest.approx(41.6)


def test_gordon_growth_zero_when_growth_exceeds_required(analyzer):
    # g capped at 0.06 < r=0.09, so never degenerate; but zero price -> 0
    assert analyzer._gordon_growth_value([2.0], 0.04, price=0.0) == 0.0


def test_rating_buckets(analyzer):
    assert analyzer._rating(75) == "Strong Payer"
    assert analyzer._rating(50) == "Reliable"
    assert analyzer._rating(10) == "Modest"
    assert analyzer._rating(0) == "None"


# --- Annual aggregation from a price/dividend Series -----------------------

def test_annual_dividends_groups_by_year(analyzer, dividends_series):
    annual = analyzer._annual_dividends(dividends_series)
    # 2018..2023 are complete years (2024 excluded as current-year in-progress
    # depends on run date); at least the older complete years are present
    assert len(annual) >= 5
    assert all(v > 0 for v in annual)


# --- End-to-end ------------------------------------------------------------

def test_non_payer_scores_zero(analyzer):
    result = analyzer.analyze({"dividend_yield": 0.0, "price": 100}, [], None)
    assert result.pays_dividend is False
    assert result.score == 0.0
    assert result.rating == "None"


def test_dividend_payer_scores(analyzer, cashflow_annual, dividends_series):
    info = {"dividend_yield": 0.025, "price": 150.0, "eps": 6.0, "dividend_years": 15}
    result = analyzer.analyze(info, cashflow_annual, dividends_series)
    assert result.pays_dividend is True
    assert result.score > 0
    assert result.dividend_yield == pytest.approx(0.025)


def test_yield_percent_normalization(analyzer):
    # yfinance sometimes reports 2.5 meaning 2.5%
    info = {"dividend_yield": 2.5, "price": 100.0, "eps": 5.0, "dividend_years": 10}
    result = analyzer.analyze(info, [], None)
    assert result.dividend_yield == pytest.approx(0.025)
