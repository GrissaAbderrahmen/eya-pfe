"""Page Risques — carte d'exposition par devise."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import plotly.graph_objects as go
import streamlit as st

from components.branding import (
    COLORS,
    inject_global_css,
    render_attijari_logo,
    render_footer,
    render_header,
)
from components.charts import risk_by_currency_chart

st.set_page_config(page_title="Risques", page_icon="🌍", layout="wide")
inject_global_css()
render_attijari_logo()

render_header(
    title="🌍 Carte des risques par devise",
    subtitle="Visualisation de l'exposition de la banque par devise · "
    "code couleur LOW (<70%) / WARNING (70-100%) / HIGH (≥100% de la limite)",
)

# Pré-remplir depuis la dernière simulation si disponible
sim = st.session_state.get("last_simulation")
default_eur = 400_000
default_usd = 300_000
if sim and "position_after" in sim:
    default_eur = int(sim["position_after"].get("eur", default_eur))
    default_usd = int(sim["position_after"].get("usd", default_usd))

# ---- Inputs ----
st.subheader("Positions par devise")
col_lim, _ = st.columns([1, 3])
with col_lim:
    limit = st.number_input(
        "Limite par devise (TND)",
        value=2_000_000, step=100_000, format="%d",
        help="Limite réglementaire BCT par position devise.",
    )

cols = st.columns(6)
positions: dict[str, float] = {}
for col, (currency, default) in zip(cols, [
    ("EUR", default_eur),
    ("USD", default_usd),
    ("GBP", 200_000),
    ("JPY", 150_000),
    ("CHF", 100_000),
    ("TND", 1_500_000),
]):
    with col:
        v = st.number_input(
            f"{currency}", min_value=0, max_value=100_000_000,
            value=int(default), step=50_000, format="%d", key=f"pos_{currency}",
        )
        positions[currency] = float(v)

st.divider()

# ---- Synthèse globale ----
total_exposure = sum(positions.values())
n_breach = sum(1 for v in positions.values() if v > limit)
n_warning = sum(1 for v in positions.values() if 0.7 * limit < v <= limit)
n_low = sum(1 for v in positions.values() if v <= 0.7 * limit)

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.metric("Exposition totale", f"{total_exposure:,.0f}")
with col_s2:
    st.metric("Devises au-dessus de la limite", n_breach,
              delta="VIOLATION BCT" if n_breach > 0 else "OK",
              delta_color="inverse" if n_breach > 0 else "normal")
with col_s3:
    st.metric("Devises en zone d'alerte", n_warning, delta="70-100% de la limite")
with col_s4:
    st.metric("Devises sous contrôle", n_low, delta="< 70%")

# ---- Bar chart ----
st.subheader("📊 Exposition par devise")
st.plotly_chart(risk_by_currency_chart(positions, limit), width='stretch')

# ---- Treemap (vue alternative) ----
st.subheader("🗺️ Vue treemap")

def _color(v):
    if v >= limit:
        return COLORS["danger"]
    if v >= 0.7 * limit:
        return COLORS["warning"]
    return COLORS["success"]

treemap = go.Figure(go.Treemap(
    labels=list(positions.keys()),
    parents=[""] * len(positions),
    values=list(positions.values()),
    text=[f"{v:,.0f}<br>{v / limit * 100:.0f}% limite" for v in positions.values()],
    textinfo="label+text",
    marker=dict(colors=[_color(v) for v in positions.values()]),
))
treemap.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(treemap, width='stretch')

# ---- Liste des breaches ----
breaches = [(c, v) for c, v in positions.items() if v > limit]
warnings = [(c, v) for c, v in positions.items() if 0.7 * limit < v <= limit]

if breaches:
    st.subheader("🔴 Violations réglementaires détectées")
    for c, v in breaches:
        st.error(
            f"**{c}** : position {v:,.0f} dépasse la limite par devise "
            f"({limit:,.0f}) — excédent de {v - limit:,.0f}",
            icon="⛔",
        )

if warnings:
    st.subheader("🟡 Zones d'alerte")
    for c, v in warnings:
        st.warning(
            f"**{c}** : position {v:,.0f} ({v / limit * 100:.0f}% de la limite) — "
            f"surveiller cette exposition",
            icon="⚠️",
        )

if not breaches and not warnings:
    st.success(
        "Toutes les positions sont sous le seuil d'alerte de 70% — exposition saine.",
        icon="✅",
    )

render_footer()
