"""Stock analysis using Yahoo Finance as the sole data source"""

import asyncio
import statistics
from typing import Dict, Any, Optional
from datetime import datetime

import pandas as pd

from ..api.yahoo_finance import YahooFinanceAPI
from ..cache.raw_cache import RawDataCache
from ..utils.logger import get_logger
from ..utils.config import config
from .graham import GrahamAnalyzer
from .quality import QualityAnalyzer
from .growth import GrowthAnalyzer
from .dcf import DCFValuator
from .dividend import DividendAnalyzer
from .technicals import MomentumAnalyzer
from .composite import CompositeScorer
from .multiples import compute_valuation_multiples
from .forward import extract_forward_context
from . import data_quality
from . import relative

logger = get_logger(__name__)


class StockAnalyzer:
    """
    Comprehensive multi-framework stock analysis using Yahoo Finance

    Fetches all data from yfinance (no API key required), runs six analysis
    frameworks (Graham value, DCF, quality, growth, dividend, momentum),
    and returns a structured result dict for report generation.
    """

    def __init__(
        self,
        raw_cache: Optional[RawDataCache] = None,
        profile: str = "balanced",
    ):
        self.yahoo = YahooFinanceAPI()
        self.raw_cache = raw_cache or RawDataCache(
            config.cache_dir, config.cache_ttl_fundamentals
        )
        self.valuation_engine = GrahamAnalyzer()
        self.quality_engine = QualityAnalyzer()
        self.growth_engine = GrowthAnalyzer()
        self.dcf_engine = DCFValuator()
        self.dividend_engine = DividendAnalyzer()
        self.momentum_engine = MomentumAnalyzer()
        self.composite_engine = CompositeScorer(profile)

    async def analyze(
        self, symbol: str, peers: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive stock analysis.

        Runs all yfinance network calls in a single background thread to keep
        the async CLI responsive, then processes the results synchronously.
        When `peers` are given, also builds a peer-relative comparison (each
        peer fetched through the same cached path).
        """
        logger.info(f"Starting analysis for {symbol}")

        try:
            raw = await asyncio.to_thread(self._fetch_yf_data, symbol.upper())
        except Exception as e:
            logger.error(f"Data fetch failed for {symbol}: {e}")
            raise Exception(f"Failed to fetch data for {symbol}: {e}")

        result = self._build_analysis(symbol.upper(), raw)

        if peers:
            result["peer_comparison"] = await asyncio.to_thread(
                self._peer_comparison, symbol.upper(), raw, peers
            )

        return result

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_yf_data(self, symbol: str) -> Dict:
        """Fetch the raw yfinance bundle, served from cache when fresh.

        Runs in a thread pool. All Yahoo access goes through YahooFinanceAPI so
        there is a single access path; the pickle cache avoids re-downloading on
        repeat runs within the fundamentals TTL.
        """
        cached = self.raw_cache.get(symbol)
        if cached is not None:
            return cached
        bundle = self.yahoo.get_raw_bundle(symbol)
        self.raw_cache.set(symbol, bundle)
        return bundle

    # ------------------------------------------------------------------
    # Analysis pipeline
    # ------------------------------------------------------------------

    def _build_analysis(self, symbol: str, raw: Dict) -> Dict[str, Any]:
        info = raw["info"]

        # --- Core price and per-share data from ticker.info ---
        current_price = float(
            info.get("currentPrice") or info.get("regularMarketPrice") or 0
        )
        if current_price == 0:
            raise Exception("Could not determine current price from Yahoo Finance")

        eps = float(info.get("trailingEps") or 0)
        book_value = float(info.get("bookValue") or 0)
        shares_outstanding = float(info.get("sharesOutstanding") or 0)
        pe_ratio = float(info.get("trailingPE") or 0)
        pb_ratio = float(info.get("priceToBook") or 0)
        market_cap = float(info.get("marketCap") or 0)
        roe = float(info.get("returnOnEquity") or 0)
        dividend_yield = self._normalize_dividend_yield(info)
        beta = float(info.get("beta") or 0)
        price_52w_high = float(info.get("fiftyTwoWeekHigh") or 0)
        price_52w_low = float(info.get("fiftyTwoWeekLow") or 0)
        price_change_pct = float(info.get("regularMarketChangePercent") or 0)

        # --- Parse financial statements ---
        income_data = self._parse_income_stmt(raw["income_stmt"])
        balance_data = self._parse_balance_sheet(
            raw["quarterly_balance"], raw["annual_balance"]
        )
        cashflow_data = self._parse_cashflow(raw["cashflow"])

        # Most-recent quarter balance sheet for NCAV / ratios
        latest_balance = balance_data["quarterly"]
        current_assets = latest_balance.get("currentAssets", 0)
        total_liabilities = latest_balance.get("totalLiabilities", 0)

        # --- Derived metrics ---
        earnings_history = income_data.get("eps_history", [])
        growth_rate = self._calculate_growth_rate(earnings_history)
        current_ratio = self._calculate_current_ratio(latest_balance)
        debt_equity = self._calculate_debt_equity(latest_balance)
        dividend_years = self._calculate_dividend_years(raw["dividends"])

        stock_data = {
            "price": current_price,
            "eps": eps,
            "book_value": book_value,
            "shares_outstanding": shares_outstanding,
            "current_ratio": current_ratio,
            "debt_equity": debt_equity,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "market_cap": market_cap,
            "dividend_years": dividend_years,
            "positive_earnings_years": len([e for e in earnings_history if e > 0]),
            "roe": roe,
            "revenue_growth_5y": income_data.get("revenue_cagr", 0),
            "ncav_per_share": 0,  # computed by valuation engine below
            "price_52w_low": price_52w_low,
            "price_52w_high": price_52w_high,
            "dividend_yield": dividend_yield,
        }

        # --- Valuation analysis ---
        valuation = self.valuation_engine.comprehensive_analysis(
            eps=eps,
            book_value_per_share=book_value,
            current_assets=current_assets,
            total_liabilities=total_liabilities,
            shares_outstanding=shares_outstanding,
            current_price=current_price,
            earnings_history=earnings_history,
            growth_rate=growth_rate,
            aaa_yield=config.aaa_bond_yield,
            stock_data=stock_data,
        )

        avg_intrinsic = self._avg_intrinsic_value(valuation)

        # --- Expanded framework analysis ---
        income_annual = income_data.get("annual", [])
        cashflow_annual = cashflow_data.get("annual", [])
        fcf_history = [r.get("freeCashFlow", 0) for r in cashflow_annual]

        # --- Relative-valuation multiples & forward-looking context ---
        enterprise_value = float(info.get("enterpriseValue") or 0)
        latest_ebitda = income_annual[0].get("ebitda", 0) if income_annual else 0
        latest_revenue = income_annual[0].get("totalRevenue", 0) if income_annual else 0
        latest_fcf = fcf_history[0] if fcf_history else 0
        multiples = compute_valuation_multiples(
            enterprise_value=enterprise_value,
            ebitda=latest_ebitda,
            revenue=latest_revenue,
            market_cap=market_cap,
            free_cash_flow=latest_fcf,
        )
        forward = extract_forward_context(info, current_price)

        quality = self.quality_engine.analyze(stock_data, income_annual, cashflow_annual)
        growth = self.growth_engine.analyze(stock_data, income_annual, cashflow_annual)
        dividend = self.dividend_engine.analyze(stock_data, cashflow_annual, raw["dividends"])
        momentum = self.momentum_engine.analyze(raw["history"], stock_data)

        total_debt = latest_balance.get("longTermDebt", 0) + latest_balance.get("currentDebt", 0)
        dcf = self.dcf_engine.valuate(
            fcf_history=fcf_history,
            shares_outstanding=shares_outstanding,
            current_price=current_price,
            cash=latest_balance.get("cash", 0),
            total_debt=total_debt,
        )

        composite = self.composite_engine.score(
            value_margin_of_safety=valuation.avg_margin_of_safety,
            dcf_margin_of_safety=dcf.margin_of_safety,
            quality=quality,
            growth=growth,
            dividend=dividend,
            momentum=momentum,
        )

        # --- Data confidence: how much required input was actually available ---
        history_rows = 0
        hist = raw.get("history")
        if isinstance(hist, pd.DataFrame) and "Close" in hist:
            history_rows = int(hist["Close"].dropna().shape[0])
        confidence = data_quality.assess(
            eps=eps,
            book_value=book_value,
            shares_outstanding=shares_outstanding,
            current_assets=current_assets,
            total_liabilities=total_liabilities,
            roe=roe,
            pe_ratio=pe_ratio,
            earnings_history=earnings_history,
            income_annual=income_annual,
            cashflow_annual=cashflow_annual,
            fcf_history=fcf_history,
            history_rows=history_rows,
            pays_dividend=dividend.pays_dividend,
            dividend_years=dividend_years,
        )

        return {
            "symbol": symbol,
            "analysis_date": datetime.now().isoformat(),
            "company_info": {
                "name": info.get("longName", symbol),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "website": info.get("website", ""),
                "description": info.get("longBusinessSummary", ""),
            },
            "current_price": current_price,
            "price_change_pct": price_change_pct,
            "valuation": {
                "graham_number": valuation.graham_number,
                "ncav_per_share": valuation.ncav_per_share,
                "normalized_value": valuation.normalized_earnings_value,
                "dividend_adjusted_value": valuation.dividend_adjusted_value,
                "avg_intrinsic_value": avg_intrinsic,
                "margins_of_safety": {
                    "graham": valuation.margin_of_safety_graham,
                    "ncav": valuation.margin_of_safety_ncav,
                    "normalized": valuation.margin_of_safety_normalized,
                    "dividend_adjusted": valuation.margin_of_safety_dividend,
                    "average": valuation.avg_margin_of_safety,
                },
            },
            "recommendation": composite.recommendation,
            "graham_recommendation": valuation.recommendation,
            "profile": composite.profile,
            "multiples": multiples,
            "forward": forward,
            "data_confidence": confidence,
            "defensive_checklist": valuation.defensive_checklist,
            "enterprising_checklist": valuation.enterprise_checklist,
            "frameworks": {
                "quality": quality,
                "growth": growth,
                "dividend": dividend,
                "momentum": momentum,
                "dcf": dcf,
                "composite": composite,
            },
            "financial_statements": {
                "income": income_data,
                "balance": balance_data,
                "cashflow": cashflow_data,
            },
            "metrics": {**stock_data, "beta": beta, "dividend_yield": dividend_yield},
            "history": raw["history"],
        }

    # ------------------------------------------------------------------
    # DataFrame parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_get(df: pd.DataFrame, col, names) -> float:
        """Extract a value from a DataFrame by trying a list of row names."""
        if isinstance(names, str):
            names = [names]
        for name in names:
            if name in df.index:
                val = df.loc[name, col]
                if not pd.isna(val):
                    return float(val)
        return 0.0

    def _parse_income_stmt(self, df: Optional[pd.DataFrame]) -> Dict:
        if df is None or df.empty:
            return {"annual": [], "eps_history": [], "revenue_cagr": 0.0}

        annual_data = []
        eps_history = []

        for col in df.columns:  # most-recent first
            date_str = str(col.date()) if hasattr(col, "date") else str(col)
            eps = self._safe_get(df, col, ["Diluted EPS", "Basic EPS"])
            row = {
                "fiscalDateEnding": date_str,
                "totalRevenue": self._safe_get(df, col, "Total Revenue"),
                "netIncome": self._safe_get(df, col, "Net Income"),
                "grossProfit": self._safe_get(df, col, "Gross Profit"),
                "operatingIncome": self._safe_get(df, col, "Operating Income"),
                "ebitda": self._safe_get(df, col, "EBITDA"),
                "dilutedEPS": eps,
            }
            annual_data.append(row)
            if eps != 0:
                eps_history.append(eps)

        # Revenue CAGR (up to 5 years)
        revenues = [r["totalRevenue"] for r in annual_data if r["totalRevenue"] > 0]
        revenue_cagr = 0.0
        if len(revenues) >= 2:
            try:
                years = min(len(revenues) - 1, 5)
                revenue_cagr = (revenues[0] / revenues[-1]) ** (1 / years) - 1
            except Exception:
                revenue_cagr = 0.0

        return {
            "annual": annual_data,
            "eps_history": eps_history,
            "revenue_cagr": revenue_cagr,
        }

    def _parse_balance_sheet(
        self,
        quarterly_df: Optional[pd.DataFrame],
        annual_df: Optional[pd.DataFrame],
    ) -> Dict:
        def extract(df):
            if df is None or df.empty:
                return {}
            col = df.columns[0]
            return {
                "currentAssets": self._safe_get(df, col, "Current Assets"),
                "currentLiabilities": self._safe_get(df, col, "Current Liabilities"),
                "totalAssets": self._safe_get(df, col, "Total Assets"),
                "totalLiabilities": self._safe_get(
                    df, col, "Total Liabilities Net Minority Interest"
                ),
                "totalShareholderEquity": self._safe_get(
                    df,
                    col,
                    ["Stockholders Equity", "Total Equity Gross Minority Interest"],
                ),
                "longTermDebt": self._safe_get(df, col, "Long Term Debt"),
                "currentDebt": self._safe_get(
                    df, col, ["Current Debt", "Short Term Debt"]
                ),
                "cash": self._safe_get(
                    df,
                    col,
                    [
                        "Cash And Cash Equivalents",
                        "Cash Cash Equivalents And Short Term Investments",
                    ],
                ),
            }

        return {"quarterly": extract(quarterly_df), "annual": extract(annual_df)}

    def _parse_cashflow(self, df: Optional[pd.DataFrame]) -> Dict:
        if df is None or df.empty:
            return {"annual": []}

        annual_data = []
        for col in df.columns:
            date_str = str(col.date()) if hasattr(col, "date") else str(col)
            op_cf = self._safe_get(
                df,
                col,
                ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
            )
            capex = self._safe_get(df, col, ["Capital Expenditure", "Capital Expenditures"])
            annual_data.append(
                {
                    "fiscalDateEnding": date_str,
                    "operatingCashflow": op_cf,
                    "capitalExpenditures": capex,
                    "freeCashFlow": op_cf - abs(capex),
                    "dividendPayout": self._safe_get(
                        df,
                        col,
                        ["Common Stock Dividend Paid", "Payment Of Dividends"],
                    ),
                }
            )

        return {"annual": annual_data}

    # ------------------------------------------------------------------
    # Derived metric helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_dividend_yield(info: Dict) -> float:
        """Return dividend yield as a clean decimal (e.g. 0.0034 for 0.34%).

        yfinance's `dividendYield` field is inconsistent across versions — current
        releases return it in percent units (0.34 meaning 0.34%, not 34%). Prefer
        `trailingAnnualDividendYield`, which is an unambiguous decimal; otherwise
        fall back to `dividendYield` interpreted as percent units.
        """
        trailing = info.get("trailingAnnualDividendYield")
        if trailing:
            return float(trailing)
        raw = float(info.get("dividendYield") or 0)
        return raw / 100 if raw else 0.0

    @staticmethod
    def _calculate_current_ratio(balance: Dict) -> float:
        assets = balance.get("currentAssets", 0)
        liabilities = balance.get("currentLiabilities", 0)
        return assets / liabilities if liabilities > 0 else 0.0

    @staticmethod
    def _calculate_debt_equity(balance: Dict) -> float:
        debt = balance.get("longTermDebt", 0) + balance.get("currentDebt", 0)
        equity = balance.get("totalShareholderEquity", 0)
        return debt / equity if equity > 0 else 999.0

    @staticmethod
    def _calculate_growth_rate(earnings_history: list) -> float:
        positives = [e for e in earnings_history if e > 0]
        if len(positives) < 2:
            return 0.0
        try:
            cagr = (positives[0] / positives[-1]) ** (1 / (len(positives) - 1)) - 1
            return max(0.0, min(cagr, 0.30))
        except Exception:
            return 0.0

    @staticmethod
    def _calculate_dividend_years(dividends) -> int:
        """Count consecutive calendar years with at least one dividend payment."""
        if dividends is None or (hasattr(dividends, "empty") and dividends.empty):
            return 0
        try:
            paid_years = set(dividends.index.year)
            current_year = datetime.now().year
            consecutive = 0
            for year in range(current_year, current_year - 60, -1):
                if year in paid_years:
                    consecutive += 1
                else:
                    break
            return consecutive
        except Exception:
            return 0

    @staticmethod
    def _avg_intrinsic_value(valuation) -> float:
        """
        Average of all valid intrinsic value estimates.

        NCAV is included only when positive (net-net stocks are rare; a
        negative NCAV just means the company isn't a liquidation candidate,
        not that it has zero value).
        """
        candidates = [
            valuation.graham_number,
            valuation.normalized_earnings_value,
            valuation.dividend_adjusted_value,
        ]
        if valuation.ncav_per_share > 0:
            candidates.append(valuation.ncav_per_share * (2 / 3))
        valid = [v for v in candidates if v > 0]
        return statistics.mean(valid) if valid else 0.0

    # ------------------------------------------------------------------
    # Peer-relative comparison
    # ------------------------------------------------------------------

    def _peer_comparison(self, symbol: str, raw: Dict, peers: list):
        """Build a PeerComparison of `symbol` against `peers`.

        The target snapshot reuses the already-fetched `raw`; each peer is
        fetched through the cached path. Peers that fail to resolve or duplicate
        the target are skipped. Returns None when no peer snapshot is usable.
        """
        target_snapshot = self._snapshot_from_raw(symbol, raw)
        if target_snapshot is None:
            return None

        seen = {symbol.upper()}
        peer_snapshots = []
        for peer in peers:
            p = peer.strip().upper()
            if not p or p in seen:
                continue
            seen.add(p)
            snap = self._compute_peer_snapshot(p)
            if snap is not None:
                peer_snapshots.append(snap)

        if not peer_snapshots:
            logger.warning(f"No usable peer data for {symbol}; skipping comparison")
            return None

        return relative.compare(target_snapshot, peer_snapshots)

    def _compute_peer_snapshot(self, symbol: str):
        """Fetch (cached) and build a MetricSnapshot for one peer; None on failure."""
        try:
            raw = self._fetch_yf_data(symbol)
        except Exception as e:
            logger.warning(f"Failed to fetch peer {symbol}: {e}")
            return None
        return self._snapshot_from_raw(symbol, raw)

    def _snapshot_from_raw(self, symbol: str, raw: Dict):
        """Assemble a comparable MetricSnapshot from a raw yfinance bundle."""
        try:
            info = raw.get("info", {}) or {}
            income_annual = self._parse_income_stmt(raw.get("income_stmt")).get("annual", [])
            cashflow_annual = self._parse_cashflow(raw.get("cashflow")).get("annual", [])
            balance = self._parse_balance_sheet(
                raw.get("quarterly_balance"), raw.get("annual_balance")
            )["quarterly"]

            metrics = {
                "roe": float(info.get("returnOnEquity") or 0),
                "pe_ratio": float(info.get("trailingPE") or 0),
                "eps": float(info.get("trailingEps") or 0),
            }
            quality = self.quality_engine.analyze(metrics, income_annual, cashflow_annual)
            growth = self.growth_engine.analyze(metrics, income_annual, cashflow_annual)

            multiples = compute_valuation_multiples(
                enterprise_value=float(info.get("enterpriseValue") or 0),
                ebitda=income_annual[0].get("ebitda", 0) if income_annual else 0,
                revenue=income_annual[0].get("totalRevenue", 0) if income_annual else 0,
                market_cap=float(info.get("marketCap") or 0),
                free_cash_flow=cashflow_annual[0].get("freeCashFlow", 0) if cashflow_annual else 0,
            )

            debt_equity = self._calculate_debt_equity(balance)
            dividend_yield = self._normalize_dividend_yield(info)
            return self._assemble_snapshot(
                symbol, quality, growth, multiples,
                metrics["pe_ratio"], dividend_yield, debt_equity,
            )
        except Exception as e:
            logger.warning(f"Failed to build metric snapshot for {symbol}: {e}")
            return None

    @staticmethod
    def _assemble_snapshot(symbol, quality, growth, multiples,
                           pe_ratio, dividend_yield, debt_equity):
        """Build a relative.MetricSnapshot; 0/sentinel values become None (N/A)."""
        def clean(x):
            # 0.0 in this pipeline means "not computed"; negatives are real values.
            return None if x is None or x == 0.0 else float(x)

        values = {
            "gross_margin": clean(quality.gross_margin),
            "operating_margin": clean(quality.operating_margin),
            "net_margin": clean(quality.net_margin),
            "roe": clean(quality.roe),
            "revenue_cagr": clean(growth.revenue_cagr),
            "eps_cagr": clean(growth.eps_cagr),
            "pe_ratio": clean(pe_ratio),
            "ev_ebitda": clean(multiples.ev_ebitda),
            "ev_sales": clean(multiples.ev_sales),
            "p_fcf": clean(multiples.p_fcf),
            "dividend_yield": clean(dividend_yield),
            # 999.0 is the "no equity" sentinel from _calculate_debt_equity.
            "debt_equity": debt_equity if 0 < debt_equity < 900 else None,
        }
        return relative.MetricSnapshot(symbol=symbol, values=values)
