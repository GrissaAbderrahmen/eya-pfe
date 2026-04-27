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
    RiskManagementModule,
    TreasuryManagementModule,
)
from app.core.market_data import fetch_history_ohlc
from app.core.yfinance_pairs import SIMULATED_BASE_PRICES
from components.branding import (
    COLORS,
    inject_global_css,
    render_decision_badge,
    render_footer,
    render_header,
)
from components.charts import sensitivity_grid
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

# Forex : historique réel yfinance (cache partagé avec la page Marché)
df_hist = fetch_history_ohlc(op["pair"], period="3mo")
if df_hist.empty:
    history = [SIMULATED_BASE_PRICES.get(op["pair"], 1.0)]
else:
    history = df_hist["Close"].tolist()
current_rate = float(history[-1])
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

# ==========================================================
# Courbes de sensibilité (item #14) — score = f(paramètre)
# ==========================================================
st.divider()
st.subheader("📉 Courbes de sensibilité — score global vs chaque paramètre")
st.caption(
    "Pour chaque paramètre, on fait varier sa valeur sur 21 points autour du point courant ; "
    "tous les autres paramètres sont gelés. Les pointillés horizontaux marquent les seuils "
    "BUY (+0.5) et SELL (−0.5). Le rond noir = position actuelle des sliders."
)


def _score_at(inflation_, exposure_, liquidity_, lcr_, cb_rate_, cash_delta_):
    """Recalcule le score global avec les paramètres donnés."""
    forex_r = forex.generate_signal(current_rate, history)
    net_d = (base_treasury["net_cash"] * cash_delta_ / 100)
    treasury_r = treasury.evaluate_treasury_position(
        base_treasury["cash_inflow"] + max(0, net_d),
        base_treasury["cash_outflow"] + max(0, -net_d),
        liquidity_, base_treasury["interbank_rate"],
    )
    risk_r = risk.assess_risk(inflation_, cb_rate_, forex_r["volatility"], exposure_)
    compliance_r = compliance.check_compliance(
        lcr_, pos_after["eur"], pos_after["usd"],
        base_compliance["position_limit"], exposure_,
    )
    return engine.combine_decisions(forex_r, treasury_r, risk_r, compliance_r)["global_score"]


def _sweep(label, base, lo, hi, n=21, **fixed_kwargs):
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    ys = []
    for x in xs:
        kwargs = dict(
            inflation_=inflation, exposure_=exposure, liquidity_=liquidity,
            lcr_=lcr, cb_rate_=cb_rate, cash_delta_=cash_delta,
        )
        kwargs.update(fixed_kwargs)
        kwargs[label] = x
        ys.append(_score_at(**kwargs))
    base_y = _score_at(
        inflation_=inflation, exposure_=exposure, liquidity_=liquidity,
        lcr_=lcr, cb_rate_=cb_rate, cash_delta_=cash_delta,
    )
    return xs, ys, base, base_y


curves = []
for label, key, lo, hi, base in [
    ("Inflation (%)", "inflation_", max(0, base_risk["inflation"] - 5), base_risk["inflation"] + 5,
     inflation),
    ("Taux directeur BCT (%)", "cb_rate_", max(0, base_risk["central_bank_rate"] - 5),
     base_risk["central_bank_rate"] + 5, cb_rate),
    ("Niveau d'exposition", "exposure_", max(0, base_risk["exposure_level"] - 0.4),
     min(1.0, base_risk["exposure_level"] + 0.4), exposure),
    ("Niveau de liquidité", "liquidity_",
     max(0, base_treasury["liquidity_level"] - 0.4),
     min(1.0, base_treasury["liquidity_level"] + 0.4), liquidity),
    ("LCR", "lcr_", max(0, base_compliance["lcr"] - 0.5), base_compliance["lcr"] + 0.5, lcr),
    ("Variation cash net (%)", "cash_delta_", -100.0, 100.0, cash_delta),
]:
    xs, ys, base_x, base_y = _sweep(key, base, lo, hi)
    curves.append({"label": label, "x": xs, "y": ys, "base_x": base_x, "base_y": base_y})

st.plotly_chart(sensitivity_grid(curves), width='stretch')

render_footer()
