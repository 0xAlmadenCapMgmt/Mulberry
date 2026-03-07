"""
Alpha Vantage API wrapper
Adapted from StockDashboard project and converted to async with caching support
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import BaseAPIClient
from ..cache.database import CacheManager
from ..utils.logger import get_logger
from ..utils.config import config

logger = get_logger(__name__)


class AlphaVantageAPI(BaseAPIClient):
    """
    Alpha Vantage API client for stock data

    Provides:
    - Company overview and fundamentals
    - Time series price data
    - Income statements
    - Balance sheets
    - Cash flow statements
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None, cache_manager: Optional[CacheManager] = None):
        """
        Initialize Alpha Vantage API client

        Args:
            api_key: Alpha Vantage API key (defaults to config)
            cache_manager: Cache manager instance
        """
        api_key = api_key or config.alpha_vantage_api_key
        if not api_key:
            raise ValueError("Alpha Vantage API key required")

        super().__init__(
            api_key=api_key,
            rate_limit=config.alpha_vantage_rate_limit,
            cache_manager=cache_manager,
            base_url=self.BASE_URL
        )

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote for a symbol

        Args:
            symbol: Stock ticker symbol

        Returns:
            Quote data with price, volume, etc.
        """
        url = self.BASE_URL
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }

        data = await self._fetch(
            url,
            params=params,
            use_cache=True,
            cache_key=f"{symbol.upper()}:quote",
            cache_ttl=config.cache_ttl_quotes
        )

        if "Global Quote" not in data:
            raise Exception(f"No quote data available for {symbol}")

        quote = data["Global Quote"]
        return {
            "symbol": quote.get("01. symbol", ""),
            "price": float(quote.get("05. price", 0)),
            "change": float(quote.get("09. change", 0)),
            "change_percent": quote.get("10. change percent", "0%"),
            "volume": int(quote.get("06. volume", 0)),
            "latest_trading_day": quote.get("07. latest trading day", ""),
            "previous_close": float(quote.get("08. previous close", 0)),
            "open": float(quote.get("02. open", 0)),
            "high": float(quote.get("03. high", 0)),
            "low": float(quote.get("04. low", 0))
        }

    async def get_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company overview and fundamental data
        Adapted from get_company_overview() in StockDashboard

        Args:
            symbol: Stock ticker symbol

        Returns:
            Company overview data
        """
        url = self.BASE_URL
        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }

        data = await self._fetch(
            url,
            params=params,
            use_cache=True,
            cache_key=f"{symbol.upper()}:overview",
            cache_ttl=config.cache_ttl_fundamentals
        )

        if not data or "Symbol" not in data:
            raise Exception(f"No overview data available for {symbol}")

        return data

    async def get_time_series(self, symbol: str, outputsize: str = 'full') -> Dict[str, Any]:
        """
        Get daily adjusted time series data
        Adapted from get_time_series_data() in StockDashboard

        Args:
            symbol: Stock ticker symbol
            outputsize: 'compact' (100 days) or 'full' (20+ years)

        Returns:
            Time series with dates, prices, volumes
        """
        url = self.BASE_URL
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol.upper(),
            "outputsize": outputsize,
            "apikey": self.api_key
        }

        data = await self._fetch(
            url,
            params=params,
            use_cache=True,
            cache_key=f"{symbol.upper()}:timeseries:{outputsize}",
            cache_ttl=config.cache_ttl_quotes
        )

        if "Time Series (Daily)" not in data:
            raise Exception(f"No time series data available for {symbol}")

        time_series = data["Time Series (Daily)"]
        dates = sorted(time_series.keys(), reverse=True)  # Most recent first

        prices = []
        volumes = []
        adjusted_close = []

        for date in dates:
            prices.append(float(time_series[date]["4. close"]))
            adjusted_close.append(float(time_series[date]["5. adjusted close"]))
            volumes.append(int(time_series[date]["6. volume"]))

        return {
            "symbol": symbol.upper(),
            "dates": dates,
            "prices": prices,
            "adjusted_close": adjusted_close,
            "volumes": volumes
        }

    async def get_income_statement(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get income statement data
        Adapted from get_income_statement() in StockDashboard

        Args:
            symbol: Stock ticker symbol

        Returns:
            List of quarterly income statements
        """
        url = self.BASE_URL
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }

        data = await self._fetch(
            url,
            params=params,
            use_cache=True,
            cache_key=f"{symbol.upper()}:income",
            cache_ttl=config.cache_ttl_fundamentals
        )

        if "quarterlyReports" not in data:
            raise Exception(f"No income statement data available for {symbol}")

        quarterly_reports = data["quarterlyReports"][:8]  # Last 8 quarters

        formatted_data = []
        for report in quarterly_reports:
            formatted_data.append({
                "fiscalDateEnding": report.get("fiscalDateEnding", ""),
                "reportedCurrency": report.get("reportedCurrency", ""),
                "totalRevenue": float(report.get("totalRevenue", 0) or 0),
                "netIncome": float(report.get("netIncome", 0) or 0),
                "dilutedEPS": float(report.get("dilutedEPS", 0) or 0),
                "ebitda": float(report.get("ebitda", 0) or 0),
                "grossProfit": float(report.get("grossProfit", 0) or 0),
                "operatingIncome": float(report.get("operatingIncome", 0) or 0),
                "costOfRevenue": float(report.get("costOfRevenue", 0) or 0),
                "researchAndDevelopment": float(report.get("researchAndDevelopment", 0) or 0)
            })

        # Also get annual reports for long-term analysis
        annual_reports = data.get("annualReports", [])[:10]  # Last 10 years
        annual_data = []
        for report in annual_reports:
            annual_data.append({
                "fiscalDateEnding": report.get("fiscalDateEnding", ""),
                "reportedCurrency": report.get("reportedCurrency", ""),
                "totalRevenue": float(report.get("totalRevenue", 0) or 0),
                "netIncome": float(report.get("netIncome", 0) or 0),
                "dilutedEPS": float(report.get("dilutedEPS", 0) or 0),
                "ebitda": float(report.get("ebitda", 0) or 0),
                "grossProfit": float(report.get("grossProfit", 0) or 0),
                "operatingIncome": float(report.get("operatingIncome", 0) or 0)
            })

        return {
            "quarterly": formatted_data,
            "annual": annual_data
        }

    async def get_balance_sheet(self, symbol: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get balance sheet data
        Adapted from get_balance_sheet() in StockDashboard

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with quarterly and annual balance sheets
        """
        url = self.BASE_URL
        params = {
            "function": "BALANCE_SHEET",
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }

        data = await self._fetch(
            url,
            params=params,
            use_cache=True,
            cache_key=f"{symbol.upper()}:balance",
            cache_ttl=config.cache_ttl_fundamentals
        )

        if "quarterlyReports" not in data:
            raise Exception(f"No balance sheet data available for {symbol}")

        quarterly_reports = data["quarterlyReports"][:8]  # Last 8 quarters

        formatted_data = []
        for report in quarterly_reports:
            formatted_data.append({
                "fiscalDateEnding": report.get("fiscalDateEnding", ""),
                "reportedCurrency": report.get("reportedCurrency", ""),
                "totalAssets": float(report.get("totalAssets", 0) or 0),
                "totalLiabilities": float(report.get("totalLiabilities", 0) or 0),
                "totalShareholderEquity": float(report.get("totalShareholderEquity", 0) or 0),
                "currentAssets": float(report.get("totalCurrentAssets", 0) or 0),
                "currentLiabilities": float(report.get("totalCurrentLiabilities", 0) or 0),
                "currentDebt": float(report.get("currentDebt", 0) or 0),
                "longTermDebt": float(report.get("longTermDebt", 0) or 0),
                "cash": float(report.get("cashAndShortTermInvestments", 0) or 0),
                "inventory": float(report.get("inventory", 0) or 0),
                "commonStock": float(report.get("commonStock", 0) or 0),
                "retainedEarnings": float(report.get("retainedEarnings", 0) or 0)
            })

        # Annual reports for long-term trends
        annual_reports = data.get("annualReports", [])[:10]
        annual_data = []
        for report in annual_reports:
            annual_data.append({
                "fiscalDateEnding": report.get("fiscalDateEnding", ""),
                "reportedCurrency": report.get("reportedCurrency", ""),
                "totalAssets": float(report.get("totalAssets", 0) or 0),
                "totalLiabilities": float(report.get("totalLiabilities", 0) or 0),
                "totalShareholderEquity": float(report.get("totalShareholderEquity", 0) or 0),
                "currentAssets": float(report.get("totalCurrentAssets", 0) or 0),
                "currentLiabilities": float(report.get("totalCurrentLiabilities", 0) or 0),
                "currentDebt": float(report.get("currentDebt", 0) or 0),
                "longTermDebt": float(report.get("longTermDebt", 0) or 0),
                "cash": float(report.get("cashAndShortTermInvestments", 0) or 0)
            })

        return {
            "quarterly": formatted_data,
            "annual": annual_data
        }

    async def get_cash_flow(self, symbol: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get cash flow statement data
        Adapted from get_cash_flow() in StockDashboard

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with quarterly and annual cash flows
        """
        url = self.BASE_URL
        params = {
            "function": "CASH_FLOW",
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }

        data = await self._fetch(
            url,
            params=params,
            use_cache=True,
            cache_key=f"{symbol.upper()}:cashflow",
            cache_ttl=config.cache_ttl_fundamentals
        )

        if "quarterlyReports" not in data:
            raise Exception(f"No cash flow data available for {symbol}")

        quarterly_reports = data["quarterlyReports"][:8]

        formatted_data = []
        for report in quarterly_reports:
            operating_cf = float(report.get("operatingCashflow", 0) or 0)
            capex = float(report.get("capitalExpenditures", 0) or 0)

            formatted_data.append({
                "fiscalDateEnding": report.get("fiscalDateEnding", ""),
                "reportedCurrency": report.get("reportedCurrency", ""),
                "operatingCashflow": operating_cf,
                "capitalExpenditures": capex,
                "freeCashFlow": operating_cf - abs(capex),  # CapEx is often negative
                "dividendPayout": float(report.get("dividendPayout", 0) or 0),
                "cashflowFromInvestment": float(report.get("cashflowFromInvestment", 0) or 0),
                "cashflowFromFinancing": float(report.get("cashflowFromFinancing", 0) or 0)
            })

        # Annual reports
        annual_reports = data.get("annualReports", [])[:10]
        annual_data = []
        for report in annual_reports:
            operating_cf = float(report.get("operatingCashflow", 0) or 0)
            capex = float(report.get("capitalExpenditures", 0) or 0)

            annual_data.append({
                "fiscalDateEnding": report.get("fiscalDateEnding", ""),
                "reportedCurrency": report.get("reportedCurrency", ""),
                "operatingCashflow": operating_cf,
                "capitalExpenditures": capex,
                "freeCashFlow": operating_cf - abs(capex),
                "dividendPayout": float(report.get("dividendPayout", 0) or 0)
            })

        return {
            "quarterly": formatted_data,
            "annual": annual_data
        }

    async def get_earnings(self, symbol: str) -> Dict[str, Any]:
        """
        Get earnings history (EPS estimates vs actual)

        Args:
            symbol: Stock ticker symbol

        Returns:
            Earnings data with estimates and actuals
        """
        url = self.BASE_URL
        params = {
            "function": "EARNINGS",
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }

        data = await self._fetch(
            url,
            params=params,
            use_cache=True,
            cache_key=f"{symbol.upper()}:earnings",
            cache_ttl=config.cache_ttl_fundamentals
        )

        return data
