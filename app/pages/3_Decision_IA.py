"""Page Décision IA — explication pédagogique pas-à-pas de la formule pondérée."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

from components.branding import (
    COLORS,
    inject_global_css,
    render_decision_badge,
    render_footer,
    render_header,
)
from components.gauges import global_score_gauge, normalized_scores_bar

st.set_page_config(page_title="Décision IA", page_icon="🤖", layout="wide")
inject_global_css()

render_header(
    title="🤖 Moteur de décision — Vue pédagogique",
    subtitle="Comprendre pas-à-pas comment le modèle aboutit à la recommandation finale",
)

sim = st.session_state.get("last_simulation")

if not sim:
    st.warning(
        "Aucune simulation en mémoire. Passez d'abord par la page **Simulateur** "
        "pour lancer une analyse, puis revenez ici pour la détailler.",
        icon="👈",
    )
    render_footer()
    st.stop()

decision = sim["decision"]
ns = decision["normalized_scores"]
w = decision["weights"]

# ==========================================================
# ÉTAPE 1 — Rappel de la formule
# ==========================================================
st.subheader("Étape 1 · La formule pondérée")
st.markdown(
    r"""
$$
\text{Score global} \;=\;
0.40 \cdot S_{\text{Forex}}
\;+\; 0.25 \cdot S_{\text{Trésorerie}}
\;+\; 0.25 \cdot S_{\text{Risque}}
\;+\; 0.10 \cdot S_{\text{Conformité}}
$$

Chaque score $S_i$ est **normalisé dans l'intervalle $[-1, +1]$** pour que les modules soient
comparables. Le score global résultant est donc lui aussi borné dans $[-1, +1]$.

**Seuils de décision :**
- Score **> +0.5** → **ACHAT (BUY)**
- Score **< −0.5** → **VENTE (SELL)**
- Entre les deux → **ATTENTE (HOLD)**
"""
)

st.info(
    "Les pondérations reflètent l'importance accordée à chaque dimension dans la stratégie de "
    "la banque. Le Forex domine car il capte la dynamique de marché court terme. La conformité "
    "a le plus faible poids *direct* — mais c'est un **bloqueur dur** en cas de non-conformité.",
    icon="💡",
)

# ==========================================================
# ÉTAPE 2 — Valeurs normalisées
# ==========================================================
st.subheader("Étape 2 · Scores normalisés des 4 modules")

st.plotly_chart(normalized_scores_bar(ns, w), width='stretch')

col_n1, col_n2, col_n3, col_n4 = st.columns(4)
for col, (key, label, color) in zip(
    [col_n1, col_n2, col_n3, col_n4],
    [
        ("forex", "📈 Forex", COLORS["attijari_red"]),
        ("treasury", "🏦 Trésorerie", COLORS["anthracite"]),
        ("risk", "⚠️ Risque", COLORS["warning"]),
        ("compliance", "📋 Conformité", COLORS["success"]),
    ],
):
    with col:
        st.markdown(
            f"""
<div class="module-card" style="border-left: 4px solid {color};">
    <div class="label">{label}</div>
    <div class="value">{ns[key]:+.3f}</div>
    <div class="hint">Poids {int(w[key]*100)} %</div>
</div>
            """,
            unsafe_allow_html=True,
        )

# ==========================================================
# ÉTAPE 3 — Calcul détaillé
# ==========================================================
st.subheader("Étape 3 · Calcul détaillé du score global")

components = [
    ("Forex", w["forex"], ns["forex"]),
    ("Trésorerie", w["treasury"], ns["treasury"]),
    ("Risque", w["risk"], ns["risk"]),
    ("Conformité", w["compliance"], ns["compliance"]),
]
total = 0.0
lines = []
for label, weight, score in components:
    contrib = weight * score
    total += contrib
    sign = "+" if contrib >= 0 else "−"
    lines.append(
        f"| **{label}** | {weight:.2f} | {score:+.3f} | "
        f"{sign} {abs(contrib):.4f} |"
    )

st.markdown(
    "| Module | Poids | Score normalisé | Contribution |\n"
    "|---|:---:|:---:|:---:|\n"
    + "\n".join(lines)
    + f"\n| **Total** | | | **{total:+.4f}** |"
)

st.markdown(
    f"""
```
Score global = (0.40 × {ns["forex"]:+.3f})  +  (0.25 × {ns["treasury"]:+.3f})
              + (0.25 × {ns["risk"]:+.3f})  +  (0.10 × {ns["compliance"]:+.3f})
            = {total:+.4f}
```
"""
)

# ==========================================================
# ÉTAPE 4 — Application des seuils et bloqueurs
# ==========================================================
st.subheader("Étape 4 · Application des seuils et bloqueurs durs")

soft = decision["soft_decision"]
final = decision["final_decision"]
blocked = decision["decision_blocked"]

col_gs, col_deco = st.columns([1, 1])
with col_gs:
    st.plotly_chart(global_score_gauge(decision["global_score"]), width='stretch')

with col_deco:
    st.markdown("**A. Application des seuils :**")
    if decision["global_score"] > 0.5:
        st.markdown(f"- Score **{decision['global_score']:+.3f}** > +0.5 → décision provisoire **BUY**")
    elif decision["global_score"] < -0.5:
        st.markdown(f"- Score **{decision['global_score']:+.3f}** < −0.5 → décision provisoire **SELL**")
    else:
        st.markdown(f"- Score **{decision['global_score']:+.3f}** entre −0.5 et +0.5 → décision provisoire **HOLD**")

    st.markdown("**B. Vérification des bloqueurs durs :**")
    if blocked:
        for reason in decision["blocking_reasons"]:
            st.error(f"❌ {reason}", icon="⛔")
        st.markdown(f"→ Décision **forcée à HOLD** (malgré la décision provisoire **{soft}**).")
    else:
        st.success("Aucun bloqueur déclenché (risque non-HIGH et conformité satisfaite).", icon="✅")
        st.markdown(f"→ Décision conservée : **{final}**")

# ==========================================================
# ÉTAPE 5 — Décision finale
# ==========================================================
st.subheader("Étape 5 · Décision finale")
render_decision_badge(final)

st.markdown(
    f"""
<div style="text-align: center; font-size: 1.1rem; color: #6C757D; margin-top: -0.5rem;">
    Niveau de confiance : <strong style="color: #2B2B2B;">{decision['confidence_score']:.0f} %</strong>
</div>
""",
    unsafe_allow_html=True,
)

# ==========================================================
# Rappel du contexte de la simulation
# ==========================================================
with st.expander("📎 Contexte de cette simulation"):
    op = sim["operation"]
    st.markdown(
        f"""
- **Opération analysée** : {op['direction']} de **{op['amount']:,.0f}** en **{op['pair']}** — horizon **{op['horizon']}**
- **Modules évalués** :
  - Forex : `signal_score` = {sim['forex']['signal_score']:+d}, signal = **{sim['forex']['signal']}**
  - Trésorerie : `net_cash` = {sim['treasury']['net_cash']:+,.0f} — **{sim['treasury']['treasury_recommendation']}**
  - Risque : niveau **{sim['risk']['risk_level']}** (score brut {sim['risk']['risk_score']}/8)
  - Conformité : statut **{sim['compliance']['status'].replace('_', ' ')}** ({len(sim['compliance']['flags'])} flag(s))
"""
    )

render_footer()
