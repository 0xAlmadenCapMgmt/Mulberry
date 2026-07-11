"""Tests for forward-looking context extraction."""

import pytest

from mulberry.core.forward import extract_forward_context


def test_extracts_all_fields():
    info = {
        "forwardPE": 18.5,
        "pegRatio": 1.4,
        "recommendationKey": "buy",
        "recommendationMean": 2.1,
        "numberOfAnalystOpinions": 30,
        "targetMeanPrice": 180.0,
        "targetHighPrice": 220.0,
        "targetLowPrice": 150.0,
    }
    f = extract_forward_context(info, current_price=150.0)
    assert f.has_data is True
    assert f.forward_pe == pytest.approx(18.5)
    assert f.peg_ratio == pytest.approx(1.4)
    assert f.recommendation_key == "buy"
    assert f.recommendation_mean == pytest.approx(2.1)
    assert f.num_analysts == 30
    assert f.upside_to_target == pytest.approx(180.0 / 150.0 - 1)


def test_peg_falls_back_to_trailing():
    f = extract_forward_context({"trailingPegRatio": 2.0}, current_price=0)
    assert f.peg_ratio == pytest.approx(2.0)


def test_no_data():
    f = extract_forward_context({}, current_price=100)
    assert f.has_data is False
    assert f.forward_pe is None
    assert f.upside_to_target is None


def test_zero_values_treated_as_absent():
    f = extract_forward_context({"forwardPE": 0, "targetMeanPrice": 0}, current_price=100)
    assert f.forward_pe is None
    assert f.upside_to_target is None


def test_recommendation_key_only_counts_as_data():
    f = extract_forward_context({"recommendationKey": "strong_buy"}, current_price=0)
    assert f.has_data is True
    assert f.recommendation_key == "strong buy"
