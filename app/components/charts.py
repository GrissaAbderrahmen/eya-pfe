"""Graphiques Plotly pour le module Forex."""

import plotly.graph_objects as go

from .branding import COLORS


def price_history_chart(prices: list, moving_average: float | None = None,
                        pair: str = "EUR/USD") -> go.Figure:
    if not prices:
        fig = go.Figure()
        fig.add_annotation(text="Aucune donnée — cliquez sur Rafraîchir",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=40))
        return fig

    x = list(range(1, len(prices) + 1))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x, y=prices, mode="lines+markers",
            name=pair,
            line=dict(color=COLORS["attijari_red"], width=2.5),
            marker=dict(size=6),
        )
    )
    if moving_average is not None and len(prices) >= 2:
        fig.add_hline(
            y=moving_average,
            line_dash="dash",
            line_color=COLORS["anthracite"],
            annotation_text=f"MA = {moving_average:.4f}",
            annotation_position="top right",
        )

    fig.update_layout(
        title=f"Historique — {pair}",
        xaxis_title="Tick",
        yaxis_title="Taux",
        height=340,
        margin=dict(l=20, r=20, t=50, b=40),
        plot_bgcolor="white",
        hovermode="x unified",
    )
    return fig


def rsi_indicator(rsi_value: float) -> go.Figure:
    """Jauge RSI avec zones survente / neutre / surachat."""
    if rsi_value < 30:
        color = COLORS["success"]
    elif rsi_value > 70:
        color = COLORS["danger"]
    else:
        color = COLORS["neutral"]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=rsi_value,
            number={"font": {"size": 26, "color": COLORS["anthracite"]}},
            title={"text": "RSI", "font": {"size": 13}},
            gauge={
                "axis": {"range": [0, 100], "tickvals": [0, 30, 50, 70, 100]},
                "bar": {"color": color, "thickness": 0.28},
                "steps": [
                    {"range": [0, 30], "color": "#D8F0EC"},
                    {"range": [30, 70], "color": "#EFE9E5"},
                    {"range": [70, 100], "color": "#F7D7DB"},
                ],
            },
        )
    )
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=10))
    return fig
