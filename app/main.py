"""Page d'accueil du web-app PFE Eya (Streamlit entry point)."""

import os
import sys

# Permettre les imports relatifs quand Streamlit lance le script
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from components.branding import (
    COLORS,
    inject_global_css,
    render_attijari_logo,
    render_footer,
    render_header,
)

st.set_page_config(
    page_title="ADD Salle de Marché — Attijari Bank",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_attijari_logo()

render_header(
    title="Système d'aide à la décision — Salle de marché",
    subtitle="PFE Licence en Gestion · Cas Attijari Bank Tunisie · Prototype fonctionnel",
)

st.markdown(
    """
### Bienvenue dans le prototype de démonstration

Cet outil illustre le fonctionnement d'un **système d'aide à la décision** destiné aux traders
d'une salle de marché bancaire. Il combine quatre dimensions financières pour recommander
une action (achat / vente / attente) sur une opération de change, avec un **niveau de confiance**
et des **contrôles de conformité réglementaire BCT**.

#### Architecture en 7 modules

| # | Module | Rôle | Type | Poids |
|:-:|---|---|:-:|:-:|
| 1 | 🛰️ **Collecte des données** | Récupération OHLC quotidien réel via Yahoo Finance | Infrastructure | — |
| 2 | 📈 **Analyse Forex** | Indicateurs techniques : MA, RSI, MACD, volatilité | Décision | **40 %** |
| 3 | 🏦 **Trésorerie** | Liquidité, flux net, taux interbancaire | Décision | **25 %** |
| 4 | ⚠️ **Risque** | Inflation, taux directeur BCT, exposition, volatilité FX | Décision | **25 %** |
| 5 | 📋 **Conformité BCT** | LCR ≥ 100 %, limites par devise, exposition ≤ 80 % | Décision | **10 %** |
| 6 | 🤖 **Moteur de décision intelligent** | Agrège les 4 modules de décision via la formule pondérée | Infrastructure | — |
| 7 | 💬 **Interaction trader (Chat IA)** | Chat Gemini en français contextualisé sur la simulation | Infrastructure | — |

**Total des poids des modules de décision : 100 %.** Les modules d'infrastructure ne pèsent
pas dans le score (ils alimentent ou exposent les résultats), mais ils sont essentiels au pipeline.

#### Formule de décision

> **Score global** = (Forex × 0.40) + (Trésorerie × 0.25) + (Risque × 0.25) + (Conformité × 0.10)

- Si **Score > +0.5** → recommandation **ACHAT (BUY)**
- Si **Score < −0.5** → recommandation **VENTE (SELL)**
- Sinon → **ATTENTE (HOLD)**

**Bloqueurs durs** : en cas de risque élevé (HIGH) ou de non-conformité (NON_COMPLIANT),
la décision est automatiquement forcée à HOLD, indépendamment du score.

#### Niveau de confiance (formule v2)

> **Confiance** = 30 (base) + 50 × |score global| + 20 × accord_modules

L'accord vaut `1 - écart-type` des 4 scores normalisés. Plafonné à 25 % si la décision
est bloquée. Une confiance élevée (>80 %) signifie un signal fort *et* un accord
inter-modules — un cas idéal pour une décision avec engagement.
"""
)

st.divider()

st.markdown("### 🧭 Navigation")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info(
        "**📈 Marché**\n\nOHLC quotidien, candlestick, indicateurs techniques sur 8 paires.",
        icon="📈",
    )
with col2:
    st.info(
        "**💱 Simulateur**\n\nEntrez une opération → recommandation complète avec explication.",
        icon="💱",
    )
with col3:
    st.info(
        "**🤖 Décision IA**\n\nDécomposition pas-à-pas de la formule pondérée et de la confiance.",
        icon="🤖",
    )
with col4:
    st.info(
        "**🎚 Sensibilité**\n\nFaites varier chaque paramètre et observez la décision basculer.",
        icon="🎚",
    )

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.info(
        "**💬 Chat IA**\n\nPosez vos questions en français à l'assistant Gemini.",
        icon="💬",
    )
with col6:
    st.info(
        "**📊 Backtest**\n\nValidez le modèle sur 6-12 mois d'historique : PnL, Sharpe, % gagnants.",
        icon="📊",
    )
with col7:
    st.info(
        "**🌍 Risques par devise**\n\nVisualisez l'exposition de la banque par devise.",
        icon="🌍",
    )
with col8:
    st.info(
        "**📄 Rapport PDF**\n\nExport complet : graphiques, tableaux, conclusion.",
        icon="📄",
    )

st.markdown(" ")
st.success(
    "👈 Naviguez entre les pages via la barre latérale. Pour la démo jury : "
    "**Marché → Simulateur → Décision IA → Sensibilité → Chat IA → Backtest → Rapport**.",
    icon="👉",
)

render_footer()
