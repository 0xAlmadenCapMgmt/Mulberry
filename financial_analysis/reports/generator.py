"""Main report generator engine"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
import jinja2

from ..core.stock_analysis import StockAnalyzer
from ..visualization.charts import ChartBuilder
from ..cache.database import CacheManager
from ..utils.logger import get_logger
from ..utils.config import config
from ..utils.formatters import format_currency, format_percent

logger = get_logger(__name__)


class ReportGenerator:
    """
    Main report generation engine

    Generates professional HTML reports with:
    - Graham valuation analysis
    - Interactive Plotly charts
    - Defensive/enterprising checklists
    - Financial metrics and trends
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        Initialize report generator

        Args:
            cache_manager: Optional cache manager
        """
        self.cache = cache_manager or CacheManager(str(config.cache_db_path))
        self.analyzer = StockAnalyzer(self.cache)
        self.chart_builder = ChartBuilder()

        # Setup Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(config.templates_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

        # Add custom filters
        self.jinja_env.filters['currency'] = format_currency
        self.jinja_env.filters['percent'] = format_percent

    async def generate_graham_report(
        self,
        symbol: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive Graham valuation report

        Args:
            symbol: Stock ticker symbol
            output_path: Optional output file path

        Returns:
            Path to generated HTML report
        """
        logger.info(f"Generating Graham report for {symbol}")

        try:
            # Perform analysis
            analysis = await self.analyzer.analyze(symbol)

            # Extract data
            valuation = analysis['valuation']
            quote = analysis['quote']
            overview = analysis['overview']
            margins = valuation['margins_of_safety']

            # Generate charts
            logger.info("Generating charts...")

            valuation_chart = self.chart_builder.create_graham_valuation_chart(
                valuations={
                    'graham_number': valuation['graham_number'],
                    'ncav_per_share': valuation['ncav_per_share'],
                    'normalized_value': valuation['normalized_value'],
                    'dividend_adjusted_value': valuation['dividend_adjusted_value']
                },
                current_price=analysis['current_price'],
                symbol=symbol.upper()
            )

            margin_gauge = self.chart_builder.create_margin_of_safety_gauge(
                margin=margins['average'],
                symbol=symbol.upper()
            )

            defensive_chart = self.chart_builder.create_defensive_checklist_chart(
                checklist=analysis['defensive_checklist'],
                symbol=symbol.upper()
            )

            # Price history chart (if time series data available)
            price_chart = None
            try:
                time_series = await self.analyzer.alpha_vantage.get_time_series(symbol, outputsize='compact')
                price_chart = self.chart_builder.create_price_history_chart(
                    dates=time_series['dates'][:90],  # Last 90 days
                    prices=time_series['prices'][:90],
                    symbol=symbol.upper(),
                    graham_number=valuation['graham_number']
                )
            except Exception as e:
                logger.warning(f"Could not generate price chart: {e}")

            # Financial trends chart
            financial_trends_chart = None
            if analysis['financial_statements']['income'].get('annual'):
                financial_trends_chart = self.chart_builder.create_financial_trends_chart(
                    income_data=analysis['financial_statements']['income']['annual'][:10],
                    symbol=symbol.upper()
                )

            # Generate defensive checklist table
            defensive_table = self._format_defensive_table(analysis['defensive_checklist'])

            # Generate enterprising table
            enterprising_table = self._format_enterprising_table(analysis['enterprising_checklist'])

            # Prepare template context
            context = {
                'symbol': symbol.upper(),
                'company_name': overview.get('Name', symbol.upper()),
                'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'current_price': analysis['current_price'],
                'graham_number': valuation['graham_number'],
                'ncav_per_share': valuation['ncav_per_share'],
                'normalized_value': valuation['normalized_value'],
                'dividend_adjusted_value': valuation['dividend_adjusted_value'],
                'avg_intrinsic_value': valuation['avg_intrinsic_value'],
                'margin_of_safety': margins['average'],
                'mos_graham': margins['graham'],
                'mos_ncav': margins['ncav'],
                'mos_normalized': margins['normalized'],
                'mos_dividend': margins['dividend_adjusted'],
                'recommendation': analysis['recommendation'],
                'eps': float(overview.get('EPS', 0)),
                'book_value': float(overview.get('BookValue', 0)),
                'pe_ratio': float(overview.get('PERatio', 0)),
                'pb_ratio': float(overview.get('PriceToBookRatio', 0)),
                'current_ratio': analysis['metrics']['current_ratio'],
                'debt_equity': analysis['metrics']['debt_equity'],
                'valuation_chart': valuation_chart.to_html(include_plotlyjs='cdn', div_id='valuation_chart'),
                'margin_gauge': margin_gauge.to_html(include_plotlyjs=False, div_id='margin_gauge'),
                'defensive_chart': defensive_chart.to_html(include_plotlyjs=False, div_id='defensive_chart'),
                'defensive_table': defensive_table,
                'enterprising_table': enterprising_table,
                'price_chart': price_chart.to_html(include_plotlyjs=False, div_id='price_chart') if price_chart else None,
                'financial_trends_chart': financial_trends_chart.to_html(include_plotlyjs=False, div_id='trends_chart') if financial_trends_chart else None
            }

            # Render template
            template = self.jinja_env.get_template('graham_analysis.html')
            html = template.render(**context)

            # Save to file
            if output_path is None:
                filename = f"graham_{symbol.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                output_path = config.output_dir / filename

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(f"Report generated successfully: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise Exception(f"Failed to generate report: {e}")

        finally:
            await self.analyzer.alpha_vantage.close()

    def _format_defensive_table(self, checklist: dict) -> str:
        """Format defensive investor checklist as HTML table"""
        html = '<table>'
        html += '<thead><tr><th>Criterion</th><th>Target</th><th>Actual</th><th>Result</th></tr></thead>'
        html += '<tbody>'

        for key, result in checklist.items():
            if key == 'summary':
                continue

            passed = result.get('pass', False)
            value = result.get('value', '')
            target = result.get('target', '')
            desc = result.get('description', '')

            # Format value
            if isinstance(value, float):
                if value > 1000000:
                    value_str = format_currency(value)
                else:
                    value_str = f"{value:.2f}"
            else:
                value_str = str(value)

            status = '<span class="pass">✓ PASS</span>' if passed else '<span class="fail">✗ FAIL</span>'

            html += f'<tr>'
            html += f'<td><strong>{desc}</strong></td>'
            html += f'<td>{target}</td>'
            html += f'<td>{value_str}</td>'
            html += f'<td>{status}</td>'
            html += f'</tr>'

        # Summary row
        summary = checklist.get('summary', {})
        html += f'<tr style="background: #f8f9fa; font-weight: bold;">'
        html += f'<td colspan="3">Overall Score</td>'
        html += f'<td>{summary.get("passed", 0)}/{summary.get("total", 8)} Criteria Met '
        html += f'({format_percent(summary.get("pass_rate", 0))})</td>'
        html += f'</tr>'

        html += '</tbody></table>'
        return html

    def _format_enterprising_table(self, checklist: dict) -> str:
        """Format enterprising investor assessment as HTML table"""
        html = '<table>'
        html += '<thead><tr><th>Opportunity Type</th><th>Present</th><th>Details</th></tr></thead>'
        html += '<tbody>'

        for key, result in checklist.items():
            if key == 'summary':
                continue

            opportunity = result.get('opportunity', False)
            desc = result.get('description', '')

            # Build details string
            details = []
            for k, v in result.items():
                if k not in ['opportunity', 'description']:
                    if isinstance(v, float):
                        if abs(v) > 100:
                            details.append(f"{k}: {format_currency(v)}")
                        elif k in ['discount', 'price_position', 'growth']:
                            details.append(f"{k}: {format_percent(v)}")
                        else:
                            details.append(f"{k}: {v:.2f}")
                    else:
                        details.append(f"{k}: {v}")

            status = '<span class="pass">✓ YES</span>' if opportunity else '<span>✗ NO</span>'
            details_str = '<br>'.join(details)

            html += f'<tr>'
            html += f'<td><strong>{desc}</strong></td>'
            html += f'<td>{status}</td>'
            html += f'<td><small>{details_str}</small></td>'
            html += f'</tr>'

        # Summary row
        summary = checklist.get('summary', {})
        opportunities = summary.get('opportunities', 0)
        html += f'<tr style="background: #f8f9fa; font-weight: bold;">'
        html += f'<td colspan="2">Total Opportunities</td>'
        html += f'<td>{opportunities} - {summary.get("description", "")}</td>'
        html += f'</tr>'

        html += '</tbody></table>'
        return html
