"""Graphiques Plotly pour le module Forex."""

from __future__ import annotations

import pandas as pd
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


def candlestick_chart(df: pd.DataFrame, pair: str = "EUR/USD",
                      moving_average: pd.Series | None = None) -> go.Figure:
    """Vrai graphique en chandeliers japonais (OHLC) à partir d'un DataFrame yfinance.

    df doit contenir les colonnes Open / High / Low / Close, indexé par date.
    moving_average (optionnel) : série pandas alignée sur df.index, tracée en surimpression.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible — vérifiez la paire ou réessayez",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=40, b=40))
        return fig

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=pair,
            increasing_line_color=COLORS["success"],
            decreasing_line_color=COLORS["danger"],
            increasing_fillcolor=COLORS["success"],
            decreasing_fillcolor=COLORS["danger"],
        )
    )

    if moving_average is not None and len(moving_average.dropna()) >= 2:
        fig.add_trace(
            go.Scatter(
                x=moving_average.index,
                y=moving_average.values,
                mode="lines",
                name="MA 5j",
                line=dict(color=COLORS["attijari_red"], width=2, dash="dot"),
            )
        )

    fig.update_layout(
        title=f"Chandeliers japonais — {pair}",
        xaxis_title="Date",
        yaxis_title="Taux",
        height=440,
        margin=dict(l=20, r=20, t=50, b=40),
        plot_bgcolor="white",
        xaxis=dict(rangeslider=dict(visible=False), showgrid=True, gridcolor="#EFE9E5"),
        yaxis=dict(showgrid=True, gridcolor="#EFE9E5"),
        showlegend=True,
        legend=dict(orientation="h", y=1.02, x=0),
    )
    return fig


def sensitivity_grid(curves: list[dict]) -> go.Figure:
    """Grille de mini-courbes : score global = f(paramètre).

    `curves` : liste de dicts {label, x, y, base_x, base_y}.
    """
    from plotly.subplots import make_subplots

    n = len(curves)
    cols = 3
    rows = (n + cols - 1) // cols
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[c["label"] for c in curves],
        horizontal_spacing=0.10, vertical_spacing=0.18,
    )

    for i, curve in enumerate(curves):
        r, c = i // cols + 1, i % cols + 1
        fig.add_trace(
            go.Scatter(
                x=curve["x"], y=curve["y"], mode="lines",
                line=dict(color=COLORS["attijari_red"], width=2),
                showlegend=False,
            ),
            row=r, col=c,
        )
        # Marqueur du point de base
        fig.add_trace(
            go.Scatter(
                x=[curve["base_x"]], y=[curve["base_y"]],
                mode="markers",
                marker=dict(size=10, color=COLORS["anthracite"], symbol="circle-open",
                            line=dict(width=2, color=COLORS["anthracite"])),
                showlegend=False,
                hovertemplate=f"Base : {curve['base_x']:.3f} → {curve['base_y']:+.3f}<extra></extra>",
            ),
            row=r, col=c,
        )
        # Lignes seuils BUY/SELL
        for thr, color in [(0.5, COLORS["success"]), (-0.5, COLORS["danger"])]:
            fig.add_hline(y=thr, line_dash="dot", line_color=color, opacity=0.3,
                          row=r, col=c)
        fig.update_yaxes(range=[-1.1, 1.1], row=r, col=c)

    fig.update_layout(
        height=240 * rows + 40, margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="white",
    )
    return fig


def risk_by_currency_chart(positions: dict, limit: float) -> go.Figure:
    """Bar chart horizontal — exposition par devise. Code couleur LOW/MEDIUM/HIGH."""
    if not positions:
        fig = go.Figure()
        fig.add_annotation(text="Aucune position renseignée",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=280, margin=dict(l=20, r=20, t=20, b=20))
        return fig

    sorted_items = sorted(positions.items(), key=lambda kv: abs(kv[1]), reverse=True)
    currencies = [c for c, _ in sorted_items]
    values = [abs(v) for _, v in sorted_items]
    pcts = [v / limit * 100 if limit else 0 for v in values]

    def color_for(pct):
        if pct >= 100:
            return COLORS["danger"]
        if pct >= 70:
            return COLORS["warning"]
        return COLORS["success"]

    colors = [color_for(p) for p in pcts]
    labels = [f"{v:,.0f} ({p:.0f}% de la limite)" for v, p in zip(values, pcts)]

    fig = go.Figure(go.Bar(
        x=values, y=currencies, orientation="h",
        marker_color=colors, text=labels, textposition="outside",
    ))
    fig.add_vline(x=limit, line_dash="dash", line_color=COLORS["danger"],
                  annotation_text=f"Limite {limit:,.0f}",
                  annotation_position="top")
    fig.update_layout(
        height=80 + 40 * len(currencies), margin=dict(l=20, r=80, t=20, b=20),
        xaxis_title="Position absolue", yaxis=dict(autorange="reversed"),
        plot_bgcolor="white",
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
