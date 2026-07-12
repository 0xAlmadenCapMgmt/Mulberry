"""Main report generation engine"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

import jinja2
import pandas as pd

from ..core.stock_analysis import StockAnalyzer
from ..visualization.charts import ChartBuilder
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

    def __init__(
        self,
        analyzer: Optional[StockAnalyzer] = None,
        profile: str = "balanced",
    ):
        self.analyzer = analyzer or StockAnalyzer(profile=profile)
        self.chart_builder = ChartBuilder()

        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(config.templates_dir)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )
        self.jinja_env.filters["currency"] = format_currency
        self.jinja_env.filters["percent"] = format_percent
        self.jinja_env.filters["format_large"] = _format_large

    async def generate_report(
        self,
        symbol: str,
        output_path: Optional[str] = None,
        peers: Optional[list] = None,
        include_filings: bool = False,
    ) -> str:
        """
        Generate a comprehensive fundamental analysis HTML report.

        Args:
            symbol: Stock ticker symbol
            output_path: Optional output file path
            peers: Optional list of peer tickers for relative comparison
            include_filings: Attach an SEC EDGAR filings section when available

        Returns:
            Path to generated HTML report
        """
        logger.info(f"Generating report for {symbol}")

        analysis = await self.analyzer.analyze(
            symbol, peers=peers, include_filings=include_filings
        )

        valuation = analysis["valuation"]
        margins = valuation["margins_of_safety"]
        company_info = analysis["company_info"]
        metrics = analysis["metrics"]
        frameworks = analysis["frameworks"]
        quality = frameworks["quality"]
        growth = frameworks["growth"]
        dividend = frameworks["dividend"]
        momentum = frameworks["momentum"]
        dcf = frameworks["dcf"]
        composite = frameworks["composite"]

        # --- Charts ---
        valuation_chart = self.chart_builder.create_valuation_chart(
            valuations={
                "graham_number": valuation["graham_number"],
                "ncav_per_share": valuation["ncav_per_share"],
                "normalized_value": valuation["normalized_value"],
                "dividend_adjusted_value": valuation["dividend_adjusted_value"],
                "dcf_value": dcf.intrinsic_value_per_share,
                "ddm_value": dividend.ddm_value,
            },
            current_price=analysis["current_price"],
            symbol=symbol.upper(),
        )

        radar_chart = self.chart_builder.create_framework_radar_chart(
            lens_scores=composite.lens_scores,
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
            closes = history_df["Close"]
            sma_50 = closes.rolling(50).mean() if len(closes) >= 50 else None
            sma_200 = closes.rolling(200).mean() if len(closes) >= 200 else None
            price_chart = self.chart_builder.create_price_history_chart(
                dates=[str(d.date()) for d in history_df.index],
                prices=closes.tolist(),
                symbol=symbol.upper(),
                intrinsic_value=valuation["avg_intrinsic_value"],
                sma_50=sma_50.tolist() if sma_50 is not None else None,
                sma_200=sma_200.tolist() if sma_200 is not None else None,
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
        framework_table = self._format_framework_table(composite)
        multiples_table = self._format_multiples_table(analysis.get("multiples"))
        forward = analysis.get("forward")
        forward_table = self._format_forward_table(forward, analysis["current_price"])
        peer_comparison = analysis.get("peer_comparison")
        peer_table = self._format_peer_table(peer_comparison)

        # SEC filings (optional context section)
        filings = analysis.get("filings")
        filings_chart = None
        if filings is not None and filings.trends:
            filings_chart = self.chart_builder.create_filings_trend_chart(
                filings.trends, symbol.upper()
            )
        filings_timeline_table = self._format_filings_timeline(filings)
        filings_trends_table = self._format_filings_trends(filings)
        filings_flags_html = self._format_red_flags(filings)

        confidence = analysis.get("data_confidence")
        confidence_table = self._format_confidence_table(confidence)
        quality_table = self._format_checks_table(quality.checks)
        growth_table = self._format_checks_table(growth.checks)
        dividend_table = self._format_checks_table(dividend.checks)
        momentum_table = self._format_checks_table(momentum.checks)
        dcf_sensitivity_table = self._format_dcf_sensitivity(dcf)

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
            "graham_recommendation": analysis.get("graham_recommendation", ""),
            # Multi-framework results
            "profile": composite.profile,
            "profile_label": self._PROFILE_LABELS.get(composite.profile, composite.profile),
            "composite_score": composite.overall_score,
            "lens_scores": composite.lens_scores,
            "lens_ratings": composite.lens_ratings,
            "lens_verdicts": composite.lens_verdicts,
            "dcf_value": dcf.intrinsic_value_per_share,
            "dcf_margin": dcf.margin_of_safety,
            "dcf_stage1_growth": dcf.stage1_growth,
            "dcf_discount_rate": dcf.discount_rate,
            "dcf_terminal_growth": dcf.terminal_growth,
            "ddm_value": dividend.ddm_value,
            "quality_score": quality.score,
            "quality_rating": quality.rating,
            "growth_score": growth.score,
            "growth_rating": growth.rating,
            "dividend_score": dividend.score,
            "dividend_rating": dividend.rating,
            "momentum_score": momentum.score,
            "momentum_signal": momentum.signal,
            "momentum_volatility": momentum.volatility_annual,
            "momentum_max_drawdown": momentum.max_drawdown,
            "momentum_sharpe": momentum.sharpe_ratio,
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
            "radar_chart": radar_chart.to_html(
                include_plotlyjs=False, div_id="radar_chart", full_html=False
            ),
            # Tables
            "health_table": health_table,
            "opportunities_table": opportunities_table,
            "framework_table": framework_table,
            "multiples_table": multiples_table,
            "forward_table": forward_table,
            "forward_has_data": bool(forward and forward.has_data),
            "peer_table": peer_table,
            "peer_symbols": ", ".join(peer_comparison.peer_symbols) if peer_comparison else "",
            "peer_overall_percentile": peer_comparison.overall_percentile if peer_comparison else 0,
            # SEC filings
            "filings_available": filings is not None,
            "filings_entity": filings.entity_name if filings else "",
            "filings_freshness": filings.days_since_last_periodic if filings else None,
            "filings_8k_count": filings.recent_8k_count if filings else 0,
            "filings_flag_count": len(filings.red_flags) if filings else 0,
            "filings_timeline_table": filings_timeline_table,
            "filings_trends_table": filings_trends_table,
            "filings_flags_html": filings_flags_html,
            "filings_sections": filings.sections if filings else [],
            "filings_chart": filings_chart.to_html(
                include_plotlyjs=False, div_id="filings_chart", full_html=False
            ) if filings_chart else None,
            "data_confidence_level": confidence.level if confidence else "",
            "data_confidence_score": confidence.score if confidence else 0,
            "data_confidence_notes": confidence.notes if confidence else [],
            "data_confidence_table": confidence_table,
            "quality_table": quality_table,
            "growth_table": growth_table,
            "dividend_table": dividend_table,
            "momentum_table": momentum_table,
            "dcf_sensitivity_table": dcf_sensitivity_table,
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

    _PROFILE_LABELS = {
        "balanced": "Balanced",
        "deep_value": "Deep Value",
        "garp": "Growth at a Reasonable Price",
        "income": "Income",
        "quality_growth": "Quality Growth",
    }

    @staticmethod
    def _format_filings_timeline(filings) -> str:
        """Recent 10-K / 10-Q / 8-K filing timeline."""
        if filings is None or not filings.timeline:
            return ""
        rows = ""
        for ref in filings.timeline:
            items = f' <span style="color:#64748b;">({ref.items})</span>' if ref.items else ""
            rows += (
                f"<tr><td><strong>{ref.form}</strong>{items}</td>"
                f"<td>{ref.filing_date}</td>"
                f"<td>{ref.report_date}</td></tr>"
            )
        return (
            '<table class="data-table">'
            "<thead><tr><th>Form</th><th>Filed</th><th>Period</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    @staticmethod
    def _format_filings_trends(filings) -> str:
        """Multi-year structured trends with a favorable/unfavorable read."""
        if filings is None or not filings.trends:
            return ""
        rows = ""
        for t in filings.trends:
            if t.unit == "shares":
                latest = f"{t.latest / 1_000_000:,.0f}M sh"
            else:
                latest = _format_large(t.latest)
            # Favorable if the direction matches what's good for this metric.
            if t.direction == "Flat":
                badge_class = "badge-neutral"
            else:
                good = (t.direction == "Rising") == t.higher_is_better
                badge_class = "badge-pass" if good else "badge-fail"
            rows += (
                f"<tr><td><strong>{t.label}</strong></td>"
                f"<td>{latest}</td>"
                f"<td>{t.change_pct * 100:+.0f}%</td>"
                f'<td><span class="badge {badge_class}">{t.direction}</span></td></tr>'
            )
        return (
            '<table class="data-table">'
            "<thead><tr><th>Metric</th><th>Latest</th><th>Δ over period</th>"
            "<th>Trend</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    @staticmethod
    def _format_red_flags(filings) -> str:
        """Red-flag callout list; explicit 'none' note when clean."""
        if filings is None:
            return ""
        if not filings.red_flags:
            return (
                '<p style="font-size:13px;color:#16a34a;">'
                "✓ No going-concern, material-weakness, restatement, or notable "
                "8-K red flags detected in recent filings.</p>"
            )
        severity_badge = {"high": "badge-fail", "medium": "badge-hold", "info": "badge-neutral"}
        rows = ""
        for flag in filings.red_flags:
            badge = severity_badge.get(flag.severity, "badge-neutral")
            rows += (
                f"<tr>"
                f'<td><span class="badge {badge}">{flag.severity.title()}</span></td>'
                f"<td><strong>{flag.label}</strong></td>"
                f'<td style="font-size:12px;color:#64748b;">{flag.detail}</td>'
                f"</tr>"
            )
        return (
            '<table class="data-table">'
            "<thead><tr><th>Severity</th><th>Flag</th><th>Detail</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    @staticmethod
    def _format_multiples_table(multiples) -> str:
        """Relative-valuation multiples table (EV/EBITDA, EV/Sales, P/FCF)."""
        if multiples is None:
            return ""
        rows_spec = [
            ("EV / EBITDA", multiples.ev_ebitda, "Enterprise value to operating cash earnings"),
            ("EV / Sales", multiples.ev_sales, "Enterprise value to revenue"),
            ("Price / FCF", multiples.p_fcf, "Market cap to free cash flow"),
        ]
        rows = ""
        for label, value, desc in rows_spec:
            shown = f"{value:.1f}x" if value and value > 0 else "&mdash;"
            rows += (
                f"<tr><td><strong>{label}</strong></td>"
                f"<td>{shown}</td>"
                f'<td style="font-size:12px;color:#64748b;">{desc}</td></tr>'
            )
        return (
            '<table class="data-table">'
            "<thead><tr><th>Multiple</th><th>Value</th><th>Basis</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    @staticmethod
    def _format_forward_table(forward, current_price: float) -> str:
        """Analyst/estimate context panel."""
        if forward is None or not forward.has_data:
            return ""
        rows = ""

        def add(label, value):
            nonlocal rows
            rows += (
                f"<tr><td><strong>{label}</strong></td><td>{value}</td></tr>"
            )

        if forward.recommendation_key:
            mean = (
                f" (mean {forward.recommendation_mean:.1f}/5)"
                if forward.recommendation_mean else ""
            )
            analysts = f" · {forward.num_analysts} analysts" if forward.num_analysts else ""
            add("Analyst consensus", f"{forward.recommendation_key.title()}{mean}{analysts}")
        if forward.forward_pe:
            add("Forward P/E", f"{forward.forward_pe:.1f}x")
        if forward.peg_ratio:
            add("Forward PEG", f"{forward.peg_ratio:.2f}")
        if forward.target_mean:
            target = format_currency(forward.target_mean)
            if forward.upside_to_target is not None:
                sign = "+" if forward.upside_to_target >= 0 else ""
                target += f" ({sign}{forward.upside_to_target * 100:.1f}% vs price)"
            add("Mean price target", target)
        if forward.target_low and forward.target_high:
            add(
                "Target range",
                f"{format_currency(forward.target_low)} – {format_currency(forward.target_high)}",
            )

        return (
            '<table class="data-table">'
            "<thead><tr><th>Forward Indicator</th><th>Value</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    @staticmethod
    def _format_peer_table(comparison) -> str:
        """Peer-relative percentile table (target vs peer median per metric)."""
        if comparison is None or not comparison.results:
            return ""

        def fmt(value, kind):
            if kind == "percent":
                return format_percent(value)
            return f"{value:.1f}x"

        rows = ""
        for r in comparison.results:
            pct = r.percentile
            if pct >= 0.66:
                badge_class = "badge-pass"
            elif pct >= 0.33:
                badge_class = "badge-hold"
            else:
                badge_class = "badge-fail"
            direction = "higher better" if r.higher_is_better else "lower better"
            rows += (
                f"<tr>"
                f"<td><strong>{r.label}</strong>"
                f'<div style="font-size:11px;color:var(--slate-400);">{direction}</div></td>'
                f"<td>{fmt(r.target, r.fmt)}</td>"
                f"<td>{fmt(r.peer_median, r.fmt)}</td>"
                f'<td><span class="badge {badge_class}">{pct * 100:.0f}th pct</span></td>'
                f"</tr>"
            )

        return (
            '<table class="data-table">'
            "<thead><tr><th>Metric</th><th>Target</th><th>Peer Median</th>"
            "<th>Percentile</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            f'<tfoot><tr><td colspan="3"><strong>Overall vs Peers</strong></td>'
            f"<td><strong>{comparison.overall_percentile * 100:.0f}th pct</strong></td>"
            "</tr></tfoot></table>"
        )

    def _format_framework_table(self, composite) -> str:
        """Composite scorecard: one row per analysis lens."""
        lens_names = {
            "value": "Value (Graham + DCF)",
            "quality": "Business Quality",
            "growth": "Growth / GARP",
            "momentum": "Momentum",
            "dividend": "Dividend",
        }
        rows = ""
        for key, label in lens_names.items():
            score = composite.lens_scores.get(key, 0)
            rating = composite.lens_ratings.get(key, "")
            verdict = composite.lens_verdicts.get(key, "")
            weight = composite.weights.get(key, 0)

            if score >= 65:
                badge_class = "badge-pass"
            elif score >= 40:
                badge_class = "badge-hold"
            else:
                badge_class = "badge-fail"

            rows += (
                f"<tr>"
                f"<td><strong>{label}</strong></td>"
                f'<td><span class="badge {badge_class}">{score:.0f}/100</span></td>'
                f"<td>{rating}</td>"
                f"<td>{weight:.0%}</td>"
                f'<td style="font-size:12px;color:#64748b;">{verdict}</td>'
                f"</tr>"
            )

        return (
            '<table class="data-table">'
            "<thead><tr><th>Framework</th><th>Score</th><th>Rating</th>"
            "<th>Weight</th><th>Assessment</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            f'<tfoot><tr><td colspan="4"><strong>Composite Score</strong></td>'
            f"<td><strong>{composite.overall_score:.0f}/100</strong></td></tr></tfoot>"
            "</table>"
        )

    @staticmethod
    def _format_check_value(key: str, value) -> str:
        """Human-readable rendering for a check value."""
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, (int, float)):
            v = float(value)
            # Ratios/rates below 1 (or small negatives) read best as percents,
            # except explicit multiples like conversion or PEG
            percent_keys = (
                "margin", "roe", "yield", "growth", "cagr", "consistency",
                "return", "sma",
            )
            if any(p in key for p in percent_keys) and abs(v) < 5:
                return format_percent(v)
            if abs(v) >= 1_000_000:
                return _format_large(v)
            if float(v).is_integer():
                return f"{int(v)}"
            return f"{v:.2f}"
        return str(value)

    def _format_checks_table(self, checks: dict) -> str:
        """Generic criterion/target/actual/result table from a checks dict."""
        rows = ""
        for key, result in checks.items():
            passed = result.get("pass", False)
            value_str = self._format_check_value(key, result.get("value", ""))
            target = result.get("target", "")
            desc = result.get("description", "")

            badge = (
                '<span class="badge badge-pass">Pass</span>'
                if passed
                else '<span class="badge badge-fail">Miss</span>'
            )
            rows += (
                f"<tr>"
                f"<td><strong>{desc}</strong></td>"
                f'<td style="font-family:monospace;font-size:12px;">{target}</td>'
                f"<td>{value_str}</td>"
                f"<td>{badge}</td>"
                f"</tr>"
            )

        return (
            '<table class="data-table">'
            "<thead><tr><th>Criterion</th><th>Target</th><th>Actual</th><th>Result</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table>"
        )

    @staticmethod
    def _format_confidence_table(confidence) -> str:
        """Per-lens data-availability table."""
        if confidence is None:
            return ""

        lens_names = {
            "value": "Value (Graham + DCF)",
            "quality": "Business Quality",
            "growth": "Growth / GARP",
            "dcf": "DCF",
            "dividend": "Dividend",
            "momentum": "Momentum",
        }
        rows = ""
        for key, label in lens_names.items():
            lens = confidence.lenses.get(key)
            if lens is None:
                continue
            if lens.score >= 0.8:
                badge_class = "badge-pass"
            elif lens.score >= 0.5:
                badge_class = "badge-hold"
            else:
                badge_class = "badge-fail"
            missing = ", ".join(lens.missing) if lens.missing else "&mdash;"
            rows += (
                f"<tr>"
                f"<td><strong>{label}</strong></td>"
                f'<td><span class="badge {badge_class}">{lens.present}/{lens.total}</span></td>'
                f'<td style="font-size:12px;color:#64748b;">{missing}</td>'
                f"</tr>"
            )

        return (
            '<table class="data-table">'
            "<thead><tr><th>Framework</th><th>Inputs Available</th>"
            "<th>Missing</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            f'<tfoot><tr><td><strong>Overall Confidence</strong></td>'
            f'<td colspan="2"><strong>{confidence.level}</strong> '
            f"({confidence.score:.0%} of inputs available)</td></tr></tfoot>"
            "</table>"
        )

    @staticmethod
    def _format_dcf_sensitivity(dcf) -> str:
        """Discount-rate vs terminal-growth sensitivity grid."""
        if not dcf.sensitivity:
            return ""

        terminal_rates = [
            f"{cell['terminal_growth']:.1%} terminal"
            for cell in dcf.sensitivity[0]["values"]
        ]
        header = "".join(f"<th>{t}</th>" for t in terminal_rates)

        rows = ""
        for row in dcf.sensitivity:
            cells = "".join(
                f"<td>{format_currency(cell['value'])}</td>" for cell in row["values"]
            )
            rows += (
                f"<tr><td><strong>{row['discount_rate']:.0%} discount</strong></td>"
                f"{cells}</tr>"
            )

        return (
            '<table class="data-table">'
            f"<thead><tr><th>Per-Share Value</th>{header}</tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table>"
        )
