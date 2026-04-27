"""Page Simulateur Trader — la page centrale de la démo jury."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from datetime import datetime

import pandas as pd
import streamlit as st

from app.core.engine import (
    AIDecisionEngine,
    ComplianceModule,
    ForexAnalysisModule,
    RiskManagementModule,
    TreasuryManagementModule,
)
from app.core.explainer import explain_decision
from app.core.market_data import fetch_history_ohlc
from app.core.yfinance_pairs import PAIRS, SIMULATED_BASE_PRICES
from components.branding import (
    COLORS,
    inject_global_css,
    render_blocked_banner,
    render_decision_badge,
    render_footer,
    render_header,
    render_module_card,
)
from components.gauges import (
    confidence_gauge,
    global_score_gauge,
    liquidity_gauge,
    normalized_scores_bar,
)

st.set_page_config(page_title="Simulateur", page_icon="💱", layout="wide")
inject_global_css()


def build_narrative(amount, direction, pair, horizon, decision,
                    forex, treasury, risk, compliance):
    """Génère un petit paragraphe d'interprétation orienté jury."""
    verb = {"BUY": "ACHETER", "SELL": "VENDRE", "HOLD": "ATTENDRE"}
    action = verb.get(decision["final_decision"], "ATTENDRE")

    parts = [
        f"Sur votre opération de **{direction.lower()} de {amount:,.0f}** en **{pair}** "
        f"à horizon **{horizon}**, le modèle recommande **{action}** avec "
        f"**{decision['confidence_score']:.0f}% de confiance**."
    ]

    if decision["decision_blocked"]:
        parts.append(
            f"⚠️ La décision est **forcée à HOLD** car : "
            f"{', '.join(decision['blocking_reasons']).lower()}."
        )
    else:
        ns = decision["normalized_scores"]
        dominant = max(ns, key=lambda k: abs(ns[k]))
        dominant_fr = {"forex": "l'analyse Forex", "treasury": "la trésorerie",
                       "risk": "le niveau de risque", "compliance": "la conformité"}[dominant]
        parts.append(
            f"Le score global pondéré est de **{decision['global_score']:+.3f}** "
            f"(seuil ACHAT : +0.5, seuil VENTE : −0.5). "
            f"Le facteur le plus influent ici est **{dominant_fr}** "
            f"(score normalisé {ns[dominant]:+.2f})."
        )

    parts.append(
        f"État des 4 modules : Forex **{forex['signal']}**, "
        f"Trésorerie **{treasury['treasury_recommendation'].split(' -> ')[0]}**, "
        f"Risque **{risk['risk_level']}**, "
        f"Conformité **{compliance['status'].replace('_', ' ')}**."
    )

    return "\n\n".join(parts)


render_header(
    title="💱 Simulateur de décision Trader",
    subtitle="Entrez les paramètres d'une opération et obtenez une recommandation complète",
)

# ==========================================================
# SCÉNARIOS PRÉ-CHARGÉS (démo jury en un clic)
# ==========================================================
SCENARIOS = {
    "— Personnalisé —": None,
    "✅ Scénario favorable (BUY attendu)": {
        "amount": 500_000, "pair": "EUR/USD", "direction": "Achat", "horizon": "1 mois",
        "cash_inflow": 1_500_000, "cash_outflow": 900_000,
        "liquidity_level": 0.75, "interbank_rate": 5.5,
        "inflation": 3.5, "cb_rate": 4.0, "exposure_level": 0.40,
        "lcr": 1.20, "position_eur": 400_000, "position_usd": 300_000,
        "position_limit": 2_000_000,
    },
    "🇹🇳 Opération EUR/TND (cas tunisien)": {
        "amount": 800_000, "pair": "EUR/TND", "direction": "Achat", "horizon": "1 mois",
        "cash_inflow": 1_200_000, "cash_outflow": 950_000,
        "liquidity_level": 0.65, "interbank_rate": 6.25,
        "inflation": 6.8, "cb_rate": 8.0, "exposure_level": 0.55,
        "lcr": 1.15, "position_eur": 600_000, "position_usd": 200_000,
        "position_limit": 2_000_000,
    },
    "⚠️ Marché stressé (HOLD attendu)": {
        "amount": 500_000, "pair": "EUR/USD", "direction": "Achat", "horizon": "1 mois",
        "cash_inflow": 900_000, "cash_outflow": 900_000,
        "liquidity_level": 0.50, "interbank_rate": 7.0,
        "inflation": 5.5, "cb_rate": 6.0, "exposure_level": 0.55,
        "lcr": 1.05, "position_eur": 400_000, "position_usd": 300_000,
        "position_limit": 2_000_000,
    },
    "⛔ Non-conformité (décision bloquée)": {
        "amount": 1_800_000, "pair": "EUR/USD", "direction": "Achat", "horizon": "3 mois",
        "cash_inflow": 800_000, "cash_outflow": 1_100_000,
        "liquidity_level": 0.35, "interbank_rate": 8.5,
        "inflation": 8.0, "cb_rate": 8.5, "exposure_level": 0.85,
        "lcr": 0.75, "position_eur": 1_500_000, "position_usd": 1_400_000,
        "position_limit": 2_000_000,
    },
}

scenario = st.selectbox(
    "🎬 Scénario pré-chargé (optionnel)",
    options=list(SCENARIOS.keys()),
    help="Chargez un scénario prêt pour la démo, puis cliquez sur Analyser.",
)
preset = SCENARIOS.get(scenario) or {}


def P(key, default):
    return preset.get(key, default)


st.divider()

# ==========================================================
# 1) INPUTS — OPÉRATION
# ==========================================================
st.subheader("1 · Paramètres de l'opération")
col_op1, col_op2, col_op3, col_op4 = st.columns(4)
with col_op1:
    amount = st.number_input("Montant (devise de base)", min_value=1_000, max_value=100_000_000,
                             value=P("amount", 500_000), step=10_000, format="%d")
with col_op2:
    default_pair = P("pair", "EUR/USD")
    pair = st.selectbox("Paire de devises", options=PAIRS,
                        index=PAIRS.index(default_pair) if default_pair in PAIRS else 0)
with col_op3:
    direction = st.selectbox("Sens", options=["Achat", "Vente"],
                             index=0 if P("direction", "Achat") == "Achat" else 1)
with col_op4:
    horizon = st.selectbox("Horizon", options=["Spot", "1 semaine", "1 mois", "3 mois"],
                           index=["Spot", "1 semaine", "1 mois", "3 mois"].index(P("horizon", "1 mois")))

# ==========================================================
# 2) INPUTS — TRÉSORERIE / RISQUE / CONFORMITÉ
# ==========================================================
st.subheader("2 · Paramètres du modèle")

with st.expander("🏦 Trésorerie", expanded=True):
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        cash_inflow = st.number_input("Cash inflow (TND)", min_value=0, max_value=50_000_000,
                                      value=P("cash_inflow", 1_200_000), step=50_000, format="%d")
    with col_t2:
        cash_outflow = st.number_input("Cash outflow (TND)", min_value=0, max_value=50_000_000,
                                       value=P("cash_outflow", 950_000), step=50_000, format="%d")
    with col_t3:
        liquidity_level = st.slider("Niveau de liquidité", 0.0, 1.0,
                                    value=float(P("liquidity_level", 0.70)), step=0.05)
    with col_t4:
        interbank_rate = st.number_input("Taux interbancaire (%)", min_value=0.0, max_value=25.0,
                                         value=float(P("interbank_rate", 6.25)), step=0.25)

with st.expander("⚠️ Risque", expanded=True):
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        inflation = st.number_input("Inflation (%)", min_value=0.0, max_value=30.0,
                                    value=float(P("inflation", 6.8)), step=0.1)
    with col_r2:
        cb_rate = st.number_input("Taux directeur BCT (%)", min_value=0.0, max_value=25.0,
                                  value=float(P("cb_rate", 8.0)), step=0.25)
    with col_r3:
        exposure_level = st.slider("Niveau d'exposition (0-1)", 0.0, 1.0,
                                   value=float(P("exposure_level", 0.65)), step=0.05)

with st.expander("📋 Conformité réglementaire", expanded=True):
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        lcr = st.number_input("LCR (Liquidity Coverage Ratio)", min_value=0.0, max_value=3.0,
                              value=float(P("lcr", 1.15)), step=0.05,
                              help="Seuil réglementaire : LCR ≥ 1.00 (100 %)")
    with col_c2:
        position_eur = st.number_input("Position EUR (avant opération)", min_value=0,
                                       max_value=100_000_000,
                                       value=P("position_eur", 400_000), step=50_000, format="%d")
    with col_c3:
        position_usd = st.number_input("Position USD (avant opération)", min_value=0,
                                       max_value=100_000_000,
                                       value=P("position_usd", 300_000), step=50_000, format="%d")
    with col_c4:
        position_limit = st.number_input("Limite par devise", min_value=100_000,
                                         max_value=100_000_000,
                                         value=P("position_limit", 2_000_000), step=100_000, format="%d")

st.divider()
analyse = st.button("🚀 **Analyser l'opération**", type="primary", width='stretch')

# ==========================================================
# 3) ANALYSE
# ==========================================================
if analyse:
    # Marché — historique réel via yfinance (cache 1h). Si yfinance ne renvoie
    # rien (paire indisponible ou réseau down), on retombe sur le taux de base
    # simulé pour ne pas bloquer la démo jury.
    df = fetch_history_ohlc(pair, period="3mo")
    if df.empty:
        st.warning(
            f"yfinance n'a pas retourné de données pour {pair}. Utilisation d'une "
            f"valeur de référence simulée — l'analyse Forex sera neutre.",
            icon="⚠️",
        )
        history = [SIMULATED_BASE_PRICES.get(pair, 1.0)]
    else:
        history = df["Close"].tolist()

    current_rate = float(history[-1])

    # Position après l'opération (impact sur conformité)
    base = pair.split("/")[0]
    delta = amount if direction == "Achat" else -amount
    pos_eur_after = position_eur + (delta if base == "EUR" else 0)
    pos_usd_after = position_usd + (delta if base == "USD" else 0)

    # Appel des modules
    forex_mod = ForexAnalysisModule()
    forex_result = forex_mod.generate_signal(current_rate, history)

    treasury_mod = TreasuryManagementModule()
    treasury_result = treasury_mod.evaluate_treasury_position(
        cash_inflow, cash_outflow, liquidity_level, interbank_rate,
    )

    risk_mod = RiskManagementModule()
    risk_result = risk_mod.assess_risk(
        inflation, cb_rate, forex_result["volatility"], exposure_level,
    )

    compliance_mod = ComplianceModule()
    compliance_result = compliance_mod.check_compliance(
        lcr, pos_eur_after, pos_usd_after, position_limit, exposure_level,
    )

    engine = AIDecisionEngine()
    decision = engine.combine_decisions(
        forex_result, treasury_result, risk_result, compliance_result,
    )

    # Persister pour la page Rapport
    st.session_state["last_simulation"] = {
        "operation": {"amount": amount, "pair": pair, "direction": direction, "horizon": horizon},
        "forex": forex_result,
        "treasury": treasury_result,
        "risk": risk_result,
        "compliance": compliance_result,
        "decision": decision,
        "position_after": {"eur": pos_eur_after, "usd": pos_usd_after},
    }

    # Historique des simulations (item #12) — FIFO, max 50 entrées
    if "simulations_history" not in st.session_state:
        st.session_state["simulations_history"] = []
    st.session_state["simulations_history"].append({
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Paire": pair,
        "Sens": direction,
        "Montant": amount,
        "Score global": round(decision["global_score"], 3),
        "Décision": decision["final_decision"],
        "Confiance %": round(decision["confidence_score"], 1),
    })
    st.session_state["simulations_history"] = st.session_state["simulations_history"][-50:]

    # --- Résultats ---
    st.subheader("3 · Résultat de l'analyse")

    render_decision_badge(decision["final_decision"])
    if decision["decision_blocked"]:
        render_blocked_banner(decision["blocking_reasons"])

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(global_score_gauge(decision["global_score"]),
                        width='stretch')
    with col_g2:
        st.plotly_chart(confidence_gauge(decision["confidence_score"]),
                        width='stretch')

    st.markdown("#### Détail des 4 modules")
    qualitative = {
        "forex": forex_result["signal"],
        "treasury": treasury_result["treasury_recommendation"].split(" -> ")[0],
        "risk": risk_result["risk_level"],
        "compliance": compliance_result["status"].replace("_", " "),
    }
    st.plotly_chart(
        normalized_scores_bar(decision["normalized_scores"], decision["weights"],
                              qualitative_labels=qualitative),
        width='stretch',
    )

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        render_module_card(
            "📈 Forex",
            forex_result["signal"],
            f"Rate {forex_result['current_rate']:.4f} · RSI {forex_result['rsi']:.1f}",
        )
    with col_m2:
        render_module_card(
            "🏦 Trésorerie",
            treasury_result["treasury_recommendation"].split(" -> ")[0],
            f"Net : {treasury_result['net_cash']:+,.0f} TND",
        )
    with col_m3:
        render_module_card(
            "⚠️ Risque",
            risk_result["risk_level"],
            f"Score {risk_result['risk_score']}/8",
        )
    with col_m4:
        render_module_card(
            "📋 Conformité",
            compliance_result["status"].replace("_", " "),
            f"{len(compliance_result['flags'])} flag(s)",
        )

    # --- Conformité en détail ---
    st.markdown("#### Contrôle conformité")
    col_lcr, col_flags = st.columns([1, 2])
    with col_lcr:
        st.plotly_chart(liquidity_gauge(lcr), width='stretch')
    with col_flags:
        if compliance_result["flags"]:
            st.markdown("**🔴 Violations réglementaires :**")
            for flag in compliance_result["flags"]:
                st.error(flag, icon="⛔")
        else:
            st.success("Tous les contrôles réglementaires sont satisfaits.", icon="✅")

        if compliance_result.get("warnings"):
            st.markdown("**🟡 Zones d'alerte (conforme mais proche du seuil) :**")
            for warning in compliance_result["warnings"]:
                st.warning(warning, icon="⚠️")

        st.caption(
            f"**Position après opération** — EUR : {pos_eur_after:,.0f} · "
            f"USD : {pos_usd_after:,.0f} (limite : {position_limit:,.0f})"
        )

    # --- Explication langage simple (pour le jury) ---
    st.markdown("#### 💡 Explication en langage simple")
    explanation = explain_decision(decision, forex_result, treasury_result,
                                   risk_result, compliance_result)
    st.info(explanation, icon="🎓")

    # --- Narratif détaillé ---
    st.markdown("#### 📝 Interprétation détaillée")
    narrative = build_narrative(amount, direction, pair, horizon, decision,
                                forex_result, treasury_result, risk_result, compliance_result)
    st.info(narrative, icon="💬")

elif "last_simulation" in st.session_state:
    st.caption("💡 Résultats de la dernière analyse conservés en mémoire — modifiez les paramètres "
               "et cliquez à nouveau sur Analyser.")
else:
    st.info("Entrez les paramètres ci-dessus puis cliquez sur **Analyser l'opération** "
            "pour obtenir une recommandation.", icon="👆")

# ==========================================================
# 4) HISTORIQUE DES SIMULATIONS (item #12)
# ==========================================================
history = st.session_state.get("simulations_history", [])
if history:
    st.divider()
    st.subheader(f"📚 Historique des simulations ({len(history)})")
    hist_df = pd.DataFrame(history[::-1])  # plus récent en haut
    st.dataframe(
        hist_df,
        width='stretch',
        column_config={
            "Montant": st.column_config.NumberColumn("Montant", format="%d"),
            "Score global": st.column_config.NumberColumn("Score global", format="%+.3f"),
            "Confiance %": st.column_config.NumberColumn("Confiance %", format="%.1f"),
        },
        hide_index=True,
    )
    if st.button("🗑️ Effacer l'historique", type="secondary"):
        st.session_state["simulations_history"] = []
        st.rerun()

render_footer()
