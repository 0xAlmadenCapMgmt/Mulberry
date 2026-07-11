"""Tests for the momentum / technicals engine."""

import numpy as np
import pandas as pd
import pytest

from mulberry.core.technicals import MomentumAnalyzer


@pytest.fixture
def analyzer():
    return MomentumAnalyzer()


def _closes(values):
    idx = pd.date_range("2023-01-02", periods=len(values), freq="B")
    return pd.Series(values, index=idx, name="Close")


# --- Deterministic helpers -------------------------------------------------

def test_rsi_all_gains_is_100(analyzer):
    closes = _closes(np.linspace(100, 200, 60))  # strictly rising
    assert analyzer._rsi(closes) == pytest.approx(100.0)


def test_rsi_insufficient_history(analyzer):
    assert analyzer._rsi(_closes([100, 101, 102])) == 50.0


def test_trailing_return(analyzer):
    # 21 points: last / (point 21 back) - 1
    values = list(np.linspace(100, 120, 21))
    closes = _closes(values)
    # 20-day lookback: closes[-1]=120 over closes[-21]=100 -> 0.20
    assert analyzer._trailing_return(closes, 20) == pytest.approx(0.20)


def test_trailing_return_insufficient(analyzer):
    assert analyzer._trailing_return(_closes([100, 110]), 63) == 0.0


def test_signal_buckets(analyzer):
    assert analyzer._signal(70) == "Bullish"
    assert analyzer._signal(50) == "Neutral"
    assert analyzer._signal(20) == "Bearish"


# --- End-to-end ------------------------------------------------------------

def test_uptrend_is_bullish(analyzer):
    idx = pd.date_range("2022-01-03", periods=520, freq="B")
    df = pd.DataFrame({"Close": np.linspace(50, 150, 520)}, index=idx)
    info = {"price_52w_low": 100, "price_52w_high": 150}
    result = analyzer.analyze(df, info)
    assert result.signal == "Bullish"
    assert result.golden_cross is True
    assert result.score >= 65


def test_downtrend_is_bearish(analyzer):
    idx = pd.date_range("2022-01-03", periods=520, freq="B")
    df = pd.DataFrame({"Close": np.linspace(150, 50, 520)}, index=idx)
    info = {"price_52w_low": 50, "price_52w_high": 150}
    result = analyzer.analyze(df, info)
    assert result.signal == "Bearish"
    assert result.golden_cross is False


def test_empty_history_returns_neutral(analyzer):
    result = analyzer.analyze(None, {})
    assert result.signal == "Neutral"
    assert result.score == 50.0

    result2 = analyzer.analyze(pd.DataFrame(), {})
    assert result2.signal == "Neutral"
