"""Tests for the StockAnalyzer pipeline: parsers, derived metrics, and a
fully-offline end-to-end run via a patched yfinance."""

import asyncio

import pandas as pd
import pytest

from mulberry.core.stock_analysis import StockAnalyzer


@pytest.fixture
def analyzer():
    return StockAnalyzer()


# --- _safe_get -------------------------------------------------------------

def test_safe_get_tries_multiple_names(analyzer, income_df):
    col = income_df.columns[0]
    assert analyzer._safe_get(income_df, col, "Total Revenue") == 400.0
    # falls through to the second candidate name
    assert analyzer._safe_get(income_df, col, ["Nonexistent", "Net Income"]) == 100.0
    # missing row -> 0.0
    assert analyzer._safe_get(income_df, col, "Not A Row") == 0.0


# --- Statement parsers -----------------------------------------------------

def test_parse_income_stmt(analyzer, income_df):
    parsed = analyzer._parse_income_stmt(income_df)
    assert len(parsed["annual"]) == 4
    assert parsed["annual"][0]["totalRevenue"] == 400.0
    assert parsed["eps_history"] == [6.0, 5.6, 5.2, 4.9]
    # revenue CAGR over the series is positive
    assert parsed["revenue_cagr"] > 0


def test_parse_income_stmt_empty(analyzer):
    parsed = analyzer._parse_income_stmt(None)
    assert parsed == {"annual": [], "eps_history": [], "revenue_cagr": 0.0}


def test_parse_balance_sheet(analyzer, balance_df):
    parsed = analyzer._parse_balance_sheet(balance_df, balance_df)
    q = parsed["quarterly"]
    assert q["currentAssets"] == 150.0
    assert q["totalLiabilities"] == 280.0
    assert q["cash"] == 60.0


def test_parse_cashflow_free_cash_flow(analyzer, cashflow_df):
    parsed = analyzer._parse_cashflow(cashflow_df)
    # FCF = operating cash flow - abs(capex) = 120 - 11 = 109
    assert parsed["annual"][0]["freeCashFlow"] == pytest.approx(109.0)


# --- Derived metrics -------------------------------------------------------

def test_current_ratio(analyzer):
    assert analyzer._calculate_current_ratio(
        {"currentAssets": 150, "currentLiabilities": 130}
    ) == pytest.approx(150 / 130)
    assert analyzer._calculate_current_ratio({"currentAssets": 150}) == 0.0


def test_debt_equity(analyzer):
    assert analyzer._calculate_debt_equity(
        {"longTermDebt": 100, "currentDebt": 20, "totalShareholderEquity": 70}
    ) == pytest.approx(120 / 70)
    # no equity -> sentinel 999
    assert analyzer._calculate_debt_equity({"longTermDebt": 100}) == 999.0


def test_growth_rate_capped(analyzer):
    # huge growth clamped to 0.30
    assert analyzer._calculate_growth_rate([100, 1]) == pytest.approx(0.30)
    assert analyzer._calculate_growth_rate([5]) == 0.0


def test_dividend_years_counts_consecutive(analyzer, dividends_series):
    years = analyzer._calculate_dividend_years(dividends_series)
    assert isinstance(years, int)
    assert years >= 0


def test_dividend_years_no_dividends(analyzer):
    assert analyzer._calculate_dividend_years(None) == 0
    assert analyzer._calculate_dividend_years(pd.Series(dtype=float)) == 0


def test_normalize_dividend_yield(analyzer):
    # Prefer the unambiguous decimal field
    assert analyzer._normalize_dividend_yield(
        {"trailingAnnualDividendYield": 0.0033, "dividendYield": 0.34}
    ) == pytest.approx(0.0033)
    # Fallback: yfinance percent-units field (0.34 meaning 0.34%) -> 0.0034
    assert analyzer._normalize_dividend_yield({"dividendYield": 0.34}) == pytest.approx(0.0034)
    # A percent value like 2.5 -> 0.025
    assert analyzer._normalize_dividend_yield({"dividendYield": 2.5}) == pytest.approx(0.025)
    assert analyzer._normalize_dividend_yield({}) == 0.0


# --- End-to-end (patched yfinance) -----------------------------------------

def test_analyze_end_to_end_offline(analyzer, patch_yfinance):
    result = asyncio.run(analyzer.analyze("TEST"))

    assert result["symbol"] == "TEST"
    assert result["current_price"] == 150.0
    assert result["company_info"]["name"] == "Test Corp"

    # All six frameworks present
    frameworks = result["frameworks"]
    for key in ("quality", "growth", "dividend", "momentum", "dcf", "composite"):
        assert key in frameworks

    composite = frameworks["composite"]
    assert 0 <= composite.overall_score <= 100
    assert isinstance(composite.recommendation, str)
    assert result["recommendation"] == composite.recommendation

    # Graham valuation block intact
    assert result["valuation"]["graham_number"] > 0
    assert "average" in result["valuation"]["margins_of_safety"]


def test_analyze_raises_without_price(analyzer, monkeypatch, fake_ticker):
    import yfinance
    fake_ticker.info = {"longName": "No Price Corp"}  # no currentPrice
    monkeypatch.setattr(yfinance, "Ticker", lambda *a, **k: fake_ticker)
    with pytest.raises(Exception):
        asyncio.run(analyzer.analyze("NOPX"))
