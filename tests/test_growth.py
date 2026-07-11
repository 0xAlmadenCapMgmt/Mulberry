"""Tests for the growth / GARP engine."""

import pytest

from mulberry.core.growth import GrowthAnalyzer


@pytest.fixture
def analyzer():
    return GrowthAnalyzer()


# --- Deterministic helpers -------------------------------------------------

def test_cagr_known_value(analyzer):
    # most-recent first: (121/100)^(1/2) - 1 = 0.10
    assert analyzer._cagr([121, 110, 100]) == pytest.approx(0.10)


def test_cagr_edge_cases(analyzer):
    assert analyzer._cagr([100]) == 0.0
    assert analyzer._cagr([100, 0]) == 0.0     # non-positive denominator
    assert analyzer._cagr([]) == 0.0


def test_consistency(analyzer):
    # most-recent first, every year grew over the prior
    assert analyzer._consistency([121, 110, 100]) == pytest.approx(1.0)
    # one down year out of two transitions
    assert analyzer._consistency([100, 110, 100]) == pytest.approx(0.5)


def test_rating_buckets(analyzer):
    assert analyzer._rating(75) == "Rapid"
    assert analyzer._rating(50) == "Solid"
    assert analyzer._rating(30) == "Slow"
    assert analyzer._rating(10) == "Stalled"


# --- PEG computation via analyze -------------------------------------------

def test_peg_ratio_computed(analyzer):
    income = [
        {"totalRevenue": 115, "dilutedEPS": 1.15, "freeCashFlow": 0},
        {"totalRevenue": 100, "dilutedEPS": 1.00, "freeCashFlow": 0},
    ]
    # eps_cagr = 15%, pe = 15 -> PEG = 15 / 15 = 1.0
    result = analyzer.analyze({"pe_ratio": 15.0, "eps": 1.15}, income, [])
    assert result.peg_ratio == pytest.approx(1.0, abs=0.01)


def test_lynch_fair_value(analyzer):
    income = [
        {"totalRevenue": 110, "dilutedEPS": 1.10},
        {"totalRevenue": 100, "dilutedEPS": 1.00},
    ]
    # eps_cagr = 10% -> P/E of 10 on EPS 1.10 = 11.0
    result = analyzer.analyze({"pe_ratio": 15.0, "eps": 1.10}, income, [])
    assert result.lynch_fair_value == pytest.approx(11.0, abs=0.05)


# --- End-to-end ------------------------------------------------------------

def test_growing_company_scores_higher_than_flat(analyzer):
    growing = [
        {"totalRevenue": 160, "dilutedEPS": 1.6, "freeCashFlow": 160},
        {"totalRevenue": 140, "dilutedEPS": 1.4, "freeCashFlow": 140},
        {"totalRevenue": 120, "dilutedEPS": 1.2, "freeCashFlow": 120},
        {"totalRevenue": 100, "dilutedEPS": 1.0, "freeCashFlow": 100},
    ]
    flat = [
        {"totalRevenue": 100, "dilutedEPS": 1.0, "freeCashFlow": 100},
        {"totalRevenue": 100, "dilutedEPS": 1.0, "freeCashFlow": 100},
        {"totalRevenue": 100, "dilutedEPS": 1.0, "freeCashFlow": 100},
    ]
    cf_growing = [{"freeCashFlow": r["freeCashFlow"]} for r in growing]
    cf_flat = [{"freeCashFlow": r["freeCashFlow"]} for r in flat]
    g = analyzer.analyze({"pe_ratio": 20, "eps": 1.6}, growing, cf_growing)
    f = analyzer.analyze({"pe_ratio": 20, "eps": 1.0}, flat, cf_flat)
    assert g.score > f.score
    assert g.revenue_cagr > f.revenue_cagr


def test_empty_inputs(analyzer):
    result = analyzer.analyze({}, [], [])
    assert result.score == pytest.approx(0.0, abs=1e-9) or result.score >= 0
    assert result.rating == "Stalled"
