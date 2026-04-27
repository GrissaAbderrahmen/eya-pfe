"""Page Chat IA — assistant Gemini contextualisé sur la simulation en cours."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

from app.core.chat import ChatService
from components.branding import (
    inject_global_css,
    render_attijari_logo,
    render_footer,
    render_header,
)

st.set_page_config(page_title="Chat IA", page_icon="💬", layout="wide")
inject_global_css()
render_attijari_logo()

render_header(
    title="💬 Chat IA — Assistant trader",
    subtitle="Posez vos questions en français. L'assistant s'appuie sur Google Gemini "
    "et le contexte de votre dernière simulation.",
)

# ---- État ----
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
sim = st.session_state.get("last_simulation")
service = ChatService()

# ---- Bandeau d'état ----
col_a, col_b = st.columns([3, 1])
with col_a:
    if not sim:
        st.warning(
            "Aucune simulation en mémoire. L'assistant peut répondre à des questions "
            "générales, mais les réponses contextuelles nécessitent que vous lanciez "
            "d'abord une analyse depuis la page **Simulateur**.",
            icon="👈",
        )
    else:
        op = sim["operation"]
        decision = sim["decision"]
        st.info(
            f"**Contexte chargé :** {op['direction']} de {op['amount']:,.0f} en {op['pair']} → "
            f"décision **{decision['final_decision']}** (score {decision['global_score']:+.3f}, "
            f"confiance {decision['confidence_score']:.0f}%).",
            icon="📎",
        )
with col_b:
    if ChatService.is_available():
        st.success("✅ Gemini connecté")
    else:
        st.warning("⚙️ Mode secours")
        st.caption("Définissez `GEMINI_API_KEY` dans `.env` pour activer Gemini.")

# ---- Suggestions de questions ----
with st.expander("💡 Exemples de questions à poser à l'assistant"):
    st.markdown(
        """
- *Que penses-tu de cette opération ?*
- *Quels sont les risques principaux que je dois surveiller ?*
- *Pourquoi la décision est-elle bloquée ?*
- *Que se passerait-il si l'inflation montait à 9 % ?*
- *Le LCR est-il suffisant pour cette opération ?*
- *Explique-moi la décision en deux phrases pour un commercial.*
- *Quelle est la principale raison du score global actuel ?*
"""
    )

# ---- Historique de conversation ----
st.divider()
for entry in st.session_state.chat_history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])

# ---- Saisie ----
question = st.chat_input("Posez votre question…")
if question:
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Gemini réfléchit…"):
            answer = service.ask(question, sim)
        st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

# ---- Bouton effacer historique ----
if st.session_state.chat_history:
    st.divider()
    if st.button("🗑️ Effacer la conversation", type="secondary"):
        st.session_state.chat_history = []
        st.rerun()

render_footer()
