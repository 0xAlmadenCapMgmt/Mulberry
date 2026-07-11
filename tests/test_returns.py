"""Tests for the shared return/risk-metrics helper."""

import numpy as np
import pandas as pd
import pytest

from mulberry.utils.returns import compute_return_metrics


def _series(values, start="2022-01-03"):
    idx = pd.date_range(start, periods=len(values), freq="B")
    return pd.Series(values, index=idx, dtype=float)


def test_total_return():
    m = compute_return_metrics(_series([100, 110]))
    assert m["total_return"] == pytest.approx(0.10)


def test_empty_and_short_series_are_zero():
    assert compute_return_metrics(None)["volatility"] == 0.0
    assert compute_return_metrics(_series([100]))["total_return"] == 0.0


def test_max_drawdown_is_negative_on_decline():
    # rise to 150 then fall to 75 -> ~50% drawdown from the peak
    m = compute_return_metrics(_series([100, 150, 75]))
    assert m["max_drawdown"] < 0
    assert m["max_drawdown"] == pytest.approx(-0.5, abs=0.01)


def test_volatility_zero_for_constant_series():
    m = compute_return_metrics(_series([100, 100, 100, 100]))
    assert m["volatility"] == pytest.approx(0.0)
    assert m["sharpe_ratio"] == 0.0


def test_annualized_return_positive_uptrend():
    m = compute_return_metrics(_series(list(np.linspace(100, 200, 252))))
    assert m["annualized_return"] > 0
    assert m["volatility"] >= 0
