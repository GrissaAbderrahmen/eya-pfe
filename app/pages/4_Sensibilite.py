"""Page Sensibilité — tester la robustesse de la décision en faisant varier les inputs."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

from app.core.engine import (
    AIDecisionEngine,
    ComplianceModule,
    ForexAnalysisModule,
    MarketDataModule,
    RiskManagementModule,
    TreasuryManagementModule,
)
from components.branding import (
    COLORS,
    inject_global_css,
    render_decision_badge,
    render_footer,
    render_header,
)
from components.gauges import global_score_gauge

st.set_page_config(page_title="Sensibilité", page_icon="🎚", layout="wide")
inject_global_css()

render_header(
    title="🎚 Analyse de sensibilité",
    subtitle="Variez chaque input pour tester la robustesse de la décision du modèle",
)

sim = st.session_state.get("last_simulation")
if not sim:
    st.warning(
        "Lancez d'abord une simulation depuis la page **Simulateur** — cette page variera "
        "ses inputs pour mesurer la robustesse.",
        icon="👈",
    )
    render_footer()
    st.stop()

# Inputs de base (depuis la dernière simulation)
base_treasury = sim["treasury"]
base_risk = sim["risk"]
base_compliance = sim["compliance"]
base_decision = sim["decision"]
op = sim["operation"]
pos_after = sim["position_after"]

st.caption(
    f"Simulation de référence : {op['direction']} de {op['amount']:,.0f} en {op['pair']} · "
    f"score global de base **{base_decision['global_score']:+.3f}** → **{base_decision['final_decision']}**"
)

st.divider()
st.markdown("### Variez les paramètres")

col_s1, col_s2 = st.columns(2)
with col_s1:
    inflation = st.slider(
        "Inflation (%)",
        min_value=max(0.0, base_risk["inflation"] - 3.0),
        max_value=base_risk["inflation"] + 3.0,
        value=base_risk["inflation"],
        step=0.1,
        help="Impact direct sur le score de risque.",
    )
    exposure = st.slider(
        "Niveau d'exposition",
        min_value=max(0.0, base_risk["exposure_level"] - 0.20),
        max_value=min(1.0, base_risk["exposure_level"] + 0.20),
        value=base_risk["exposure_level"],
        step=0.01,
    )
    liquidity = st.slider(
        "Niveau de liquidité",
        min_value=max(0.0, base_treasury["liquidity_level"] - 0.20),
        max_value=min(1.0, base_treasury["liquidity_level"] + 0.20),
        value=base_treasury["liquidity_level"],
        step=0.01,
    )

with col_s2:
    lcr = st.slider(
        "LCR",
        min_value=max(0.0, base_compliance["lcr"] - 0.30),
        max_value=base_compliance["lcr"] + 0.30,
        value=base_compliance["lcr"],
        step=0.01,
    )
    cb_rate = st.slider(
        "Taux directeur BCT (%)",
        min_value=max(0.0, base_risk["central_bank_rate"] - 3.0),
        max_value=base_risk["central_bank_rate"] + 3.0,
        value=base_risk["central_bank_rate"],
        step=0.25,
    )
    cash_delta = st.slider(
        "Variation du cash net (%)",
        min_value=-50.0,
        max_value=50.0,
        value=0.0,
        step=5.0,
        help="±50 % sur le net cash inflow — outflow de base.",
    )

# Recalcul en direct
forex = ForexAnalysisModule()
treasury = TreasuryManagementModule()
risk = RiskManagementModule()
compliance = ComplianceModule()
engine = AIDecisionEngine()

# Forex : on rejoue sur l'historique du marché déjà disponible ou on simule vite
history = st.session_state.get("market_history", {}).get(op["pair"], [])
if len(history) < 5:
    market = MarketDataModule(pair=op["pair"], use_api=False)
    for _ in range(20):
        market.get_realtime_or_simulated_rate()
    history = market.price_history
current_rate = history[-1]
forex_result = forex.generate_signal(current_rate, history)

# Trésorerie : applique la variation au net cash
net_delta = (base_treasury["net_cash"] * cash_delta / 100)
adj_inflow = base_treasury["cash_inflow"] + max(0, net_delta)
adj_outflow = base_treasury["cash_outflow"] + max(0, -net_delta)
treasury_result = treasury.evaluate_treasury_position(
    adj_inflow, adj_outflow, liquidity, base_treasury["interbank_rate"],
)

risk_result = risk.assess_risk(inflation, cb_rate, forex_result["volatility"], exposure)

compliance_result = compliance.check_compliance(
    lcr, pos_after["eur"], pos_after["usd"],
    base_compliance["position_limit"], exposure,
)

decision = engine.combine_decisions(forex_result, treasury_result, risk_result, compliance_result)

# Affichage comparé
st.divider()
st.markdown("### Résultat en temps réel")

col_r1, col_r2, col_r3 = st.columns([1, 1, 1])
with col_r1:
    st.plotly_chart(global_score_gauge(decision["global_score"]), width='stretch')

with col_r2:
    delta = decision["global_score"] - base_decision["global_score"]
    st.metric(
        "Score global",
        f"{decision['global_score']:+.3f}",
        delta=f"{delta:+.3f} vs base",
        delta_color="normal",
    )
    st.metric(
        "Confiance",
        f"{decision['confidence_score']:.0f} %",
        delta=f"{decision['confidence_score'] - base_decision['confidence_score']:+.0f} pts",
        delta_color="normal",
    )

with col_r3:
    st.markdown("#### Décision")
    render_decision_badge(decision["final_decision"])
    if decision["final_decision"] != base_decision["final_decision"]:
        st.warning(
            f"⚠️ Décision **changée** par rapport à la base "
            f"({base_decision['final_decision']} → {decision['final_decision']})",
            icon="🔄",
        )
    else:
        st.success("Décision **inchangée** par rapport à la base.", icon="✅")

with st.expander("Voir l'état des 4 modules après variation"):
    st.markdown(
        f"""
- 📈 **Forex** : signal {forex_result['signal']} (score normalisé {decision['normalized_scores']['forex']:+.2f})
- 🏦 **Trésorerie** : {treasury_result['treasury_recommendation']} (score normalisé {decision['normalized_scores']['treasury']:+.2f})
- ⚠️ **Risque** : {risk_result['risk_level']} — score {risk_result['risk_score']}/8 (score normalisé {decision['normalized_scores']['risk']:+.2f})
- 📋 **Conformité** : {compliance_result['status']} — {len(compliance_result['flags'])} flag(s) (score normalisé {decision['normalized_scores']['compliance']:+.2f})
"""
    )
    if compliance_result["flags"]:
        for flag in compliance_result["flags"]:
            st.caption(f"⚠️ {flag}")

st.info(
    "**À présenter au jury** : démontrer qu'en déplaçant l'inflation ou l'exposition de quelques "
    "points, la décision peut basculer — ce qui prouve que le modèle est bien **réactif** aux "
    "conditions de marché.",
    icon="🎓",
)

render_footer()
