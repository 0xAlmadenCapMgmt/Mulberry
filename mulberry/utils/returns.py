"""Return and risk metrics from a price series.

A single implementation shared by the momentum lens (fed the price history the
pipeline already downloaded) and YahooFinanceAPI.calculate_returns, so the
Sharpe / volatility / drawdown math lives in exactly one place.
"""

from typing import Dict

import pandas as pd

TRADING_DAYS = 252


def compute_return_metrics(closes: pd.Series, risk_free_rate: float = 0.0) -> Dict[str, float]:
    """Total/annualized return, annualized volatility, max drawdown, Sharpe.

    Args:
        closes: Close-price series with a DatetimeIndex, oldest first.
        risk_free_rate: Annual risk-free rate for the Sharpe numerator.

    Returns a dict of floats; all-zero when the series is too short to measure.
    """
    empty = {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "volatility": 0.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
    }
    if closes is None:
        return empty
    closes = closes.dropna()
    if len(closes) < 2:
        return empty

    start_price = float(closes.iloc[0])
    end_price = float(closes.iloc[-1])
    if start_price <= 0:
        return empty

    total_return = end_price / start_price - 1

    # Years from the index span, falling back to a trading-day estimate.
    try:
        years = (closes.index[-1] - closes.index[0]).days / 365.25
    except (AttributeError, TypeError):
        years = len(closes) / TRADING_DAYS
    years = max(years, 1e-9)

    annualized_return = (end_price / start_price) ** (1 / years) - 1

    daily_returns = closes.pct_change().dropna()
    volatility = float(daily_returns.std() * (TRADING_DAYS ** 0.5)) if not daily_returns.empty else 0.0

    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0

    sharpe = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0.0

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
    }
