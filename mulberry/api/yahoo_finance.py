"""Yahoo Finance API wrapper using yfinance library"""

import yfinance as yf
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ..utils.logger import get_logger
from ..utils.returns import compute_return_metrics

logger = get_logger(__name__)


class YahooFinanceAPI:
    """
    Yahoo Finance API client using yfinance library

    Provides:
    - Historical price data
    - Dividend history
    - Stock splits
    - Company info
    - Options data
    """

    def __init__(self):
        """Initialize Yahoo Finance API client"""
        pass

    def get_raw_bundle(self, symbol: str, history_period: str = "2y") -> Dict[str, Any]:
        """Fetch the full raw payload the analysis pipeline consumes.

        This is the single place that constructs a yfinance Ticker and reads
        its statement/history/dividend attributes, so there is one Yahoo access
        path rather than duplicated `yf.Ticker` logic across the codebase.
        """
        ticker = yf.Ticker(symbol.upper())
        return {
            "info": ticker.info or {},
            "income_stmt": ticker.income_stmt,
            "quarterly_balance": ticker.quarterly_balance_sheet,
            "annual_balance": ticker.balance_sheet,
            "cashflow": ticker.cashflow,
            "dividends": ticker.dividends,
            # 2 years of history so the 200-day moving average is available
            "history": ticker.history(period=history_period),
        }

    def get_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get company information

        Args:
            symbol: Stock ticker symbol

        Returns:
            Company info dictionary
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info

            return {
                "symbol": symbol.upper(),
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0),
                "enterprise_value": info.get("enterpriseValue", 0),
                "trailing_pe": info.get("trailingPE", 0),
                "forward_pe": info.get("forwardPE", 0),
                "peg_ratio": info.get("pegRatio", 0),
                "price_to_book": info.get("priceToBook", 0),
                "price_to_sales": info.get("priceToSalesTrailing12Months", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "beta": info.get("beta", 0),
                "52week_high": info.get("fiftyTwoWeekHigh", 0),
                "52week_low": info.get("fiftyTwoWeekLow", 0),
                "50day_avg": info.get("fiftyDayAverage", 0),
                "200day_avg": info.get("twoHundredDayAverage", 0),
                "shares_outstanding": info.get("sharesOutstanding", 0),
                "float_shares": info.get("floatShares", 0),
                "website": info.get("website", ""),
                "description": info.get("longBusinessSummary", "")
            }

        except Exception as e:
            logger.error(f"Error getting Yahoo Finance info for {symbol}: {e}")
            raise Exception(f"Failed to get Yahoo Finance data: {e}")

    def get_historical_data(
        self,
        symbol: str,
        period: str = "5y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical price data

        Args:
            symbol: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                raise Exception(f"No historical data available for {symbol}")

            return df

        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            raise Exception(f"Failed to get historical data: {e}")

    def get_dividends(self, symbol: str) -> pd.DataFrame:
        """
        Get dividend history

        Args:
            symbol: Stock ticker symbol

        Returns:
            DataFrame with dividend dates and amounts
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            dividends = ticker.dividends

            if dividends.empty:
                logger.warning(f"No dividend data available for {symbol}")
                return pd.DataFrame()

            return dividends

        except Exception as e:
            logger.error(f"Error getting dividends for {symbol}: {e}")
            return pd.DataFrame()

    def get_splits(self, symbol: str) -> pd.DataFrame:
        """
        Get stock split history

        Args:
            symbol: Stock ticker symbol

        Returns:
            DataFrame with split dates and ratios
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            splits = ticker.splits

            if splits.empty:
                logger.debug(f"No split data available for {symbol}")
                return pd.DataFrame()

            return splits

        except Exception as e:
            logger.error(f"Error getting splits for {symbol}: {e}")
            return pd.DataFrame()

    def get_financials(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        Get financial statements from Yahoo Finance

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with income statement, balance sheet, cash flow
        """
        try:
            ticker = yf.Ticker(symbol.upper())

            return {
                "income_statement": ticker.income_stmt,
                "balance_sheet": ticker.balance_sheet,
                "cash_flow": ticker.cashflow
            }

        except Exception as e:
            logger.error(f"Error getting financials for {symbol}: {e}")
            return {
                "income_statement": pd.DataFrame(),
                "balance_sheet": pd.DataFrame(),
                "cash_flow": pd.DataFrame()
            }

    def get_analyst_recommendations(self, symbol: str) -> pd.DataFrame:
        """
        Get analyst recommendations

        Args:
            symbol: Stock ticker symbol

        Returns:
            DataFrame with analyst recommendations
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            recommendations = ticker.recommendations

            if recommendations is None or recommendations.empty:
                logger.debug(f"No analyst recommendations for {symbol}")
                return pd.DataFrame()

            return recommendations

        except Exception as e:
            logger.error(f"Error getting recommendations for {symbol}: {e}")
            return pd.DataFrame()

    def calculate_returns(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calculate various return metrics

        Args:
            symbol: Stock ticker symbol
            start_date: Start date for calculation
            end_date: End date for calculation

        Returns:
            Dictionary with return metrics
        """
        try:
            # Default to 5 years if not specified
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=365 * 5)

            ticker = yf.Ticker(symbol.upper())
            df = ticker.history(start=start_date, end=end_date)

            if df.empty:
                raise Exception(f"No price data available for {symbol}")

            metrics = compute_return_metrics(df['Close'])
            metrics.update({
                "start_price": float(df['Close'].iloc[0]),
                "end_price": float(df['Close'].iloc[-1]),
                "days": (end_date - start_date).days,
            })
            return metrics

        except Exception as e:
            logger.error(f"Error calculating returns for {symbol}: {e}")
            raise Exception(f"Failed to calculate returns: {e}")
