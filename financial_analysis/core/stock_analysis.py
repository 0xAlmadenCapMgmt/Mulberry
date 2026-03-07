"""Stock analysis integrating multiple data sources and Graham analysis"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..api.alpha_vantage import AlphaVantageAPI
from ..api.yahoo_finance import YahooFinanceAPI
from ..cache.database import CacheManager
from ..utils.logger import get_logger
from ..utils.config import config
from .graham import GrahamAnalyzer

logger = get_logger(__name__)


class StockAnalyzer:
    """
    Comprehensive stock analysis integrating multiple data sources

    Features:
    - Parallel API calls for faster data fetching
    - Ben Graham valuation analysis
    - Financial strength metrics
    - Growth and profitability analysis
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        Initialize stock analyzer

        Args:
            cache_manager: Optional cache manager for API calls
        """
        self.cache = cache_manager or CacheManager(str(config.cache_db_path))
        self.alpha_vantage = AlphaVantageAPI(cache_manager=self.cache)
        self.yahoo = YahooFinanceAPI()
        self.graham = GrahamAnalyzer()

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        """
        Perform comprehensive stock analysis

        Args:
            symbol: Stock ticker symbol

        Returns:
            Complete analysis dictionary
        """
        logger.info(f"Starting comprehensive analysis for {symbol}")

        try:
            # Fetch data from multiple sources in parallel
            quote, overview, income, balance, cashflow, yf_info = await asyncio.gather(
                self.alpha_vantage.get_quote(symbol),
                self.alpha_vantage.get_overview(symbol),
                self.alpha_vantage.get_income_statement(symbol),
                self.alpha_vantage.get_balance_sheet(symbol),
                self.alpha_vantage.get_cash_flow(symbol),
                asyncio.to_thread(self.yahoo.get_info, symbol),
                return_exceptions=True
            )

            # Handle exceptions
            if isinstance(quote, Exception):
                logger.error(f"Quote fetch failed: {quote}")
                raise quote
            if isinstance(overview, Exception):
                logger.error(f"Overview fetch failed: {overview}")
                raise overview

            # Extract key metrics
            current_price = quote['price']
            eps = float(overview.get('EPS', 0))
            book_value = float(overview.get('BookValue', 0))
            shares_outstanding = float(overview.get('SharesOutstanding', 0))

            # Get latest balance sheet data
            latest_balance = balance['quarterly'][0] if not isinstance(balance, Exception) and balance.get('quarterly') else {}
            current_assets = latest_balance.get('currentAssets', 0)
            total_liabilities = latest_balance.get('totalLiabilities', 0)

            # Build earnings history
            earnings_history = []
            if not isinstance(income, Exception) and income.get('annual'):
                earnings_history = [
                    report['dilutedEPS']
                    for report in income['annual']
                    if report.get('dilutedEPS', 0) != 0
                ][:10]

            # Estimate growth rate from earnings history
            growth_rate = self._calculate_growth_rate(earnings_history)

            # Prepare stock data for Graham analysis
            stock_data = {
                'price': current_price,
                'eps': eps,
                'book_value': book_value,
                'shares_outstanding': shares_outstanding,
                'current_ratio': self._calculate_current_ratio(latest_balance),
                'debt_equity': self._calculate_debt_equity(latest_balance),
                'pe_ratio': float(overview.get('PERatio', 0)),
                'pb_ratio': float(overview.get('PriceToBookRatio', 0)),
                'market_cap': float(overview.get('MarketCapitalization', 0)),
                'dividend_years': self._estimate_dividend_years(yf_info),
                'positive_earnings_years': len([e for e in earnings_history if e > 0]),
                'roe': float(overview.get('ReturnOnEquityTTM', 0)),
                'revenue_growth_5y': self._calculate_revenue_growth(income),
                'ncav_per_share': 0,  # Will be calculated by Graham analyzer
            }

            # Add Yahoo Finance data if available
            if not isinstance(yf_info, Exception):
                stock_data.update({
                    'price_52w_low': yf_info.get('52week_low', 0),
                    'price_52w_high': yf_info.get('52week_high', 0),
                    'dividend_yield': yf_info.get('dividend_yield', 0),
                })

            # Perform Graham analysis
            graham_analysis = self.graham.comprehensive_analysis(
                eps=eps,
                book_value_per_share=book_value,
                current_assets=current_assets,
                total_liabilities=total_liabilities,
                shares_outstanding=shares_outstanding,
                current_price=current_price,
                earnings_history=earnings_history,
                growth_rate=growth_rate,
                aaa_yield=0.05,  # Default 5%, should be fetched from FRED in full implementation
                stock_data=stock_data
            )

            # Build comprehensive result
            result = {
                'symbol': symbol.upper(),
                'analysis_date': datetime.now().isoformat(),
                'quote': quote,
                'overview': overview,
                'current_price': current_price,
                'valuation': {
                    'graham_number': graham_analysis.graham_number,
                    'ncav_per_share': graham_analysis.ncav_per_share,
                    'normalized_value': graham_analysis.normalized_earnings_value,
                    'dividend_adjusted_value': graham_analysis.dividend_adjusted_value,
                    'avg_intrinsic_value': (
                        graham_analysis.graham_number +
                        graham_analysis.normalized_earnings_value +
                        graham_analysis.dividend_adjusted_value
                    ) / 3,
                    'margins_of_safety': {
                        'graham': graham_analysis.margin_of_safety_graham,
                        'ncav': graham_analysis.margin_of_safety_ncav,
                        'normalized': graham_analysis.margin_of_safety_normalized,
                        'dividend_adjusted': graham_analysis.margin_of_safety_dividend,
                        'average': graham_analysis.avg_margin_of_safety
                    }
                },
                'recommendation': graham_analysis.recommendation,
                'defensive_checklist': graham_analysis.defensive_checklist,
                'enterprising_checklist': graham_analysis.enterprise_checklist,
                'financial_statements': {
                    'income': income if not isinstance(income, Exception) else {},
                    'balance': balance if not isinstance(balance, Exception) else {},
                    'cashflow': cashflow if not isinstance(cashflow, Exception) else {}
                },
                'metrics': stock_data
            }

            logger.info(f"Analysis complete for {symbol}")
            logger.info(f"Recommendation: {graham_analysis.recommendation}")

            return result

        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            raise Exception(f"Stock analysis failed: {e}")

        finally:
            await self.alpha_vantage.close()

    def _calculate_current_ratio(self, balance_sheet: Dict[str, Any]) -> float:
        """Calculate current ratio from balance sheet"""
        current_assets = balance_sheet.get('currentAssets', 0)
        current_liabilities = balance_sheet.get('currentLiabilities', 1)

        if current_liabilities == 0:
            return 0.0

        return current_assets / current_liabilities

    def _calculate_debt_equity(self, balance_sheet: Dict[str, Any]) -> float:
        """Calculate debt-to-equity ratio"""
        total_debt = (
            balance_sheet.get('longTermDebt', 0) +
            balance_sheet.get('currentDebt', 0)
        )
        equity = balance_sheet.get('totalShareholderEquity', 1)

        if equity <= 0:
            return 999.0  # Invalid

        return total_debt / equity

    def _calculate_growth_rate(self, earnings_history: list) -> float:
        """Calculate compound annual growth rate from earnings history"""
        if len(earnings_history) < 2:
            return 0.0

        # Filter out zeros and negatives
        positive_earnings = [e for e in earnings_history if e > 0]

        if len(positive_earnings) < 2:
            return 0.0

        try:
            start = positive_earnings[-1]
            end = positive_earnings[0]
            years = len(positive_earnings) - 1

            if years <= 0 or start <= 0:
                return 0.0

            cagr = (end / start) ** (1 / years) - 1
            return max(0.0, min(cagr, 0.30))  # Cap at 30%

        except Exception as e:
            logger.error(f"Growth rate calculation error: {e}")
            return 0.0

    def _estimate_dividend_years(self, yf_info: Dict[str, Any]) -> int:
        """Estimate continuous dividend years from Yahoo Finance data"""
        # This is a placeholder - in full implementation, would analyze dividend history
        dividend_yield = yf_info.get('dividend_yield', 0) if isinstance(yf_info, dict) else 0

        if dividend_yield > 0:
            return 10  # Conservative estimate
        return 0

    def _calculate_revenue_growth(self, income_statements: Dict[str, Any]) -> float:
        """Calculate 5-year revenue CAGR"""
        if not isinstance(income_statements, dict) or not income_statements.get('annual'):
            return 0.0

        annual = income_statements['annual']
        if len(annual) < 2:
            return 0.0

        try:
            revenues = [r['totalRevenue'] for r in annual if r.get('totalRevenue', 0) > 0]

            if len(revenues) < 2:
                return 0.0

            start = revenues[-1]
            end = revenues[0]
            years = min(len(revenues) - 1, 5)

            if years <= 0 or start <= 0:
                return 0.0

            cagr = (end / start) ** (1 / years) - 1
            return cagr

        except Exception as e:
            logger.error(f"Revenue growth calculation error: {e}")
            return 0.0
