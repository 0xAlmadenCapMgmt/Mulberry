"""Tests for the business-quality engine."""

import pytest

from mulberry.core.quality import QualityAnalyzer


@pytest.fixture
def analyzer():
    return QualityAnalyzer()


# --- Deterministic helpers -------------------------------------------------

def test_scale_bounds(analyzer):
    assert analyzer._scale(0.10, 0.20, 0.50, 15) == 0.0     # at/below low
    assert analyzer._scale(0.50, 0.20, 0.50, 15) == 15.0    # at/above high
    assert analyzer._scale(0.35, 0.20, 0.50, 15) == pytest.approx(7.5)  # midpoint


def test_margin_trend(analyzer):
    assert analyzer._margin_trend([0.20, 0.10, 0.10]) == "Improving"
    assert analyzer._margin_trend([0.10, 0.20, 0.20]) == "Declining"
    assert analyzer._margin_trend([0.15, 0.15]) == "Stable"
    assert analyzer._margin_trend([0.15]) == "Unknown"


def test_rating_buckets(analyzer):
    assert analyzer._rating(80) == "Excellent"
    assert analyzer._rating(60) == "Good"
    assert analyzer._rating(40) == "Average"
    assert analyzer._rating(10) == "Weak"


def test_fcf_metrics(analyzer, income_annual, cashflow_annual):
    conversion, positive_years = analyzer._fcf_metrics(income_annual, cashflow_annual)
    # 4 positive-FCF years; conversion ~ average of fcf/net_income by date
    assert positive_years == 4
    assert conversion == pytest.approx(1.086, abs=0.02)


# --- End-to-end scoring ----------------------------------------------------

def test_strong_company_rates_excellent(analyzer, stock_data, income_annual, cashflow_annual):
    result = analyzer.analyze(stock_data, income_annual, cashflow_annual)
    assert result.rating == "Excellent"
    assert result.score >= 85
    assert result.gross_margin == pytest.approx(0.45)
    assert result.operating_margin == pytest.approx(0.30)
    assert result.positive_fcf_years == 4


def test_weak_company_rates_low(analyzer):
    weak_income = [
        {"fiscalDateEnding": "2024", "totalRevenue": 100, "grossProfit": 15,
         "operatingIncome": 2, "netIncome": 1, "dilutedEPS": 0.1},
        {"fiscalDateEnding": "2023", "totalRevenue": 100, "grossProfit": 18,
         "operatingIncome": 5, "netIncome": 3, "dilutedEPS": 0.3},
    ]
    weak_cashflow = [
        {"fiscalDateEnding": "2024", "freeCashFlow": -5, "netIncome": 1},
        {"fiscalDateEnding": "2023", "freeCashFlow": -2, "netIncome": 3},
    ]
    result = analyzer.analyze({"roe": 0.02}, weak_income, weak_cashflow)
    assert result.rating in ("Weak", "Average")
    assert result.score < 40


def test_empty_inputs_do_not_crash(analyzer):
    result = analyzer.analyze({}, [], [])
    assert result.score >= 0
    assert result.rating in ("Weak", "Average", "Good", "Excellent")
