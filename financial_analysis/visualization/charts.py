"""Plotly chart builders for financial visualizations"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional
import pandas as pd

from ..utils.formatters import format_currency, format_percent


class ChartBuilder:
    """
    Builder class for creating interactive Plotly charts

    All charts return Plotly Figure objects that can be:
    - Displayed in notebooks
    - Converted to HTML with fig.to_html()
    - Exported to static images
    """

    @staticmethod
    def create_graham_valuation_chart(
        valuations: Dict[str, float],
        current_price: float,
        symbol: str
    ) -> go.Figure:
        """
        Create bar chart comparing four Graham valuations vs current price

        Args:
            valuations: Dict with graham_number, ncav, normalized, dividend_adjusted
            current_price: Current market price
            symbol: Stock symbol

        Returns:
            Plotly Figure
        """
        methods = [
            'Graham Number',
            'Net-Net NCAV',
            'Normalized Earnings',
            'Dividend-Adjusted',
            'Current Price'
        ]

        values = [
            valuations.get('graham_number', 0),
            valuations.get('ncav_per_share', 0) * 0.67,  # Buy at 2/3 NCAV
            valuations.get('normalized_value', 0),
            valuations.get('dividend_adjusted_value', 0),
            current_price
        ]

        # Color code: green for valuations, red for current price
        colors = ['#28a745', '#28a745', '#28a745', '#28a745', '#dc3545']

        fig = go.Figure(data=[
            go.Bar(
                x=methods,
                y=values,
                marker_color=colors,
                text=[format_currency(v) for v in values],
                textposition='outside',
                hovertemplate='%{x}<br>%{text}<extra></extra>'
            )
        ])

        fig.update_layout(
            title=f'{symbol} - Graham Valuation Methods',
            xaxis_title='Valuation Method',
            yaxis_title='Price ($)',
            showlegend=False,
            height=500,
            template='plotly_white',
            font=dict(size=12)
        )

        # Add horizontal line for current price
        fig.add_hline(
            y=current_price,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Current: {format_currency(current_price)}",
            annotation_position="right"
        )

        return fig

    @staticmethod
    def create_margin_of_safety_gauge(margin: float, symbol: str) -> go.Figure:
        """
        Create gauge chart showing margin of safety

        Args:
            margin: Margin of safety as decimal (-1 to 1)
            symbol: Stock symbol

        Returns:
            Plotly Figure
        """
        margin_percent = margin * 100

        # Color based on margin level
        if margin >= 0.50:
            color = '#28a745'  # Green - strong buy
        elif margin >= 0.30:
            color = '#17a2b8'  # Blue - buy
        elif margin >= 0.15:
            color = '#ffc107'  # Yellow - hold
        elif margin >= 0:
            color = '#fd7e14'  # Orange - avoid
        else:
            color = '#dc3545'  # Red - sell

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=margin_percent,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"{symbol} - Margin of Safety"},
            delta={'reference': 30, 'suffix': '%'},
            gauge={
                'axis': {'range': [-50, 100], 'ticksuffix': '%'},
                'bar': {'color': color},
                'steps': [
                    {'range': [-50, 0], 'color': '#ffcccc'},
                    {'range': [0, 15], 'color': '#ffe5cc'},
                    {'range': [15, 30], 'color': '#fff9cc'},
                    {'range': [30, 50], 'color': '#ccffcc'},
                    {'range': [50, 100], 'color': '#99ff99'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 30
                }
            }
        ))

        fig.update_layout(
            height=400,
            template='plotly_white'
        )

        return fig

    @staticmethod
    def create_price_history_chart(
        dates: List[str],
        prices: List[float],
        symbol: str,
        graham_number: Optional[float] = None
    ) -> go.Figure:
        """
        Create price history chart with optional Graham Number overlay

        Args:
            dates: List of date strings
            prices: List of prices
            symbol: Stock symbol
            graham_number: Optional Graham Number to overlay

        Returns:
            Plotly Figure
        """
        fig = go.Figure()

        # Price line
        fig.add_trace(go.Scatter(
            x=dates,
            y=prices,
            mode='lines',
            name='Price',
            line=dict(color='#1f77b4', width=2),
            hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>'
        ))

        # Graham Number line
        if graham_number:
            fig.add_hline(
                y=graham_number,
                line_dash="dash",
                line_color="green",
                annotation_text=f"Graham Number: {format_currency(graham_number)}",
                annotation_position="right"
            )

        fig.update_layout(
            title=f'{symbol} - Price History',
            xaxis_title='Date',
            yaxis_title='Price ($)',
            height=500,
            template='plotly_white',
            hovermode='x unified'
        )

        return fig

    @staticmethod
    def create_financial_trends_chart(
        income_data: List[Dict[str, Any]],
        symbol: str
    ) -> go.Figure:
        """
        Create multi-line chart for revenue, earnings, and cash flow trends

        Args:
            income_data: List of income statement dictionaries
            symbol: Stock symbol

        Returns:
            Plotly Figure
        """
        if not income_data:
            return go.Figure()

        # Extract data
        dates = [d['fiscalDateEnding'] for d in income_data]
        revenues = [d.get('totalRevenue', 0) / 1_000_000 for d in income_data]
        net_incomes = [d.get('netIncome', 0) / 1_000_000 for d in income_data]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates,
            y=revenues,
            mode='lines+markers',
            name='Revenue',
            line=dict(color='#1f77b4', width=2),
            hovertemplate='%{x}<br>Revenue: $%{y:.1f}M<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=dates,
            y=net_incomes,
            mode='lines+markers',
            name='Net Income',
            line=dict(color='#2ca02c', width=2),
            hovertemplate='%{x}<br>Net Income: $%{y:.1f}M<extra></extra>'
        ))

        fig.update_layout(
            title=f'{symbol} - Financial Trends (in millions)',
            xaxis_title='Date',
            yaxis_title='Amount ($M)',
            height=500,
            template='plotly_white',
            hovermode='x unified',
            legend=dict(x=0, y=1)
        )

        return fig

    @staticmethod
    def create_defensive_checklist_chart(checklist: Dict[str, Any], symbol: str) -> go.Figure:
        """
        Create visual checklist for defensive investor criteria

        Args:
            checklist: Defensive investor checklist results
            symbol: Stock symbol

        Returns:
            Plotly Figure
        """
        # Remove summary from display
        criteria = {k: v for k, v in checklist.items() if k != 'summary'}

        names = []
        passes = []
        colors = []
        values = []

        for criterion, result in criteria.items():
            names.append(criterion.replace('_', ' ').title())
            passed = result.get('pass', False)
            passes.append(1 if passed else 0)
            colors.append('#28a745' if passed else '#dc3545')

            # Format value display
            value = result.get('value', '')
            if isinstance(value, float):
                if value > 100:
                    value = format_currency(value)
                else:
                    value = f"{value:.2f}"
            values.append(str(value))

        fig = go.Figure(data=[
            go.Bar(
                y=names,
                x=passes,
                orientation='h',
                marker_color=colors,
                text=['✓ PASS' if p == 1 else '✗ FAIL' for p in passes],
                textposition='inside',
                hovertemplate='%{y}<br>%{text}<extra></extra>',
                showlegend=False
            )
        ])

        fig.update_layout(
            title=f'{symbol} - Defensive Investor Checklist',
            xaxis_title='Pass/Fail',
            xaxis=dict(tickvals=[0, 1], ticktext=['Fail', 'Pass']),
            height=400,
            template='plotly_white'
        )

        return fig

    @staticmethod
    def create_valuation_spider_chart(
        pe_ratio: float,
        pb_ratio: float,
        ps_ratio: float,
        current_ratio: float,
        debt_equity: float,
        roe: float,
        symbol: str
    ) -> go.Figure:
        """
        Create spider/radar chart showing relative valuation metrics

        Args:
            Various financial ratios
            symbol: Stock symbol

        Returns:
            Plotly Figure
        """
        categories = ['P/E', 'P/B', 'P/S', 'Current Ratio', 'Debt/Equity', 'ROE']

        # Normalize values to 0-100 scale (lower is better for most)
        values = [
            max(0, 100 - min(pe_ratio * 5, 100)),  # Lower P/E is better
            max(0, 100 - min(pb_ratio * 50, 100)),  # Lower P/B is better
            max(0, 100 - min(ps_ratio * 25, 100)),  # Lower P/S is better
            min(current_ratio * 33, 100),  # Higher current ratio is better
            max(0, 100 - min(debt_equity * 100, 100)),  # Lower debt is better
            min(roe * 500, 100)  # Higher ROE is better
        ]

        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=symbol,
            line_color='#1f77b4'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title=f'{symbol} - Valuation Profile',
            height=500,
            template='plotly_white'
        )

        return fig

    @staticmethod
    def create_earnings_history_chart(
        earnings_history: List[float],
        symbol: str
    ) -> go.Figure:
        """
        Create bar chart showing earnings history

        Args:
            earnings_history: List of annual EPS values
            symbol: Stock symbol

        Returns:
            Plotly Figure
        """
        if not earnings_history:
            return go.Figure()

        years = list(range(len(earnings_history), 0, -1))
        colors = ['#28a745' if e > 0 else '#dc3545' for e in earnings_history]

        fig = go.Figure(data=[
            go.Bar(
                x=years,
                y=earnings_history,
                marker_color=colors,
                text=[f'${e:.2f}' for e in earnings_history],
                textposition='outside',
                hovertemplate='Year %{x}<br>EPS: $%{y:.2f}<extra></extra>'
            )
        ])

        fig.update_layout(
            title=f'{symbol} - Earnings History (EPS)',
            xaxis_title='Years Ago',
            yaxis_title='EPS ($)',
            height=400,
            template='plotly_white',
            showlegend=False
        )

        fig.add_hline(y=0, line_dash="dash", line_color="gray")

        return fig
