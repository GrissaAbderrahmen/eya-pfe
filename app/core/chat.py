"""Service de chat IA basé sur Google Gemini (free tier).

Utilise google-generativeai. La clé est lue depuis :
1. la variable d'environnement GEMINI_API_KEY ;
2. st.secrets["GEMINI_API_KEY"] (utile pour Streamlit Cloud).

Si aucune clé n'est disponible OU si l'appel API échoue, un mode de fallback
templated répond à partir du contexte de la simulation. La démo jury reste
ainsi fonctionnelle même hors-ligne — c'est un argument à mettre en avant
côté soutenance (« robustesse aux défaillances externes »).
"""

from __future__ import annotations

import os
from typing import Any

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False


_SYSTEM_PROMPT = """Tu es l'assistant trading interne d'Attijari Bank Tunisie. Tu aides la
salle de marché à interpréter les recommandations du système d'aide à la décision.

Règles strictes :
- Réponds toujours en français professionnel.
- Cite les chiffres exacts du contexte de simulation fourni (RSI, LCR, exposition, score, etc.).
- Maximum 200 mots par réponse.
- Si la question dépasse les données fournies, dis-le clairement, ne devine pas.
- Reste neutre et factuel : tu n'es pas un conseiller en investissement, tu interprètes le modèle.
- Mentionne les contraintes BCT si elles sont en jeu (LCR, position, exposition).
"""


def _get_api_key() -> str | None:
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    if _HAS_STREAMLIT:
        try:
            return st.secrets.get("GEMINI_API_KEY", None)
        except Exception:
            return None
    return None


def _format_simulation_context(sim: dict[str, Any] | None) -> str:
    if not sim:
        return "(Aucune simulation en cours — l'utilisateur n'a pas encore lancé d'analyse.)"
    op = sim.get("operation", {})
    forex = sim.get("forex", {})
    treasury = sim.get("treasury", {})
    risk = sim.get("risk", {})
    compliance = sim.get("compliance", {})
    decision = sim.get("decision", {})
    return f"""
Opération en cours :
  - Sens : {op.get('direction', '?')}
  - Montant : {op.get('amount', 0):,.0f}
  - Paire : {op.get('pair', '?')}
  - Horizon : {op.get('horizon', '?')}

Module Forex :
  - Signal : {forex.get('signal', '?')} (score brut {forex.get('signal_score', 0):+d}/4)
  - Taux courant : {forex.get('current_rate', 0):.4f}
  - RSI : {forex.get('rsi', 50):.1f}
  - MACD : {forex.get('macd', 0):+.4f}
  - Volatilité : {forex.get('volatility', 0):.6f}

Module Trésorerie :
  - Recommandation : {treasury.get('treasury_recommendation', '?')}
  - Net cash : {treasury.get('net_cash', 0):+,.0f} TND
  - Niveau de liquidité : {treasury.get('liquidity_level', 0):.0%}

Module Risque :
  - Niveau : {risk.get('risk_level', '?')}
  - Score brut : {risk.get('risk_score', 0)}/8
  - Inflation : {risk.get('inflation', 0):.1f}%
  - Taux directeur BCT : {risk.get('central_bank_rate', 0):.2f}%
  - Exposition : {risk.get('exposure_level', 0):.0%}

Module Conformité BCT :
  - Statut : {compliance.get('status', '?')}
  - LCR : {compliance.get('lcr', 0) * 100:.0f}%
  - Flags : {len(compliance.get('flags', []))} ({'; '.join(compliance.get('flags', [])) or 'aucun'})
  - Warnings : {len(compliance.get('warnings', []))} ({'; '.join(compliance.get('warnings', [])) or 'aucun'})

Décision finale :
  - Action : {decision.get('final_decision', '?')}
  - Score global : {decision.get('global_score', 0):+.3f}
  - Confiance : {decision.get('confidence_score', 0):.0f}%
  - Bloquée : {'oui' if decision.get('decision_blocked', False) else 'non'}
  - Raisons de blocage : {'; '.join(decision.get('blocking_reasons', [])) or 'aucune'}
""".strip()


def _fallback_response(question: str, sim: dict[str, Any] | None,
                       suppress_key_hint: bool = False) -> str:
    """Réponse templated quand Gemini est indisponible — basée sur le contexte simu.

    suppress_key_hint : True quand la clé EST configurée mais l'API a échoué
    (évite le message trompeur « clé non configurée »).
    """
    if not sim:
        return (
            "Aucune simulation n'est encore chargée. Merci de lancer d'abord une analyse "
            "depuis la page **Simulateur**, puis de revenir poser votre question."
        )
    decision = sim.get("decision", {})
    forex = sim.get("forex", {})
    op = sim.get("operation", {})
    final = decision.get("final_decision", "HOLD")
    confidence = decision.get("confidence_score", 50)
    score = decision.get("global_score", 0)
    body = (
        f"Le modèle recommande **{final}** sur cette opération de "
        f"{op.get('direction', '').lower()} de {op.get('amount', 0):,.0f} en "
        f"{op.get('pair', '?')}, avec un score global de **{score:+.3f}** et une confiance "
        f"de **{confidence:.0f}%**. "
        f"Le signal Forex est **{forex.get('signal', '?')}** (RSI à {forex.get('rsi', 50):.0f})."
    )
    if not suppress_key_hint:
        body += (
            f"\n\n*(Mode de secours — la clé Gemini n'est pas configurée. "
            f"Définissez `GEMINI_API_KEY` dans `.streamlit/secrets.toml` ou `.env` "
            f"pour des réponses contextuelles complètes.)*"
        )
    return body


class ChatService:
    """Wrapper autour de Gemini avec retombée templated.

    Usage :
        svc = ChatService()
        response = svc.ask("Que penses-tu de cette opération ?", simulation_dict)
    """

    # gemini-1.5-flash : modèle le plus largement disponible géographiquement
    # (gemini-2.0-flash peut être restreint dans certaines régions). Free tier
    # généreux : 15 RPM, 1500 RPD.
    MODEL_NAME = "gemini-1.5-flash"

    def __init__(self):
        self._client = None
        if genai is None:
            return
        key = _get_api_key()
        if not key:
            return
        try:
            self._client = genai.Client(api_key=key)
        except Exception:
            self._client = None

    @classmethod
    def is_available(cls) -> bool:
        return genai is not None and _get_api_key() is not None

    def ask(self, question: str, simulation_context: dict | None = None) -> str:
        if self._client is None:
            return _fallback_response(question, simulation_context)
        try:
            full_prompt = (
                f"Contexte de la simulation :\n{_format_simulation_context(simulation_context)}\n\n"
                f"Question du trader : {question}"
            )
            response = self._client.models.generate_content(
                model=self.MODEL_NAME,
                contents=full_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_output_tokens=400,
                ),
            )
            text = (response.text or "").strip()
            return text or _fallback_response(question, simulation_context)
        except Exception as exc:
            # Surface l'erreur réelle (et pas juste le type) pour faciliter le debug.
            # Les ClientError de Gemini contiennent souvent un message JSON utile
            # (model not found, quota exceeded, permission denied, etc.).
            err_msg = str(exc).strip() or type(exc).__name__
            # Tronquer pour éviter d'exploser l'UI
            if len(err_msg) > 400:
                err_msg = err_msg[:400] + "…"
            return (
                f"⚠️ **Appel Gemini échoué** ({type(exc).__name__})\n\n"
                f"Détail technique : `{err_msg}`\n\n"
                f"---\n\n"
                f"**Réponse de secours basée sur la simulation :**\n\n"
                f"{_fallback_response(question, simulation_context, suppress_key_hint=True)}"
            )
