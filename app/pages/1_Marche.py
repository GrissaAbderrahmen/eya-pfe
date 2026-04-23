"""Page Marché — taux en temps réel et indicateurs techniques."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

from app.core.engine import ForexAnalysisModule, MarketDataModule
from components.branding import (
    COLORS,
    inject_global_css,
    render_footer,
    render_header,
    render_module_card,
)
from components.charts import price_history_chart, rsi_indicator

st.set_page_config(page_title="Marché", page_icon="📈", layout="wide")
inject_global_css()

render_header(
    title="📈 Marché en temps réel",
    subtitle="Taux de change et indicateurs techniques (API Frankfurter + fallback simulation)",
)

# ---- Initialisation session state ----
if "market_history" not in st.session_state:
    st.session_state.market_history = {"EUR/USD": [], "USD/TND": [], "EUR/TND": []}
if "market_source" not in st.session_state:
    st.session_state.market_source = {}

# ---- Contrôles ----
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
with col_ctrl1:
    pair = st.selectbox(
        "Paire de devises",
        options=["EUR/USD", "USD/TND", "EUR/TND"],
        index=0,
        help="EUR/USD est couvert par l'API Frankfurter ; les paires TND tombent en simulation.",
    )
with col_ctrl2:
    use_api = st.toggle("Utiliser l'API Frankfurter", value=True)
with col_ctrl3:
    st.markdown(" ")
    fetch = st.button("🔄 Rafraîchir prix", type="primary", width='stretch')

if fetch:
    module = MarketDataModule(pair=pair, use_api=use_api)
    # Charger l'historique existant pour que le simulateur soit cohérent
    module.price_history = list(st.session_state.market_history[pair])
    rate, source = module.get_realtime_or_simulated_rate()
    st.session_state.market_history[pair] = module.price_history
    st.session_state.market_source[pair] = source

history = st.session_state.market_history[pair]
source = st.session_state.market_source.get(pair, "—")

# ---- Badge + dernier prix ----
if history:
    current_rate = history[-1]
    col_a, col_b = st.columns([1, 3])
    with col_a:
        badge_color = COLORS["success"] if source == "API" else COLORS["warning"]
        st.markdown(
            f'<div style="display:inline-block; padding: 0.3rem 0.9rem; border-radius: 999px; '
            f'background:{badge_color}22; color:{badge_color}; font-weight:700; '
            f'letter-spacing:0.06em;">● {source}</div>',
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            f'<div style="font-size: 0.85rem; color: #6C757D; margin-top: 0.15rem;">'
            f'Taux actuel · {pair}</div>'
            f'<div style="font-size: 2.2rem; font-weight: 700; color:{COLORS["attijari_red"]};">'
            f'{current_rate:.4f}</div>',
            unsafe_allow_html=True,
        )
else:
    st.info("Cliquez sur **Rafraîchir prix** pour démarrer la collecte des taux.", icon="ℹ️")

# ---- Graphique historique + indicateurs ----
forex = ForexAnalysisModule()

if history:
    ma = forex.calculate_moving_average(history, period=5)
    vol = forex.calculate_volatility(history, period=10)
    rsi = forex.calculate_rsi(history, period=14)
    macd = forex.calculate_macd(history, short_period=5, long_period=12)
    signal_result = forex.generate_signal(history[-1], history)

    st.plotly_chart(price_history_chart(history, ma, pair), width='stretch')

    st.subheader("Indicateurs techniques")
    col_i1, col_i2, col_i3, col_i4 = st.columns(4)
    with col_i1:
        render_module_card("Moyenne mobile (5)", f"{ma:.4f}",
                           "Tendance courte")
    with col_i2:
        render_module_card("Volatilité (σ, 10)", f"{vol:.6f}",
                           "Dispersion des prix")
    with col_i3:
        render_module_card("MACD (5-12)", f"{macd:+.4f}",
                           "Momentum — positif = haussier")
    with col_i4:
        render_module_card("Signal Forex", signal_result["signal"],
                           f"Score : {signal_result['signal_score']:+d} / 4")

    st.plotly_chart(rsi_indicator(rsi), width='stretch')

    with st.expander("🔍 Détail des règles appliquées"):
        st.markdown(
            f"""
- **Prix vs MA** : `{history[-1]:.4f}` {'>' if history[-1] > ma else '<' if history[-1] < ma else '='} `{ma:.4f}` MA
- **RSI** : `{rsi:.2f}` — {'survente (< 30) → +1' if rsi < 30 else 'surachat (> 70) → -1' if rsi > 70 else 'neutre (30-70) → 0'}
- **MACD** : `{macd:+.4f}` — {'positif → +1' if macd > 0 else 'négatif → -1' if macd < 0 else '0'}
- **Volatilité** : `{vol:.6f}` — {'élevée (> 0.01) → pénalité -1' if vol > 0.01 else 'acceptable → 0'}
- **Score agrégé** : `{signal_result['signal_score']:+d}` → **{signal_result['signal']}**
"""
        )

    # Astuce : collecter rapidement un historique
    if len(history) < 5:
        st.warning(
            f"Seulement {len(history)} point(s) dans l'historique. Cliquez plusieurs fois sur "
            f"**Rafraîchir** (ou utilisez le bouton ci-dessous) pour obtenir des indicateurs "
            f"significatifs.",
            icon="⚠️",
        )

with st.expander("🧪 Remplir l'historique rapidement (pour la démo)"):
    n = st.slider("Nombre de ticks à générer", min_value=5, max_value=60, value=20, step=5)
    if st.button("Générer maintenant"):
        module = MarketDataModule(pair=pair, use_api=False)  # simulation pour être rapide
        module.price_history = list(st.session_state.market_history[pair])
        for _ in range(n):
            module.get_realtime_or_simulated_rate()
        st.session_state.market_history[pair] = module.price_history
        st.session_state.market_source[pair] = "SIMULATION"
        st.rerun()

render_footer()
