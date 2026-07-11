"""Tests for the composite multi-framework scorer."""

from types import SimpleNamespace

import pytest

from mulberry.core.composite import CompositeScorer


@pytest.fixture
def scorer():
    return CompositeScorer()


def _quality(score=80):
    return SimpleNamespace(score=score, rating="Good", roe=0.20,
                           operating_margin=0.25, margin_trend="Stable")


def _growth(score=60):
    return SimpleNamespace(score=score, rating="Solid", revenue_cagr=0.10,
                           eps_cagr=0.12, peg_ratio=1.2)


def _momentum(score=40):
    return SimpleNamespace(score=score, signal="Neutral", rsi_14=55,
                           range_position_52w=0.6)


def _dividend(score=20, pays=True):
    return SimpleNamespace(score=score, rating="Reliable", pays_dividend=pays,
                           dividend_yield=0.025, consecutive_years=15)


# --- Deterministic helpers -------------------------------------------------

def test_value_score(scorer):
    assert scorer._value_score(0.2, 0.3) == pytest.approx(75.0)   # avg 0.25 -> 75
    assert scorer._value_score(0.0, 0.0) == pytest.approx(50.0)
    assert scorer._value_score(-1.0, -1.0) == pytest.approx(50.0)  # both N/A
    assert scorer._value_score(1.0, 1.0) == pytest.approx(100.0)   # clamped


def test_value_rating(scorer):
    assert scorer._value_rating(85) == "Deep Value"
    assert scorer._value_rating(65) == "Undervalued"
    assert scorer._value_rating(45) == "Fair"
    assert scorer._value_rating(20) == "Expensive"


def test_recommendation_buckets(scorer):
    assert "STRONG BUY" in scorer._recommendation(80, 0.20)
    assert "BUY" in scorer._recommendation(65, 0.05)
    assert "HOLD" in scorer._recommendation(65, -0.10)   # strong but expensive
    assert "HOLD" in scorer._recommendation(45, 0.0)
    assert "REDUCE" in scorer._recommendation(30, -0.2)
    assert "AVOID" in scorer._recommendation(10, -0.5)


# --- Weighting -------------------------------------------------------------

def test_weighted_overall_score(scorer):
    result = scorer.score(
        value_margin_of_safety=0.0,   # value_score = 50
        dcf_margin_of_safety=0.0,
        quality=_quality(80),
        growth=_growth(60),
        dividend=_dividend(20, pays=True),
        momentum=_momentum(40),
    )
    # 50*.30 + 80*.25 + 60*.20 + 40*.15 + 20*.10 = 55
    assert result.overall_score == pytest.approx(55.0)
    assert result.weights == CompositeScorer.DEFAULT_WEIGHTS


def test_non_payer_redistributes_dividend_weight(scorer):
    result = scorer.score(
        value_margin_of_safety=0.10,
        dcf_margin_of_safety=0.10,
        quality=_quality(80),
        growth=_growth(60),
        dividend=_dividend(0, pays=False),
        momentum=_momentum(50),
    )
    assert result.weights["dividend"] == 0.0
    assert sum(result.weights.values()) == pytest.approx(1.0)
    # dividend lens must not drag the score of a non-payer
    assert "value" in result.lens_scores
    assert result.lens_scores["dividend"] == 0


def test_lens_structures_present(scorer):
    result = scorer.score(0.1, 0.1, _quality(), _growth(), _dividend(), _momentum())
    for key in ("value", "quality", "growth", "momentum", "dividend"):
        assert key in result.lens_scores
        assert key in result.lens_ratings
        assert key in result.lens_verdicts


# --- Investor-style weight profiles ----------------------------------------

def test_all_profiles_sum_to_one():
    for name, weights in CompositeScorer.PROFILES.items():
        assert sum(weights.values()) == pytest.approx(1.0), f"{name} weights must sum to 1.0"


def test_profile_changes_weights_and_score():
    args = dict(
        value_margin_of_safety=0.0,
        dcf_margin_of_safety=0.0,
        quality=_quality(80),
        growth=_growth(60),
        dividend=_dividend(20, pays=True),
        momentum=_momentum(40),
    )
    balanced = CompositeScorer("balanced").score(**args)
    deep_value = CompositeScorer("deep_value").score(**args)

    assert balanced.profile == "balanced"
    assert deep_value.profile == "deep_value"
    assert deep_value.weights["value"] == pytest.approx(0.45)
    # Different weightings must produce a different composite for the same inputs
    assert balanced.overall_score != pytest.approx(deep_value.overall_score)


def test_unknown_profile_raises():
    with pytest.raises(ValueError):
        CompositeScorer("nonsense")
