"""
Ben Graham valuation methods
Based on formulas from FINANCIAL_ANALYSIS_SKILLS.md
Implements The Intelligent Investor principles
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import statistics

from ..utils.logger import get_logger
from ..utils.formatters import format_currency, format_percent

logger = get_logger(__name__)


@dataclass
class GrahamValuation:
    """Results from Graham valuation analysis"""
    graham_number: float
    ncav_per_share: float
    normalized_earnings_value: float
    dividend_adjusted_value: float
    current_price: float
    margin_of_safety_graham: float
    margin_of_safety_ncav: float
    margin_of_safety_normalized: float
    margin_of_safety_dividend: float
    avg_margin_of_safety: float
    recommendation: str
    defensive_checklist: Dict[str, Any]
    enterprise_checklist: Dict[str, Any]


class GrahamAnalyzer:
    """
    Ben Graham value investing analysis engine

    Implements four valuation methods:
    1. Graham Number Formula
    2. Net-Net Working Capital (NCAV)
    3. Normalized Earnings Valuation
    4. Dividend-Adjusted Graham Formula

    Reference: FINANCIAL_ANALYSIS_SKILLS.md lines 126-169
    """

    # Constants from Graham's work
    MAX_PE_DEFENSIVE = 15.0
    MAX_PB_DEFENSIVE = 1.5
    MIN_CURRENT_RATIO = 2.0
    MAX_DEBT_EQUITY = 0.5
    MIN_DIVIDEND_YEARS = 20
    MIN_EARNINGS_STABILITY_YEARS = 8
    NCAV_DISCOUNT = 2 / 3  # Buy at 2/3 of NCAV
    AAA_BOND_HISTORICAL = 4.4  # Historical AAA yield constant

    def __init__(self):
        """Initialize Graham Analyzer"""
        pass

    def graham_number(self, eps: float, book_value_per_share: float) -> float:
        """
        Calculate Graham Number

        Formula: √(22.5 × EPS × BVPS)
        Where 22.5 = 15 (max P/E) × 1.5 (max P/B)

        Args:
            eps: Earnings per share (trailing 12 months)
            book_value_per_share: Book value per share

        Returns:
            Graham Number intrinsic value
        """
        if eps <= 0 or book_value_per_share <= 0:
            logger.warning("Graham Number requires positive EPS and book value")
            return 0.0

        try:
            result = (22.5 * eps * book_value_per_share) ** 0.5
            logger.debug(f"Graham Number: ${result:.2f} (EPS={eps}, BVPS={book_value_per_share})")
            return result
        except Exception as e:
            logger.error(f"Error calculating Graham Number: {e}")
            return 0.0

    def net_net_working_capital(
        self,
        current_assets: float,
        total_liabilities: float,
        shares_outstanding: float
    ) -> float:
        """
        Calculate Net Current Asset Value (NCAV) per share

        Formula: (Current Assets - Total Liabilities) / Shares Outstanding
        Buy signal: Stock Price < (2/3 × NCAV per share)

        Args:
            current_assets: Total current assets
            total_liabilities: Total liabilities (current + long-term)
            shares_outstanding: Number of shares outstanding

        Returns:
            NCAV per share
        """
        if shares_outstanding <= 0:
            logger.error("Invalid shares outstanding for NCAV calculation")
            return 0.0

        try:
            ncav = current_assets - total_liabilities
            ncav_per_share = ncav / shares_outstanding

            logger.debug(f"NCAV per share: ${ncav_per_share:.2f}")
            return ncav_per_share
        except Exception as e:
            logger.error(f"Error calculating NCAV: {e}")
            return 0.0

    def normalized_earnings_value(
        self,
        earnings_history: List[float],
        growth_rate: float = 0.0,
        conservative: bool = True
    ) -> float:
        """
        Calculate intrinsic value based on normalized earnings

        Formula: Average Earnings (7-10 years) × Appropriate P/E
        P/E = 8.5 + (2 × expected growth rate)

        Args:
            earnings_history: List of annual EPS for last 7-10 years
            growth_rate: Expected annual growth rate (as decimal, e.g., 0.05 for 5%)
            conservative: Use conservative P/E (10-12) if True

        Returns:
            Intrinsic value based on normalized earnings
        """
        if not earnings_history or len(earnings_history) < 3:
            logger.warning("Insufficient earnings history for normalization")
            return 0.0

        try:
            # Calculate average earnings
            avg_earnings = statistics.mean(earnings_history)

            # Calculate appropriate P/E multiple
            if conservative:
                pe_multiple = min(12.0, 8.5 + (2 * growth_rate * 100))
            else:
                pe_multiple = 8.5 + (2 * growth_rate * 100)

            # Cap at maximum defensive P/E
            pe_multiple = min(pe_multiple, self.MAX_PE_DEFENSIVE)

            value = avg_earnings * pe_multiple

            logger.debug(
                f"Normalized value: ${value:.2f} "
                f"(Avg EPS={avg_earnings:.2f}, P/E={pe_multiple:.1f})"
            )
            return value

        except Exception as e:
            logger.error(f"Error calculating normalized earnings value: {e}")
            return 0.0

    def dividend_adjusted_value(
        self,
        eps: float,
        growth_rate: float,
        aaa_bond_yield: float
    ) -> float:
        """
        Calculate intrinsic value using dividend-adjusted Graham formula

        Formula: (EPS × (8.5 + 2g) × 4.4) / Y
        Where:
            g = Expected annual earnings growth (as decimal)
            Y = Current yield on AAA corporate bonds
            4.4 = Historical average AAA bond yield

        Args:
            eps: Current earnings per share
            growth_rate: Expected growth rate (as decimal, e.g., 0.05 for 5%)
            aaa_bond_yield: Current AAA corporate bond yield (as decimal)

        Returns:
            Intrinsic value adjusted for growth and interest rates
        """
        if eps <= 0:
            logger.warning("Dividend-adjusted formula requires positive EPS")
            return 0.0

        if aaa_bond_yield <= 0:
            logger.warning("Using historical AAA yield (4.4%) as fallback")
            aaa_bond_yield = self.AAA_BOND_HISTORICAL / 100

        try:
            # Convert growth rate to percentage if needed
            g = growth_rate * 100 if growth_rate < 1 else growth_rate

            value = (eps * (8.5 + 2 * g) * self.AAA_BOND_HISTORICAL) / (aaa_bond_yield * 100)

            logger.debug(
                f"Dividend-adjusted value: ${value:.2f} "
                f"(EPS={eps}, g={g}%, AAA={aaa_bond_yield*100:.2f}%)"
            )
            return value

        except Exception as e:
            logger.error(f"Error calculating dividend-adjusted value: {e}")
            return 0.0

    def margin_of_safety(self, intrinsic_value: float, market_price: float) -> float:
        """
        Calculate margin of safety

        Formula: (Intrinsic Value - Market Price) / Intrinsic Value
        Target: ≥ 30% for defensive investors, ≥ 50% for enterprising

        Args:
            intrinsic_value: Calculated intrinsic value
            market_price: Current market price

        Returns:
            Margin of safety as decimal (e.g., 0.30 = 30%)
        """
        if intrinsic_value <= 0:
            return -1.0  # Invalid

        margin = (intrinsic_value - market_price) / intrinsic_value
        return margin

    def defensive_investor_checklist(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate stock against defensive investor criteria

        8-point checklist from The Intelligent Investor:
        1. Current ratio ≥ 2.0
        2. Long-term debt < Net working capital
        3. No losses in past 10 years
        4. Continuous dividends for 20+ years
        5. P/E ratio ≤ 15
        6. P/B ratio ≤ 1.5
        7. P/E × P/B ≤ 22.5
        8. Adequate size (market cap > $2B in modern terms)

        Args:
            stock_data: Dictionary with financial metrics

        Returns:
            Dictionary with pass/fail for each criterion
        """
        results = {}

        # 1. Current ratio
        current_ratio = stock_data.get('current_ratio', 0)
        results['current_ratio'] = {
            'pass': current_ratio >= self.MIN_CURRENT_RATIO,
            'value': current_ratio,
            'target': f'>= {self.MIN_CURRENT_RATIO}',
            'description': 'Strong liquidity position'
        }

        # 2. Debt-to-equity
        debt_equity = stock_data.get('debt_equity', 999)
        results['debt_to_equity'] = {
            'pass': debt_equity < self.MAX_DEBT_EQUITY,
            'value': debt_equity,
            'target': f'< {self.MAX_DEBT_EQUITY}',
            'description': 'Conservative capital structure'
        }

        # 3. Earnings stability
        positive_earnings_years = stock_data.get('positive_earnings_years', 0)
        results['earnings_stability'] = {
            'pass': positive_earnings_years >= self.MIN_EARNINGS_STABILITY_YEARS,
            'value': positive_earnings_years,
            'target': f'>= {self.MIN_EARNINGS_STABILITY_YEARS} years',
            'description': 'Consistent profitability'
        }

        # 4. Dividend record
        dividend_years = stock_data.get('dividend_years', 0)
        results['dividend_record'] = {
            'pass': dividend_years >= self.MIN_DIVIDEND_YEARS,
            'value': dividend_years,
            'target': f'>= {self.MIN_DIVIDEND_YEARS} years',
            'description': 'Long dividend history'
        }

        # 5. P/E ratio
        pe_ratio = stock_data.get('pe_ratio', 999)
        results['pe_ratio'] = {
            'pass': 0 < pe_ratio <= self.MAX_PE_DEFENSIVE,
            'value': pe_ratio,
            'target': f'<= {self.MAX_PE_DEFENSIVE}',
            'description': 'Reasonable earnings multiple'
        }

        # 6. P/B ratio
        pb_ratio = stock_data.get('pb_ratio', 999)
        results['pb_ratio'] = {
            'pass': 0 < pb_ratio <= self.MAX_PB_DEFENSIVE,
            'value': pb_ratio,
            'target': f'<= {self.MAX_PB_DEFENSIVE}',
            'description': 'Trading near or below book value'
        }

        # 7. Combined P/E × P/B test
        combined = pe_ratio * pb_ratio if pe_ratio > 0 and pb_ratio > 0 else 999
        results['combined_test'] = {
            'pass': combined <= 22.5,
            'value': combined,
            'target': '<= 22.5',
            'description': 'Graham Number criterion'
        }

        # 8. Adequate size
        market_cap = stock_data.get('market_cap', 0)
        results['adequate_size'] = {
            'pass': market_cap >= 2_000_000_000,  # $2B minimum
            'value': market_cap,
            'target': '>= $2B',
            'description': 'Large, established company'
        }

        # Calculate overall pass rate
        passed = sum(1 for r in results.values() if r['pass'])
        total = len(results)
        results['summary'] = {
            'passed': passed,
            'total': total,
            'pass_rate': passed / total,
            'overall_pass': passed >= 6  # At least 75% criteria met
        }

        return results

    def enterprising_investor_checklist(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate stock for enterprising investor opportunities

        Criteria for deep value / special situations:
        1. Trading below working capital (net-net)
        2. P/E < 7 with improving prospects
        3. Strong financial position + low valuation
        4. Unpopular but fundamentally sound
        5. Price < 2/3 NCAV (extreme bargain)

        Args:
            stock_data: Dictionary with financial metrics

        Returns:
            Dictionary with opportunity assessment
        """
        results = {}

        # 1. Net-net opportunity
        price = stock_data.get('price', 0)
        ncav_per_share = stock_data.get('ncav_per_share', 0)
        net_net_buy_price = ncav_per_share * self.NCAV_DISCOUNT

        results['net_net'] = {
            'opportunity': price < net_net_buy_price if price > 0 and ncav_per_share > 0 else False,
            'price': price,
            'target_price': net_net_buy_price,
            'discount': (net_net_buy_price - price) / net_net_buy_price if net_net_buy_price > 0 else 0,
            'description': 'Extreme deep value (Ben Graham\'s favorite)'
        }

        # 2. Low P/E with growth
        pe_ratio = stock_data.get('pe_ratio', 999)
        revenue_growth = stock_data.get('revenue_growth_5y', 0)

        results['low_pe_growth'] = {
            'opportunity': pe_ratio < 7 and revenue_growth > 0,
            'pe': pe_ratio,
            'growth': revenue_growth,
            'description': 'Undervalued growth opportunity'
        }

        # 3. Financial strength + low valuation
        current_ratio = stock_data.get('current_ratio', 0)
        debt_equity = stock_data.get('debt_equity', 999)
        pb_ratio = stock_data.get('pb_ratio', 999)

        strong_finances = current_ratio >= 2.0 and debt_equity < 0.3
        low_valuation = pb_ratio < 1.0 and pe_ratio < 10

        results['strong_cheap'] = {
            'opportunity': strong_finances and low_valuation,
            'current_ratio': current_ratio,
            'debt_equity': debt_equity,
            'pb_ratio': pb_ratio,
            'description': 'Financially strong but undervalued'
        }

        # 4. Unpopular / contrarian
        price_52w_low = stock_data.get('price_52w_low', 0)
        price_52w_high = stock_data.get('price_52w_high', 999)

        if price_52w_high > 0 and price > 0:
            price_position = (price - price_52w_low) / (price_52w_high - price_52w_low)
            unpopular = price_position < 0.3  # In bottom 30% of 52-week range
        else:
            unpopular = False
            price_position = 0

        results['contrarian'] = {
            'opportunity': unpopular and stock_data.get('roe', 0) > 0.10,
            'price_position': price_position,
            'description': 'Out of favor but fundamentally sound'
        }

        # Calculate overall opportunity score
        opportunities = sum(1 for r in results.values() if isinstance(r, dict) and r.get('opportunity', False))
        results['summary'] = {
            'opportunities': opportunities,
            'high_conviction': opportunities >= 2,
            'description': 'Suitable for enterprising investor' if opportunities >= 2 else 'Limited opportunities'
        }

        return results

    def comprehensive_analysis(
        self,
        eps: float,
        book_value_per_share: float,
        current_assets: float,
        total_liabilities: float,
        shares_outstanding: float,
        current_price: float,
        earnings_history: List[float],
        growth_rate: float = 0.05,
        aaa_yield: float = 0.05,
        stock_data: Optional[Dict[str, Any]] = None
    ) -> GrahamValuation:
        """
        Perform comprehensive Graham analysis with all four methods

        Args:
            eps: Current earnings per share
            book_value_per_share: Book value per share
            current_assets: Total current assets
            total_liabilities: Total liabilities
            shares_outstanding: Shares outstanding
            current_price: Current market price
            earnings_history: List of historical EPS
            growth_rate: Expected growth rate (decimal)
            aaa_yield: Current AAA bond yield (decimal)
            stock_data: Additional stock metrics for checklists

        Returns:
            GrahamValuation object with complete analysis
        """
        logger.info(f"Performing comprehensive Graham analysis (Price: ${current_price:.2f})")

        # Calculate all four valuation methods
        graham_num = self.graham_number(eps, book_value_per_share)
        ncav = self.net_net_working_capital(current_assets, total_liabilities, shares_outstanding)
        normalized = self.normalized_earnings_value(earnings_history, growth_rate)
        dividend_adj = self.dividend_adjusted_value(eps, growth_rate, aaa_yield)

        # Calculate margins of safety
        mos_graham = self.margin_of_safety(graham_num, current_price)
        mos_ncav = self.margin_of_safety(ncav * self.NCAV_DISCOUNT, current_price)
        mos_normalized = self.margin_of_safety(normalized, current_price)
        mos_dividend = self.margin_of_safety(dividend_adj, current_price)

        # Average margin of safety (excluding invalid values)
        valid_margins = [m for m in [mos_graham, mos_ncav, mos_normalized, mos_dividend] if m >= 0]
        avg_mos = statistics.mean(valid_margins) if valid_margins else -1.0

        # Generate recommendation
        recommendation = self._generate_recommendation(avg_mos, mos_graham, stock_data)

        # Run checklists
        defensive_check = self.defensive_investor_checklist(stock_data or {})
        enterprising_check = self.enterprising_investor_checklist(stock_data or {})

        return GrahamValuation(
            graham_number=graham_num,
            ncav_per_share=ncav,
            normalized_earnings_value=normalized,
            dividend_adjusted_value=dividend_adj,
            current_price=current_price,
            margin_of_safety_graham=mos_graham,
            margin_of_safety_ncav=mos_ncav,
            margin_of_safety_normalized=mos_normalized,
            margin_of_safety_dividend=mos_dividend,
            avg_margin_of_safety=avg_mos,
            recommendation=recommendation,
            defensive_checklist=defensive_check,
            enterprise_checklist=enterprising_check
        )

    def _generate_recommendation(
        self,
        avg_margin: float,
        graham_margin: float,
        stock_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate investment recommendation based on analysis"""

        if avg_margin >= 0.50:
            return "STRONG BUY - Exceptional margin of safety (50%+)"
        elif avg_margin >= 0.30:
            return "BUY - Adequate margin of safety for defensive investor (30%+)"
        elif avg_margin >= 0.15:
            return "HOLD - Modest margin, suitable only for enterprising investor"
        elif avg_margin >= 0:
            return "AVOID - Insufficient margin of safety"
        else:
            return "SELL - Trading above intrinsic value"
