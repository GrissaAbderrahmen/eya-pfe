"""Génération d'explications en langage simple pour la décision finale.

Templated (pas de LLM) — gratuit, déterministe, jury-friendly. La même décision
produit toujours la même explication, ce qui aide à défendre les choix devant
le jury : on peut montrer la phrase, puis pointer la règle qui l'a produite.
"""

from __future__ import annotations


_VERB = {"BUY": "ACHETER", "SELL": "VENDRE", "HOLD": "ATTENDRE"}
_DOMINANT_FR = {
    "forex": "l'analyse technique Forex",
    "treasury": "la position de trésorerie",
    "risk": "l'évaluation du risque",
    "compliance": "le contrôle de conformité",
}


def _forex_clause(forex: dict) -> str:
    rsi = forex.get("rsi", 50.0)
    macd = forex.get("macd", 0.0)
    signal = forex.get("signal", "HOLD")
    if rsi < 30:
        return f"le RSI à {rsi:.0f} indique une zone de survente (signal {signal})"
    if rsi > 70:
        return f"le RSI à {rsi:.0f} indique un surachat (signal {signal})"
    if macd > 0:
        return f"le MACD positif ({macd:+.4f}) confirme un momentum haussier"
    if macd < 0:
        return f"le MACD négatif ({macd:+.4f}) confirme un momentum baissier"
    return f"les indicateurs techniques sont neutres (RSI {rsi:.0f}, MACD {macd:+.4f})"


def _treasury_clause(treasury: dict) -> str:
    rec = treasury.get("treasury_recommendation", "BALANCED")
    net = treasury.get("net_cash", 0)
    if "SURPLUS" in rec:
        return f"la trésorerie est en surplus ({net:+,.0f} TND) — capacité d'investissement"
    if "DEFICIT" in rec:
        return f"la trésorerie est en déficit ({net:+,.0f} TND) — besoin de financement"
    return f"la trésorerie est équilibrée ({net:+,.0f} TND)"


def _risk_clause(risk: dict) -> str:
    level = risk.get("risk_level", "MEDIUM")
    score = risk.get("risk_score", 0)
    if level == "HIGH":
        return f"le niveau de risque est élevé (score {score}/8) — décision bloquée"
    if level == "LOW":
        return f"le risque global est faible (score {score}/8)"
    return f"le risque est modéré (score {score}/8)"


def _compliance_clause(compliance: dict) -> str:
    status = compliance.get("status", "COMPLIANT")
    lcr = compliance.get("lcr", 1.0)
    if status == "COMPLIANT":
        return f"tous les contrôles BCT sont satisfaits (LCR {lcr * 100:.0f}%)"
    if status == "WARNING":
        return f"un seuil réglementaire est en zone d'alerte (LCR {lcr * 100:.0f}%)"
    return f"plusieurs violations réglementaires détectées (LCR {lcr * 100:.0f}%)"


def explain_decision(decision: dict, forex: dict, treasury: dict,
                     risk: dict, compliance: dict) -> str:
    """Retourne 2-3 phrases françaises expliquant la décision finale.

    Identifie le module le plus influent (par |score normalisé|) et construit
    une justification orientée jury : décision + facteur dominant + facteur
    secondaire + niveau de confiance.
    """
    final = decision.get("final_decision", "HOLD")
    action = _VERB.get(final, "ATTENDRE")
    confidence = decision.get("confidence_score", 50.0)
    blocked = decision.get("decision_blocked", False)
    blocking = decision.get("blocking_reasons", [])

    if blocked:
        reasons = " et ".join(blocking).lower()
        return (
            f"La décision est forcée à **{action}** parce que {reasons}. "
            f"{_compliance_clause(compliance).capitalize()}. "
            f"Niveau de confiance : {confidence:.0f}%."
        )

    ns = decision.get("normalized_scores", {})
    if not ns:
        return f"Décision : **{action}** avec {confidence:.0f}% de confiance."

    sorted_modules = sorted(ns.items(), key=lambda kv: abs(kv[1]), reverse=True)
    dominant_key = sorted_modules[0][0]
    secondary_key = sorted_modules[1][0] if len(sorted_modules) > 1 else None

    clauses = {
        "forex": _forex_clause(forex),
        "treasury": _treasury_clause(treasury),
        "risk": _risk_clause(risk),
        "compliance": _compliance_clause(compliance),
    }

    parts = [
        f"Le modèle recommande **{action}** : {clauses[dominant_key]}.",
    ]
    if secondary_key and abs(ns[secondary_key]) > 0.1:
        parts.append(f"Cette recommandation est confortée par {clauses[secondary_key]}.")
    parts.append(f"Niveau de confiance : **{confidence:.0f}%**.")

    return " ".join(parts)
