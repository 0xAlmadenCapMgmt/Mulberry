"""Plotly chart builders for financial visualizations"""

import plotly.graph_objects as go
from typing import Dict, List, Any, Optional

from ..utils.formatters import format_currency, format_percent

# Shared color palette
_GREEN = "#10b981"
_RED = "#ef4444"
_BLUE = "#3b82f6"
_AMBER = "#f59e0b"
_SLATE = "#64748b"
_NAVY = "#0f172a"


class ChartBuilder:
    """
    Builder class for creating interactive Plotly charts.

    All methods return Plotly Figure objects that can be converted to
    self-contained HTML via fig.to_html().
    """

    @staticmethod
    def create_valuation_chart(
        valuations: Dict[str, float],
        current_price: float,
        symbol: str,
    ) -> go.Figure:
        """Bar chart comparing four intrinsic value estimates vs current price."""
        methods = [
            "Earnings-Book Value",
            "Net Asset Value",
            "Normalized Earnings",
            "Growth-Adjusted",
            "Current Price",
        ]

        values = [
            valuations.get("graham_number", 0),
            valuations.get("ncav_per_share", 0) * 0.67,
            valuations.get("normalized_value", 0),
            valuations.get("dividend_adjusted_value", 0),
            current_price,
        ]

        colors = [_GREEN, _GREEN, _GREEN, _GREEN, _RED]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=methods,
                    y=values,
                    marker_color=colors,
                    marker_line_width=0,
                    text=[format_currency(v) for v in values],
                    textposition="outside",
                    hovertemplate="%{x}<br>%{text}<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title=dict(text=f"{symbol} \u2014 Intrinsic Value Estimates", font=dict(size=14, color=_NAVY)),
            xaxis_title=None,
            yaxis_title="Price (USD)",
            showlegend=False,
            height=420,
            template="plotly_white",
            font=dict(size=12, color=_SLATE),
            margin=dict(t=50, b=40, l=60, r=20),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        fig.add_hline(
            y=current_price,
            line_dash="dash",
            line_color=_RED,
            line_width=1.5,
            annotation_text=f"Current: {format_currency(current_price)}",
            annotation_position="right",
            annotation_font_size=11,
        )

        return fig

    @classmethod
    def create_graham_valuation_chart(cls, *args, **kwargs) -> go.Figure:
        """Backward-compatible alias for create_valuation_chart."""
        return cls.create_valuation_chart(*args, **kwargs)

    @staticmethod
    def create_margin_of_safety_gauge(margin: float, symbol: str) -> go.Figure:
        """Semicircle gauge showing margin of safety."""
        margin_pct = margin * 100

        if margin >= 0.50:
            bar_color = _GREEN
        elif margin >= 0.30:
            bar_color = _BLUE
        elif margin >= 0.15:
            bar_color = _AMBER
        elif margin >= 0:
            bar_color = "#f97316"
        else:
            bar_color = _RED

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=margin_pct,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": f"{symbol} \u2014 Margin of Safety", "font": {"size": 14, "color": _NAVY}},
                number={"suffix": "%", "font": {"size": 28}},
                delta={"reference": 30, "suffix": "%"},
                gauge={
                    "axis": {"range": [-50, 100], "ticksuffix": "%", "tickfont": {"size": 11}},
                    "bar": {"color": bar_color, "thickness": 0.6},
                    "steps": [
                        {"range": [-50, 0], "color": "#fee2e2"},
                        {"range": [0, 15], "color": "#fef3c7"},
                        {"range": [15, 30], "color": "#fefce8"},
                        {"range": [30, 50], "color": "#d1fae5"},
                        {"range": [50, 100], "color": "#a7f3d0"},
                    ],
                    "threshold": {
                        "line": {"color": _NAVY, "width": 2},
                        "thickness": 0.8,
                        "value": 30,
                    },
                },
            )
        )

        fig.update_layout(
            height=340,
            template="plotly_white",
            margin=dict(t=60, b=20, l=40, r=40),
            paper_bgcolor="white",
        )

        return fig

    @staticmethod
    def create_price_history_chart(
        dates: List[str],
        prices: List[float],
        symbol: str,
        intrinsic_value: Optional[float] = None,
        graham_number: Optional[float] = None,  # legacy param name
    ) -> go.Figure:
        """Price history line chart with optional intrinsic value reference line."""
        ref_value = intrinsic_value or graham_number

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=prices,
                mode="lines",
                name="Price",
                line=dict(color=_BLUE, width=2),
                hovertemplate="%{x}<br>$%{y:.2f}<extra></extra>",
                fill="tozeroy",
                fillcolor="rgba(59,130,246,0.05)",
            )
        )

        if ref_value and ref_value > 0:
            fig.add_hline(
                y=ref_value,
                line_dash="dash",
                line_color=_GREEN,
                line_width=1.5,
                annotation_text=f"Intrinsic Value Est.: {format_currency(ref_value)}",
                annotation_position="right",
                annotation_font_size=11,
            )

        fig.update_layout(
            title=dict(text=f"{symbol} \u2014 Price History", font=dict(size=14, color=_NAVY)),
            xaxis_title=None,
            yaxis_title="Price (USD)",
            height=420,
            template="plotly_white",
            hovermode="x unified",
            font=dict(size=12, color=_SLATE),
            margin=dict(t=50, b=40, l=60, r=20),
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        return fig

    @staticmethod
    def create_financial_trends_chart(
        income_data: List[Dict[str, Any]],
        symbol: str,
    ) -> go.Figure:
        """Multi-line chart for revenue and net income trends."""
        if not income_data:
            return go.Figure()

        dates = [d["fiscalDateEnding"] for d in income_data]
        revenues = [d.get("totalRevenue", 0) / 1_000_000 for d in income_data]
        net_incomes = [d.get("netIncome", 0) / 1_000_000 for d in income_data]

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=revenues,
                mode="lines+markers",
                name="Revenue",
                line=dict(color=_BLUE, width=2),
                marker=dict(size=6),
                hovertemplate="%{x}<br>Revenue: $%{y:.1f}M<extra></extra>",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=net_incomes,
                mode="lines+markers",
                name="Net Income",
                line=dict(color=_GREEN, width=2),
                marker=dict(size=6),
                hovertemplate="%{x}<br>Net Income: $%{y:.1f}M<extra></extra>",
            )
        )

        fig.update_layout(
            title=dict(text=f"{symbol} \u2014 Financial Performance (Annual, $M)", font=dict(size=14, color=_NAVY)),
            xaxis_title=None,
            yaxis_title="Amount ($M)",
            height=420,
            template="plotly_white",
            hovermode="x unified",
            legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
            font=dict(size=12, color=_SLATE),
            margin=dict(t=50, b=40, l=70, r=20),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        return fig

    @staticmethod
    def create_health_scorecard_chart(
        checklist: Dict[str, Any], symbol: str
    ) -> go.Figure:
        """Horizontal bar chart visualizing financial health scorecard pass/fail."""
        criteria = {k: v for k, v in checklist.items() if k != "summary"}

        names, passes, colors = [], [], []
        for criterion, result in criteria.items():
            names.append(criterion.replace("_", " ").title())
            passed = result.get("pass", False)
            passes.append(1 if passed else 0)
            colors.append(_GREEN if passed else _RED)

        fig = go.Figure(
            data=[
                go.Bar(
                    y=names,
                    x=passes,
                    orientation="h",
                    marker_color=colors,
                    marker_line_width=0,
                    text=["Pass" if p == 1 else "Fail" for p in passes],
                    textposition="inside",
                    insidetextanchor="middle",
                    hovertemplate="%{y}: %{text}<extra></extra>",
                    showlegend=False,
                )
            ]
        )

        fig.update_layout(
            title=dict(text=f"{symbol} \u2014 Financial Health Scorecard", font=dict(size=14, color=_NAVY)),
            xaxis=dict(tickvals=[0, 1], ticktext=["Fail", "Pass"], showgrid=False),
            yaxis=dict(autorange="reversed"),
            height=360,
            template="plotly_white",
            font=dict(size=12, color=_SLATE),
            margin=dict(t=50, b=30, l=170, r=20),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        return fig

    @classmethod
    def create_defensive_checklist_chart(cls, *args, **kwargs) -> go.Figure:
        """Backward-compatible alias for create_health_scorecard_chart."""
        return cls.create_health_scorecard_chart(*args, **kwargs)
