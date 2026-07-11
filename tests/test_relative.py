"""Tests for peer-relative percentile scoring."""

import pytest

from mulberry.core.relative import (
    percentile_rank,
    compare,
    MetricSnapshot,
)


# --- percentile_rank -------------------------------------------------------

def test_percentile_higher_is_better():
    # target 10 beats 5 and 8, loses to 12 -> 2/3
    assert percentile_rank(10, [5, 8, 12], higher_is_better=True) == pytest.approx(2 / 3)


def test_percentile_lower_is_better():
    # lower better: 10 beats only 12 -> 1/3
    assert percentile_rank(10, [5, 8, 12], higher_is_better=False) == pytest.approx(1 / 3)


def test_percentile_ties_count_half():
    assert percentile_rank(10, [10, 10], higher_is_better=True) == pytest.approx(0.5)


def test_percentile_beats_all():
    assert percentile_rank(100, [1, 2, 3], higher_is_better=True) == pytest.approx(1.0)
    assert percentile_rank(0, [1, 2, 3], higher_is_better=False) == pytest.approx(1.0)


def test_percentile_empty_returns_none():
    assert percentile_rank(10, [], higher_is_better=True) is None


# --- compare ---------------------------------------------------------------

def test_compare_builds_results_and_skips_missing():
    target = MetricSnapshot("T", {
        "operating_margin": 0.30, "pe_ratio": 15.0, "gross_margin": None,
    })
    peers = [
        MetricSnapshot("A", {"operating_margin": 0.20, "pe_ratio": 20.0}),
        MetricSnapshot("B", {"operating_margin": 0.25, "pe_ratio": 25.0}),
    ]
    comp = compare(target, peers)
    keys = {r.key for r in comp.results}

    assert "operating_margin" in keys
    assert "pe_ratio" in keys
    assert "gross_margin" not in keys       # target value is None -> skipped

    om = next(r for r in comp.results if r.key == "operating_margin")
    assert om.percentile == pytest.approx(1.0)      # 0.30 beats both peers
    assert om.peer_median == pytest.approx(0.225)
    assert om.higher_is_better is True

    pe = next(r for r in comp.results if r.key == "pe_ratio")
    assert pe.percentile == pytest.approx(1.0)      # 15 lower than both (lower better)
    assert pe.higher_is_better is False

    assert comp.peer_symbols == ["A", "B"]
    assert 0 <= comp.overall_percentile <= 1


def test_compare_skips_metric_without_valid_peers():
    target = MetricSnapshot("T", {"ev_sales": 2.0})
    peers = [MetricSnapshot("A", {"pe_ratio": 10.0})]   # no ev_sales among peers
    comp = compare(target, peers)
    assert comp.results == []
    assert comp.overall_percentile == 0.0
