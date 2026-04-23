"""Jauges Plotly réutilisables."""

import plotly.graph_objects as go

from .branding import COLORS


def confidence_gauge(value: float, title: str = "Niveau de confiance") -> go.Figure:
    """Jauge 0-100 avec 3 zones colorées."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            number={"suffix": " %", "font": {"size": 34, "color": COLORS["anthracite"]}},
            title={"text": title, "font": {"size": 14, "color": COLORS["neutral"]}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": COLORS["neutral"]},
                "bar": {"color": COLORS["attijari_red"], "thickness": 0.25},
                "steps": [
                    {"range": [0, 40], "color": "#F7D7DB"},
                    {"range": [40, 70], "color": "#FCE4CF"},
                    {"range": [70, 100], "color": "#D8F0EC"},
                ],
                "threshold": {
                    "line": {"color": COLORS["anthracite"], "width": 3},
                    "thickness": 0.8,
                    "value": value,
                },
            },
        )
    )
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def global_score_gauge(value: float, buy_threshold: float = 0.5,
                       sell_threshold: float = -0.5) -> go.Figure:
    """Jauge du score global (-1 à +1) avec zones BUY/HOLD/SELL."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"valueformat": ".3f", "font": {"size": 32, "color": COLORS["anthracite"]}},
            title={"text": "Score global pondéré", "font": {"size": 14, "color": COLORS["neutral"]}},
            gauge={
                "axis": {"range": [-1, 1], "tickwidth": 1, "tickcolor": COLORS["neutral"],
                         "tickvals": [-1, sell_threshold, 0, buy_threshold, 1]},
                "bar": {"color": COLORS["anthracite"], "thickness": 0.18},
                "steps": [
                    {"range": [-1, sell_threshold], "color": "#F7D7DB"},
                    {"range": [sell_threshold, buy_threshold], "color": "#EFE9E5"},
                    {"range": [buy_threshold, 1], "color": "#D8F0EC"},
                ],
            },
        )
    )
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def liquidity_gauge(lcr: float) -> go.Figure:
    """Jauge du LCR (Liquidity Coverage Ratio)."""
    pct = lcr * 100
    color = COLORS["success"] if lcr >= 1.0 else COLORS["danger"]
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct,
            number={"suffix": " %", "font": {"size": 28, "color": COLORS["anthracite"]}},
            title={"text": "LCR — Seuil réglementaire 100 %", "font": {"size": 13}},
            gauge={
                "axis": {"range": [0, 200], "tickwidth": 1, "tickcolor": COLORS["neutral"]},
                "bar": {"color": color, "thickness": 0.28},
                "steps": [
                    {"range": [0, 100], "color": "#F7D7DB"},
                    {"range": [100, 200], "color": "#D8F0EC"},
                ],
                "threshold": {
                    "line": {"color": COLORS["attijari_red"], "width": 3},
                    "thickness": 0.85,
                    "value": 100,
                },
            },
        )
    )
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def normalized_scores_bar(normalized_scores: dict, weights: dict) -> go.Figure:
    """Barres horizontales des 4 scores normalisés, pondérés en opacité."""
    labels_fr = {
        "forex": "Forex",
        "treasury": "Trésorerie",
        "risk": "Risque",
        "compliance": "Conformité",
    }
    keys = ["forex", "treasury", "risk", "compliance"]
    labels = [f"{labels_fr[k]} · poids {int(weights[k]*100)}%" for k in keys]
    values = [normalized_scores[k] for k in keys]
    colors = [COLORS["success"] if v > 0 else COLORS["danger"] if v < 0 else COLORS["neutral"]
              for v in values]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.2f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        xaxis=dict(range=[-1.15, 1.15], tickvals=[-1, -0.5, 0, 0.5, 1], zeroline=True,
                   zerolinecolor=COLORS["anthracite"], zerolinewidth=1.5),
        yaxis=dict(autorange="reversed"),
        height=280,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="white",
    )
    return fig
