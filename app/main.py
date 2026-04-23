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

render_header(
    title="Système d'aide à la décision — Salle de marché",
    subtitle="PFE Licence en Gestion · Cas Attijari Bank Tunisie · Modèle académique",
)

st.markdown(
    """
### Bienvenue dans le prototype de démonstration

Cet outil illustre le fonctionnement d'un **système d'aide à la décision** destiné aux traders
d'une salle de marché bancaire. Il combine quatre dimensions financières pour recommander
une action (achat / vente / attente) sur une opération de change, avec un **niveau de confiance**
et des **contrôles de conformité réglementaire**.

#### Les 4 modules du modèle

| Module | Rôle | Poids dans le score global |
|---|---|:---:|
| 📈 **Forex** | Analyse technique (MA, RSI, MACD, volatilité) | **40 %** |
| 🏦 **Trésorerie** | Position de liquidité, flux net, taux interbancaire | **25 %** |
| ⚠️ **Risque** | Inflation, taux directeur, volatilité, exposition | **25 %** |
| 📋 **Conformité** | LCR ≥ 100 %, limites de position, exposition ≤ 80 % | **10 %** |

#### Formule de décision

> **Score global** = (Forex × 0.4) + (Trésorerie × 0.25) + (Risque × 0.25) + (Conformité × 0.1)

- Si **Score > +0.5** → recommandation **ACHAT (BUY)**
- Si **Score < −0.5** → recommandation **VENTE (SELL)**
- Sinon → **ATTENTE (HOLD)**

**Bloqueurs durs** : en cas de risque élevé (HIGH) ou de non-conformité (NON_COMPLIANT),
la décision est automatiquement forcée à HOLD, indépendamment du score.
"""
)

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.info(
        "**📈 Marché en temps réel**\n\nTaux EUR/USD et USD/TND · Moyenne mobile, RSI, MACD, volatilité.",
        icon="📈",
    )
with col2:
    st.info(
        "**💱 Simulateur trader**\n\nEntrez une opération → obtenez une recommandation complète.",
        icon="💱",
    )
with col3:
    st.info(
        "**🤖 Décision IA**\n\nVoyez étape par étape comment la formule pondérée aboutit à la décision.",
        icon="🤖",
    )

st.markdown(" ")
col4, col5 = st.columns(2)
with col4:
    st.info(
        "**🎚 Analyse de sensibilité**\n\nVariez chaque input de ±10 % et observez comment la décision évolue.",
        icon="🎚",
    )
with col5:
    st.info(
        "**📄 Rapport PDF**\n\nExportez les résultats de la dernière simulation pour annexer au PFE.",
        icon="📄",
    )

st.markdown(" ")
st.success(
    "👈 Naviguez entre les pages via la barre latérale. Commencez par **Simulateur** pour la démo jury.",
    icon="👉",
)

render_footer()
