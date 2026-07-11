"""Shared fixtures and synthetic-data builders for the Mulberry test suite.

All fixtures are fully offline — no network, no live yfinance calls. The
`fake_ticker` fixture mimics the small slice of the `yfinance.Ticker` API that
`StockAnalyzer._fetch_yf_data` actually touches, so the whole pipeline can run
against canned data.
"""

import os

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _disable_raw_cache():
    """Default the raw-data cache off so tests always exercise patched data.

    Individual cache tests re-enable/disable it per-case via monkeypatch.
    """
    prev = os.environ.get("MULBERRY_DISABLE_CACHE")
    os.environ["MULBERRY_DISABLE_CACHE"] = "1"
    yield
    if prev is None:
        os.environ.pop("MULBERRY_DISABLE_CACHE", None)
    else:
        os.environ["MULBERRY_DISABLE_CACHE"] = prev


# ---------------------------------------------------------------------------
# DataFrame builders
# ---------------------------------------------------------------------------

def make_statement_df(rows: dict, dates: list) -> pd.DataFrame:
    """Build a yfinance-style statement frame.

    Index = line-item names, columns = period-end Timestamps (most recent
    first), matching how yfinance returns income_stmt / balance_sheet / cashflow.

    `rows` maps a line-item name to a list of values aligned with `dates`.
    """
    cols = [pd.Timestamp(d) for d in dates]
    return pd.DataFrame(rows, index=cols).T


# Four fiscal years, most-recent first — the order yfinance uses.
ANNUAL_DATES = ["2024-09-30", "2023-09-30", "2022-09-30", "2021-09-30"]


@pytest.fixture
def income_df():
    return make_statement_df(
        {
            "Total Revenue": [400.0, 380.0, 365.0, 350.0],
            "Gross Profit": [180.0, 170.0, 160.0, 150.0],
            "Operating Income": [120.0, 113.0, 108.0, 100.0],
            "Net Income": [100.0, 95.0, 90.0, 85.0],
            "EBITDA": [130.0, 123.0, 118.0, 110.0],
            "Diluted EPS": [6.0, 5.6, 5.2, 4.9],
        },
        ANNUAL_DATES,
    )


@pytest.fixture
def balance_df():
    # Single most-recent column, as used by _parse_balance_sheet (df.columns[0]).
    return make_statement_df(
        {
            "Current Assets": [150.0],
            "Current Liabilities": [130.0],
            "Total Assets": [350.0],
            "Total Liabilities Net Minority Interest": [280.0],
            "Stockholders Equity": [70.0],
            "Long Term Debt": [100.0],
            "Current Debt": [20.0],
            "Cash And Cash Equivalents": [60.0],
        },
        ANNUAL_DATES[:1],
    )


@pytest.fixture
def cashflow_df():
    return make_statement_df(
        {
            "Operating Cash Flow": [120.0, 114.0, 108.0, 100.0],
            "Capital Expenditure": [-11.0, -10.0, -10.0, -9.0],
            "Common Stock Dividend Paid": [-15.0, -14.0, -13.0, -12.0],
        },
        ANNUAL_DATES,
    )


@pytest.fixture
def dividends_series():
    """Quarterly dividends, 2018–2024, slowly rising."""
    dates, amounts = [], []
    per_year = {2018: 0.60, 2019: 0.68, 2020: 0.76, 2021: 0.84,
                2022: 0.90, 2023: 0.94, 2024: 0.98}
    for year, annual in per_year.items():
        for month in (2, 5, 8, 11):
            dates.append(pd.Timestamp(f"{year}-{month:02d}-15"))
            amounts.append(annual / 4)
    return pd.Series(amounts, index=pd.DatetimeIndex(dates), name="Dividends")


@pytest.fixture
def price_history():
    """~2 years of business-day closes trending 120 -> 150 (uptrend)."""
    idx = pd.date_range("2023-01-02", periods=520, freq="B")
    closes = np.linspace(120.0, 150.0, 520)
    return pd.DataFrame(
        {
            "Open": closes,
            "High": closes * 1.01,
            "Low": closes * 0.99,
            "Close": closes,
            "Volume": np.full(520, 1_000_000),
        },
        index=idx,
    )


@pytest.fixture
def info_dict():
    return {
        "longName": "Test Corp",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "currentPrice": 150.0,
        "regularMarketPrice": 150.0,
        "regularMarketChangePercent": 1.2,
        "trailingEps": 6.0,
        "bookValue": 20.0,
        "sharesOutstanding": 16.0,
        "trailingPE": 25.0,
        "priceToBook": 7.5,
        "marketCap": 2_400_000_000_000,
        "returnOnEquity": 0.35,
        "dividendYield": 2.0,                    # yfinance percent-units field
        "trailingAnnualDividendYield": 0.02,     # unambiguous decimal
        "beta": 1.2,
        "fiftyTwoWeekHigh": 170.0,
        "fiftyTwoWeekLow": 120.0,
        "enterpriseValue": 2_500_000_000_000,
        # Forward-looking / analyst-estimate fields
        "forwardPE": 22.0,
        "pegRatio": 1.8,
        "recommendationKey": "buy",
        "recommendationMean": 2.2,
        "numberOfAnalystOpinions": 25,
        "targetMeanPrice": 175.0,
        "targetHighPrice": 200.0,
        "targetLowPrice": 150.0,
        "website": "https://example.com",
        "longBusinessSummary": "A synthetic test company.",
    }


# ---------------------------------------------------------------------------
# Fake yfinance.Ticker
# ---------------------------------------------------------------------------

class FakeTicker:
    """Stand-in for yfinance.Ticker exposing only what the pipeline reads."""

    def __init__(self, info, income, balance, cashflow, dividends, history):
        self.info = info
        self.income_stmt = income
        self.balance_sheet = balance
        self.quarterly_balance_sheet = balance
        self.cashflow = cashflow
        self.dividends = dividends
        self._history = history

    def history(self, period="2y", interval="1d", **kwargs):
        return self._history


@pytest.fixture
def fake_ticker(info_dict, income_df, balance_df, cashflow_df,
                dividends_series, price_history):
    return FakeTicker(
        info=info_dict,
        income=income_df,
        balance=balance_df,
        cashflow=cashflow_df,
        dividends=dividends_series,
        history=price_history,
    )


@pytest.fixture
def patch_yfinance(monkeypatch, fake_ticker):
    """Patch yfinance.Ticker globally so every access path returns fake_ticker."""
    import yfinance
    monkeypatch.setattr(yfinance, "Ticker", lambda symbol, *a, **k: fake_ticker)
    return fake_ticker


# ---------------------------------------------------------------------------
# Parsed-data fixtures (plain dicts/lists as the engines consume them)
# ---------------------------------------------------------------------------

@pytest.fixture
def income_annual():
    """income_data['annual'] shape, most-recent first."""
    return [
        {"fiscalDateEnding": "2024-09-30", "totalRevenue": 400.0, "netIncome": 100.0,
         "grossProfit": 180.0, "operatingIncome": 120.0, "ebitda": 130.0, "dilutedEPS": 6.0},
        {"fiscalDateEnding": "2023-09-30", "totalRevenue": 380.0, "netIncome": 95.0,
         "grossProfit": 170.0, "operatingIncome": 113.0, "ebitda": 123.0, "dilutedEPS": 5.6},
        {"fiscalDateEnding": "2022-09-30", "totalRevenue": 365.0, "netIncome": 90.0,
         "grossProfit": 160.0, "operatingIncome": 108.0, "ebitda": 118.0, "dilutedEPS": 5.2},
        {"fiscalDateEnding": "2021-09-30", "totalRevenue": 350.0, "netIncome": 85.0,
         "grossProfit": 150.0, "operatingIncome": 100.0, "ebitda": 110.0, "dilutedEPS": 4.9},
    ]


@pytest.fixture
def cashflow_annual():
    """cashflow_data['annual'] shape, most-recent first."""
    return [
        {"fiscalDateEnding": "2024-09-30", "operatingCashflow": 120.0,
         "capitalExpenditures": -11.0, "freeCashFlow": 109.0, "dividendPayout": -15.0},
        {"fiscalDateEnding": "2023-09-30", "operatingCashflow": 114.0,
         "capitalExpenditures": -10.0, "freeCashFlow": 104.0, "dividendPayout": -14.0},
        {"fiscalDateEnding": "2022-09-30", "operatingCashflow": 108.0,
         "capitalExpenditures": -10.0, "freeCashFlow": 98.0, "dividendPayout": -13.0},
        {"fiscalDateEnding": "2021-09-30", "operatingCashflow": 100.0,
         "capitalExpenditures": -9.0, "freeCashFlow": 91.0, "dividendPayout": -12.0},
    ]


@pytest.fixture
def stock_data():
    """The `stock_data`/`info_metrics` dict the engines receive."""
    return {
        "price": 150.0,
        "eps": 6.0,
        "book_value": 20.0,
        "shares_outstanding": 16.0,
        "current_ratio": 1.15,
        "debt_equity": 1.71,
        "pe_ratio": 25.0,
        "pb_ratio": 7.5,
        "market_cap": 2_400_000_000_000,
        "dividend_years": 12,
        "positive_earnings_years": 4,
        "roe": 0.35,
        "revenue_growth_5y": 0.043,
        "ncav_per_share": 0.0,
        "price_52w_low": 120.0,
        "price_52w_high": 170.0,
        "dividend_yield": 0.02,
    }
