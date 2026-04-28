"""Page Marché — historique OHLC réel via yfinance, indicateurs techniques, candlestick."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

from app.core.bct_scraper import compare_with_yfinance, fetch_bct_rates
from app.core.engine import ForexAnalysisModule
from app.core.market_data import fetch_history_ohlc, get_data_source
from app.core.yfinance_pairs import PAIRS
from components.branding import (
    COLORS,
    inject_global_css,
    render_footer,
    render_header,
    render_module_card,
)
from components.charts import candlestick_chart, rsi_indicator

st.set_page_config(page_title="Marché", page_icon="📈", layout="wide")
inject_global_css()

render_header(
    title="📈 Marché en temps réel",
    subtitle="Historique OHLC quotidien (Yahoo Finance) · 8 paires de devises · indicateurs techniques",
)

# ---- Initialisation session state (cache OHLC partagé entre pages) ----
if "ohlc_cache" not in st.session_state:
    st.session_state.ohlc_cache = {}

# ---- Contrôles ----
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
with col_ctrl1:
    pair = st.selectbox(
        "Paire de devises",
        options=PAIRS,
        index=0,
        help="Toutes les paires sont récupérées en données réelles via Yahoo Finance.",
    )
with col_ctrl2:
    period = st.selectbox(
        "Période",
        options=["1mo", "3mo", "6mo", "1y"],
        index=1,
        format_func=lambda p: {"1mo": "1 mois", "3mo": "3 mois", "6mo": "6 mois", "1y": "1 an"}[p],
    )
with col_ctrl3:
    st.markdown(" ")
    refresh = st.button("🔄 Rafraîchir", type="primary", width='stretch',
                        help="Recharge les données yfinance (cache 1 h).")

if refresh:
    fetch_history_ohlc.clear()  # vide le cache pour forcer un re-fetch

# ---- Récupération données ----
df = fetch_history_ohlc(pair, period=period)
st.session_state.ohlc_cache[pair] = df

if df.empty:
    st.error(
        f"Aucune donnée disponible pour {pair}. La paire est peut-être indisponible "
        f"sur Yahoo Finance, ou la connexion a échoué.",
        icon="⚠️",
    )
    render_footer()
    st.stop()

closes = df["Close"].tolist()
current_rate = float(df["Close"].iloc[-1])
prev_rate = float(df["Close"].iloc[-2]) if len(df) > 1 else current_rate
delta_pct = (current_rate - prev_rate) / prev_rate * 100 if prev_rate else 0.0

# ---- Badge source + dernier prix ----
source = get_data_source(pair)
source_color = {
    "yfinance": COLORS["success"],
    "CSV bundlé": COLORS["warning"],
    "simulation": COLORS["danger"],
}.get(source, COLORS["neutral"])
source_caption = {
    "yfinance": f"{len(df)} jours d'historique temps réel",
    "CSV bundlé": f"{len(df)} jours — Yahoo rate-limited, fallback CSV (1 an pré-téléchargé)",
    "simulation": "Données simulées — toutes les sources externes sont indisponibles",
}.get(source, "")

col_a, col_b, col_c = st.columns([1, 2, 2])
with col_a:
    st.markdown(
        f'<div style="display:inline-block; padding: 0.3rem 0.9rem; border-radius: 999px; '
        f'background:{source_color}22; color:{source_color}; font-weight:700; '
        f'letter-spacing:0.06em;">● {source.upper()}</div>',
        unsafe_allow_html=True,
    )
    st.caption(source_caption)
with col_b:
    st.markdown(
        f'<div style="font-size: 0.85rem; color: #6C757D; margin-top: 0.15rem;">'
        f'Taux actuel · {pair}</div>'
        f'<div style="font-size: 2.2rem; font-weight: 700; color:{COLORS["attijari_red"]};">'
        f'{current_rate:.4f}</div>',
        unsafe_allow_html=True,
    )
with col_c:
    delta_color = COLORS["success"] if delta_pct >= 0 else COLORS["danger"]
    arrow = "▲" if delta_pct >= 0 else "▼"
    st.markdown(
        f'<div style="font-size: 0.85rem; color: #6C757D; margin-top: 0.15rem;">'
        f'Variation jour précédent</div>'
        f'<div style="font-size: 1.6rem; font-weight: 700; color:{delta_color};">'
        f'{arrow} {delta_pct:+.2f}%</div>',
        unsafe_allow_html=True,
    )

# ---- Graphique candlestick ----
forex = ForexAnalysisModule()
ma_series = df["Close"].rolling(window=5, min_periods=1).mean()

st.plotly_chart(candlestick_chart(df, pair, moving_average=ma_series), width='stretch')

# ---- Indicateurs techniques calculés sur le Close ----
ma = forex.calculate_moving_average(closes, period=5)
vol = forex.calculate_volatility(closes, period=10)
rsi = forex.calculate_rsi(closes, period=14)
macd = forex.calculate_macd(closes, short_period=5, long_period=12)
signal_result = forex.generate_signal(current_rate, closes)

st.subheader("Indicateurs techniques")
col_i1, col_i2, col_i3, col_i4 = st.columns(4)
with col_i1:
    render_module_card("Moyenne mobile (5j)", f"{ma:.4f}", "Tendance courte")
with col_i2:
    render_module_card("Volatilité (σ, 10j)", f"{vol:.6f}", "Dispersion des prix")
with col_i3:
    render_module_card("MACD (5-12)", f"{macd:+.4f}", "Momentum — positif = haussier")
with col_i4:
    render_module_card("Signal Forex", signal_result["signal"],
                       f"Score : {signal_result['signal_score']:+d} / 4")

st.plotly_chart(rsi_indicator(rsi), width='stretch')

st.caption(
    "ℹ️ Les indicateurs techniques (RSI 14j, MACD 5/12, MA 5j, Volatilité 10j) "
    "utilisent des **fenêtres standards** de l'analyse technique et sont indépendants "
    "de la période d'historique sélectionnée ci-dessus. Changer la période modifie "
    "le candlestick et le tableau OHLC, pas les indicateurs (qui regardent toujours "
    "les N derniers jours)."
)

with st.expander("🔍 Détail des règles appliquées"):
    st.markdown(
        f"""
- **Prix vs MA** : `{current_rate:.4f}` {'>' if current_rate > ma else '<' if current_rate < ma else '='} `{ma:.4f}` MA
- **RSI** : `{rsi:.2f}` — {'survente (< 30) → +1' if rsi < 30 else 'surachat (> 70) → -1' if rsi > 70 else 'neutre (30-70) → 0'}
- **MACD** : `{macd:+.4f}` — {'positif → +1' if macd > 0 else 'négatif → -1' if macd < 0 else '0'}
- **Volatilité** : `{vol:.6f}` — {'élevée (> 0.01) → pénalité' if vol > 0.01 else 'acceptable → 0'}
- **Score agrégé** : `{signal_result['signal_score']:+d}` → **{signal_result['signal']}**
"""
    )

# ---- Comparaison avec taux officiel BCT (paires TND uniquement) ----
if "TND" in pair:
    st.subheader("🏛️ Comparaison avec le taux officiel BCT")
    with st.spinner("Récupération du cours BCT…"):
        bct_rates = fetch_bct_rates()
    if not bct_rates:
        st.info(
            "Source BCT indisponible (le scraping a échoué — site BCT inaccessible "
            "ou structure modifiée). Le taux yfinance reste utilisable.",
            icon="ℹ️",
        )
    else:
        comparison = compare_with_yfinance(bct_rates, current_rate, pair)
        if comparison is None:
            st.info(f"BCT n'a pas publié de cours pour {pair} aujourd'hui.", icon="ℹ️")
        else:
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                render_module_card(
                    "Taux BCT officiel",
                    f"{comparison['bct_rate']:.4f}",
                    f"1 {comparison['currency']} = ? TND",
                )
            with col_b2:
                render_module_card(
                    "Taux yfinance",
                    f"{comparison['yfinance_rate']:.4f}",
                    "Cours du marché",
                )
            with col_b3:
                delta_color = COLORS["success"] if abs(comparison['delta_pct']) < 1 \
                    else COLORS["warning"]
                render_module_card(
                    "Écart yfinance vs BCT",
                    f"{comparison['delta_pct']:+.3f}%",
                    "< 1% = parité normale",
                )
            st.caption(f"Source : {bct_rates.get('_source', 'BCT')}")

# ---- Tableau OHLC (30 derniers jours) ----
st.subheader("Données OHLC quotidiennes")
st.caption(
    "Open / High / Low / Close — base de calcul des indicateurs techniques (RSI, MACD, MA). "
    "30 derniers jours, du plus récent au plus ancien."
)
ohlc_display = df.tail(30).iloc[::-1].copy()
ohlc_display.index = ohlc_display.index.strftime("%Y-%m-%d")
ohlc_display = ohlc_display.round(4)
st.dataframe(
    ohlc_display,
    width='stretch',
    column_config={
        "Open": st.column_config.NumberColumn("Open", format="%.4f"),
        "High": st.column_config.NumberColumn("High", format="%.4f"),
        "Low": st.column_config.NumberColumn("Low", format="%.4f"),
        "Close": st.column_config.NumberColumn("Close", format="%.4f"),
    },
)

render_footer()
