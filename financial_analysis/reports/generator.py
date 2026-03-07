"""Main report generation engine"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

import jinja2
import pandas as pd

from ..core.stock_analysis import StockAnalyzer
from ..visualization.charts import ChartBuilder
from ..cache.database import CacheManager
from ..utils.logger import get_logger
from ..utils.config import config
from ..utils.formatters import format_currency, format_percent

logger = get_logger(__name__)


def _format_large(value) -> str:
    """Format large dollar values with T/B/M suffix."""
    try:
        v = float(value)
        if v >= 1_000_000_000_000:
            return f"${v / 1_000_000_000_000:.2f}T"
        elif v >= 1_000_000_000:
            return f"${v / 1_000_000_000:.2f}B"
        elif v >= 1_000_000:
            return f"${v / 1_000_000:.2f}M"
        return f"${v:,.0f}"
    except Exception:
        return str(value)


class ReportGenerator:
    """
    Main report generation engine.

    Generates professional HTML reports with interactive Plotly charts,
    valuation analysis, and financial health scorecards.
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager or CacheManager(str(config.cache_db_path))
        self.analyzer = StockAnalyzer(self.cache)
        self.chart_builder = ChartBuilder()

        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(config.templates_dir)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )
        self.jinja_env.filters["currency"] = format_currency
        self.jinja_env.filters["percent"] = format_percent
        self.jinja_env.filters["format_large"] = _format_large

    async def generate_report(
        self, symbol: str, output_path: Optional[str] = None
    ) -> str:
        """
        Generate a comprehensive fundamental analysis HTML report.

        Args:
            symbol: Stock ticker symbol
            output_path: Optional output file path

        Returns:
            Path to generated HTML report
        """
        logger.info(f"Generating report for {symbol}")

        analysis = await self.analyzer.analyze(symbol)

        valuation = analysis["valuation"]
        margins = valuation["margins_of_safety"]
        company_info = analysis["company_info"]
        metrics = analysis["metrics"]

        # --- Charts ---
        valuation_chart = self.chart_builder.create_valuation_chart(
            valuations={
                "graham_number": valuation["graham_number"],
                "ncav_per_share": valuation["ncav_per_share"],
                "normalized_value": valuation["normalized_value"],
                "dividend_adjusted_value": valuation["dividend_adjusted_value"],
            },
            current_price=analysis["current_price"],
            symbol=symbol.upper(),
        )

        margin_gauge = self.chart_builder.create_margin_of_safety_gauge(
            margin=margins["average"],
            symbol=symbol.upper(),
        )

        health_chart = self.chart_builder.create_health_scorecard_chart(
            checklist=analysis["defensive_checklist"],
            symbol=symbol.upper(),
        )

        # Price history from Yahoo Finance (already in analysis result)
        price_chart = None
        history_df = analysis.get("history")
        if isinstance(history_df, pd.DataFrame) and not history_df.empty:
            price_chart = self.chart_builder.create_price_history_chart(
                dates=[str(d.date()) for d in history_df.index],
                prices=history_df["Close"].tolist(),
                symbol=symbol.upper(),
                intrinsic_value=valuation["graham_number"],
            )

        # Financial trends
        financial_trends_chart = None
        annual_income = analysis["financial_statements"]["income"].get("annual", [])
        if annual_income:
            financial_trends_chart = self.chart_builder.create_financial_trends_chart(
                income_data=annual_income[:10],
                symbol=symbol.upper(),
            )

        # Table HTML
        health_table = self._format_health_table(analysis["defensive_checklist"])
        opportunities_table = self._format_opportunities_table(
            analysis["enterprising_checklist"]
        )

        # Health score label
        summary = analysis["defensive_checklist"].get("summary", {})
        health_score = f"{summary.get('passed', 0)}/{summary.get('total', 8)}"

        context = {
            "symbol": symbol.upper(),
            "company_name": company_info.get("name", symbol.upper()),
            "sector": company_info.get("sector", ""),
            "industry": company_info.get("industry", ""),
            "generation_time": datetime.now().strftime("%B %d, %Y"),
            "current_price": analysis["current_price"],
            "price_change_pct": analysis.get("price_change_pct", 0),
            "market_cap": metrics.get("market_cap", 0),
            "pe_ratio": metrics.get("pe_ratio", 0),
            "pb_ratio": metrics.get("pb_ratio", 0),
            "beta": metrics.get("beta", 0),
            "dividend_yield": metrics.get("dividend_yield", 0),
            # Valuation
            "graham_number": valuation["graham_number"],
            "ncav_per_share": valuation["ncav_per_share"],
            "ncav_buy_price": valuation["ncav_per_share"] * 0.67,
            "normalized_value": valuation["normalized_value"],
            "dividend_adjusted_value": valuation["dividend_adjusted_value"],
            "avg_intrinsic_value": valuation["avg_intrinsic_value"],
            "margin_of_safety": margins["average"],
            "mos_graham": margins["graham"],
            "mos_ncav": margins["ncav"],
            "mos_normalized": margins["normalized"],
            "mos_dividend": margins["dividend_adjusted"],
            "recommendation": analysis["recommendation"],
            # Metrics
            "eps": metrics.get("eps", 0),
            "book_value": metrics.get("book_value", 0),
            "current_ratio": metrics.get("current_ratio", 0),
            "debt_equity": metrics.get("debt_equity", 0),
            "health_score": health_score,
            # Charts (HTML strings)
            "valuation_chart": valuation_chart.to_html(
                include_plotlyjs="cdn", div_id="valuation_chart", full_html=False
            ),
            "margin_gauge": margin_gauge.to_html(
                include_plotlyjs=False, div_id="margin_gauge", full_html=False
            ),
            "health_chart": health_chart.to_html(
                include_plotlyjs=False, div_id="health_chart", full_html=False
            ),
            "price_chart": price_chart.to_html(
                include_plotlyjs=False, div_id="price_chart", full_html=False
            )
            if price_chart
            else None,
            "financial_trends_chart": financial_trends_chart.to_html(
                include_plotlyjs=False, div_id="trends_chart", full_html=False
            )
            if financial_trends_chart
            else None,
            # Tables
            "health_table": health_table,
            "opportunities_table": opportunities_table,
        }

        template = self.jinja_env.get_template("analysis.html")
        html = template.render(**context)

        if output_path is None:
            filename = (
                f"analysis_{symbol.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            )
            output_path = config.output_dir / filename

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Report saved: {output_path}")
        return str(output_path)

    # Legacy alias
    async def generate_graham_report(self, symbol: str, output_path: Optional[str] = None) -> str:
        return await self.generate_report(symbol, output_path)

    # ------------------------------------------------------------------
    # Table formatters
    # ------------------------------------------------------------------

    def _format_health_table(self, checklist: dict) -> str:
        rows = ""
        for key, result in checklist.items():
            if key == "summary":
                continue
            passed = result.get("pass", False)
            value = result.get("value", "")
            target = result.get("target", "")
            desc = result.get("description", "")

            if isinstance(value, float):
                if value >= 1_000_000_000:
                    value_str = _format_large(value)
                else:
                    value_str = f"{value:.2f}"
            else:
                value_str = str(value)

            badge = (
                '<span class="badge badge-pass">Pass</span>'
                if passed
                else '<span class="badge badge-fail">Fail</span>'
            )
            rows += (
                f"<tr>"
                f"<td><strong>{desc}</strong></td>"
                f'<td style="font-family:monospace;font-size:12px;">{target}</td>'
                f"<td>{value_str}</td>"
                f"<td>{badge}</td>"
                f"</tr>"
            )

        summary = checklist.get("summary", {})
        passed_count = summary.get("passed", 0)
        total = summary.get("total", 8)
        rate = format_percent(summary.get("pass_rate", 0))

        return (
            '<table class="data-table">'
            "<thead><tr><th>Criterion</th><th>Target</th><th>Actual</th><th>Result</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            f'<tfoot><tr><td colspan="3"><strong>Financial Health Score</strong></td>'
            f"<td><strong>{passed_count}/{total}</strong> criteria met ({rate})</td></tr></tfoot>"
            "</table>"
        )

    def _format_opportunities_table(self, checklist: dict) -> str:
        rows = ""
        for key, result in checklist.items():
            if key == "summary":
                continue
            opportunity = result.get("opportunity", False)
            desc = result.get("description", "")
            details = []
            for k, v in result.items():
                if k in ("opportunity", "description"):
                    continue
                if isinstance(v, float):
                    if abs(v) > 100_000:
                        details.append(f"{k}: {format_currency(v)}")
                    elif k in ("discount", "price_position", "growth"):
                        details.append(f"{k}: {format_percent(v)}")
                    else:
                        details.append(f"{k}: {v:.2f}")
                else:
                    details.append(f"{k}: {v}")

            badge = (
                '<span class="badge badge-pass">Yes</span>'
                if opportunity
                else '<span class="badge badge-neutral">No</span>'
            )
            detail_str = " &middot; ".join(details)
            rows += (
                f"<tr>"
                f"<td><strong>{desc}</strong></td>"
                f"<td>{badge}</td>"
                f'<td style="font-size:12px;color:#64748b;">{detail_str}</td>'
                f"</tr>"
            )

        summary = checklist.get("summary", {})
        opp_count = summary.get("opportunities", 0)
        summary_desc = summary.get("description", "")

        return (
            '<table class="data-table">'
            "<thead><tr><th>Opportunity Type</th><th>Signal</th><th>Details</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            f'<tfoot><tr><td colspan="2"><strong>Total Signals</strong></td>'
            f"<td>{opp_count} &mdash; {summary_desc}</td></tr></tfoot>"
            "</table>"
        )
