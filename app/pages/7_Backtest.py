"""Page Backtest — validation du modèle sur historique réel."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import plotly.graph_objects as go
import streamlit as st

from app.core.backtest import BacktestParams, naive_buy_and_hold_return, run_backtest
from app.core.yfinance_pairs import PAIRS
from components.branding import (
    COLORS,
    inject_global_css,
    render_attijari_logo,
    render_footer,
    render_header,
    render_module_card,
)

st.set_page_config(page_title="Backtest", page_icon="📊", layout="wide")
inject_global_css()
render_attijari_logo()

render_header(
    title="📊 Backtest — Validation du modèle",
    subtitle="Performance du modèle sur 6 ou 12 mois d'historique réel · "
    "Trésorerie/Risque/Conformité fixés (limitation documentée).",
)

with st.expander("⚠️ Méthodologie et limitations (à présenter au jury)"):
    st.markdown(
        """
**Définition du backtest :**
1. Pour chaque jour `J` de la période, on calcule la décision du modèle en utilisant
   uniquement les **30 derniers jours** d'historique (fenêtre glissante).
2. Pour chaque décision **BUY** ou **SELL**, on simule l'entrée au Close du jour `J`
   et la sortie au Close du jour `J + N` (holding period).
3. PnL en % : `(exit − entry) / entry`, signé selon la direction.

**Limitation honnête :** Trésorerie, Risque et Conformité sont **fixés à des valeurs
moyennes** (paramétrables ci-dessous). En production, ces variables évoluent jour par jour
mais nous n'avons pas leur historique. Cette limitation est à mentionner explicitement
en soutenance — c'est un argument de maturité scientifique.

**Comparaison naïve :** rendement « buy & hold » = acheter au premier jour, vendre au
dernier. Si le modèle bat ce benchmark, il apporte de la valeur.
"""
    )

# ---- Paramètres ----
col_p1, col_p2, col_p3, col_p4 = st.columns(4)
with col_p1:
    pair = st.selectbox("Paire", options=PAIRS, index=0)
with col_p2:
    period = st.selectbox("Période historique", options=["6mo", "1y", "2y"],
                          index=1, format_func=lambda p: {"6mo": "6 mois", "1y": "1 an",
                                                          "2y": "2 ans"}[p])
with col_p3:
    holding = st.selectbox("Holding (jours)", options=[3, 5, 10, 20], index=1)
with col_p4:
    window = st.selectbox("Fenêtre indicateurs", options=[20, 30, 60], index=1)

with st.expander("⚙️ Valeurs moyennes pour Trésorerie/Risque/Conformité (fixées sur la période)"):
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        inflation = st.number_input("Inflation moy. (%)", value=6.0, step=0.5)
        cb_rate = st.number_input("Taux directeur BCT moy. (%)", value=8.0, step=0.25)
    with col_v2:
        exposure = st.slider("Exposition moy.", 0.0, 1.0, 0.50, 0.05)
        liquidity = st.slider("Liquidité moy.", 0.0, 1.0, 0.65, 0.05)
    with col_v3:
        lcr = st.number_input("LCR moy.", value=1.20, step=0.05)
        cash_in = st.number_input("Cash inflow moy.", value=1_200_000, step=50_000, format="%d")
        cash_out = st.number_input("Cash outflow moy.", value=950_000, step=50_000, format="%d")

run = st.button("🚀 Lancer le backtest", type="primary")

if not run:
    st.info("Choisissez les paramètres puis cliquez sur **Lancer le backtest**.", icon="👆")
    render_footer()
    st.stop()

with st.spinner("Backtest en cours…"):
    params = BacktestParams(
        pair=pair, period=period, holding_days=int(holding),
        rolling_window=int(window),
        inflation=inflation, central_bank_rate=cb_rate, exposure_level=exposure,
        cash_inflow=cash_in, cash_outflow=cash_out,
        liquidity_level=liquidity, lcr=lcr,
    )
    result = run_backtest(params)
    naive = naive_buy_and_hold_return(pair, period=period)

if result.n_trades == 0:
    st.error(
        "Le backtest n'a généré aucun trade. Causes possibles : période trop courte, "
        "données yfinance absentes, ou décisions toujours HOLD/bloquées.",
        icon="⚠️",
    )
    render_footer()
    st.stop()

# ---- Indicateur de performance (item #17) ----
st.subheader("📈 Indicateur de performance du modèle")
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
with col_m1:
    render_module_card("Nombre de trades", str(result.n_trades), f"sur {len(result.decisions)} jours")
with col_m2:
    render_module_card("% trades gagnants", f"{result.win_rate:.1f}%",
                       f"{result.n_wins} gagnants sur {result.n_trades}")
with col_m3:
    render_module_card("Rendement cumulé", f"{result.total_return_pct:+.2f}%",
                       "Modèle (somme des PnL)")
with col_m4:
    render_module_card("Max drawdown", f"{result.max_drawdown_pct:.2f}%",
                       "Pire repli pic → creux")
with col_m5:
    if naive is not None:
        outperf = result.total_return_pct - naive
        render_module_card("Vs Buy & Hold", f"{outperf:+.2f} pts",
                           f"Naïf : {naive:+.2f}%")
    else:
        render_module_card("Vs Buy & Hold", "—", "Indispo")

# ---- Equity curve ----
st.subheader("Courbe d'équité du modèle")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=result.equity_curve.index, y=result.equity_curve.values,
    mode="lines", name="Modèle",
    line=dict(color=COLORS["attijari_red"], width=2.5),
    fill="tozeroy", fillcolor="rgba(200,16,46,0.08)",
))
fig.add_hline(y=1.0, line_dash="dash", line_color=COLORS["neutral"],
              annotation_text="Capital initial", annotation_position="bottom right")
fig.update_layout(
    height=380, margin=dict(l=20, r=20, t=30, b=40),
    xaxis_title="Date de sortie", yaxis_title="Capital (1.0 = initial)",
    plot_bgcolor="white",
)
st.plotly_chart(fig, width='stretch')

# ---- Distribution des PnL ----
col_d1, col_d2 = st.columns(2)
with col_d1:
    st.subheader("Distribution des PnL")
    pnls = [t.pnl_pct for t in result.trades]
    hist_fig = go.Figure(go.Histogram(
        x=pnls, nbinsx=20,
        marker_color=COLORS["attijari_red"], opacity=0.85,
    ))
    hist_fig.add_vline(x=0, line_dash="dash", line_color=COLORS["anthracite"])
    hist_fig.update_layout(
        height=320, margin=dict(l=20, r=20, t=30, b=40),
        xaxis_title="PnL (%)", yaxis_title="Nombre de trades",
        plot_bgcolor="white",
    )
    st.plotly_chart(hist_fig, width='stretch')

with col_d2:
    st.subheader("Décisions du modèle dans le temps")
    counts = result.decisions["decision"].value_counts()
    pie_fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values, hole=0.4,
        marker=dict(colors=[
            {"BUY": COLORS["success"], "SELL": COLORS["danger"],
             "HOLD": COLORS["neutral"]}.get(d, COLORS["neutral"]) for d in counts.index
        ]),
    ))
    pie_fig.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(pie_fig, width='stretch')

# ---- Tableau des trades ----
st.subheader("Détail des trades")
trades_df = result.trades_dataframe()
st.caption(f"{len(trades_df)} trades exécutés · 20 derniers affichés")
st.dataframe(trades_df.tail(20).iloc[::-1], width='stretch')

render_footer()
