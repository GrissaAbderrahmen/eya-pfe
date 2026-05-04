"""Calcul du Bid / Ask / Spread pour chaque paire Forex.

yfinance ne publie pas de bid/ask fiables sur les paires FX (le champ `info`
est souvent vide ou aliassé sur le close). On simule donc un spread réaliste
à partir du **mid price** (= dernier Close yfinance) en s'appuyant sur des
fourchettes typiques observées en salle de marché :

- Paires majeures très liquides (EUR/USD, USD/JPY) : ~1 pip ≈ 0.01 % du prix
- Paires majeures liquides (GBP/USD, USD/CHF, EUR/GBP) : ~1.5–2 pips
- Paires TND (moins liquides, marché tunisien) : 15–25 pips

Convention prix :
    Bid  = prix auquel la banque est prête à *acheter* la devise de base
           = prix auquel le client *vend*   (« prix de vente » côté trader)
    Ask  = prix auquel la banque est prête à *vendre* la devise de base
           = prix auquel le client *achète* (« prix d'achat » côté trader)
    Mid  = (Bid + Ask) / 2 (cours médian, celui retourné par yfinance)
    Spread = Ask − Bid     (toujours ≥ 0)

Logique de trading :
    Décision BUY  → exécution au prix Ask  (le trader achète la base devise)
    Décision SELL → exécution au prix Bid  (le trader vend la base devise)
"""

from __future__ import annotations

# Spread typique en fraction du mid (ex: 0.0001 = 1 pip = 0.01 %).
# Source : observations sur EBS/Reuters + interbancaire BCT pour les paires TND.
TYPICAL_SPREAD_PCT = {
    "EUR/USD": 0.00010,   # 1 pip — la paire la plus liquide au monde
    "USD/JPY": 0.00010,   # 1 pip
    "GBP/USD": 0.00015,   # 1.5 pip
    "USD/CHF": 0.00020,   # 2 pip
    "EUR/GBP": 0.00020,   # 2 pip
    "USD/TND": 0.00150,   # ~15 pips — marché tunisien, moins de profondeur
    "EUR/TND": 0.00200,   # ~20 pips
    "GBP/TND": 0.00250,   # ~25 pips
}

# Bandes de qualité de liquidité, exprimées en multiple du spread typique.
# ratio = spread_observé / spread_typique
# Un ratio < 1 = marché plus liquide qu'à l'ordinaire (favorable).
_QUALITY_BANDS = [
    # (ratio_max, label, ajustement_score)
    (0.80, "Très liquide", +0.10),
    (1.20, "Liquide",       0.00),
    (1.80, "Élargi",       -0.15),
    (3.00, "Peu liquide",  -0.30),
]


def compute_bid_ask(pair: str, mid: float, spread_multiplier: float = 1.0) -> dict:
    """Calcule Bid / Ask / Spread autour d'un mid price.

    Args:
        pair: paire Forex (ex: "EUR/USD"). Détermine le spread typique.
        mid: prix médian (typiquement le dernier Close yfinance).
        spread_multiplier: facteur d'élargissement du spread (1.0 = conditions
            normales, 2.0 = marché stressé, 0.7 = très liquide). Permet à la
            page Simulateur de simuler des conditions dégradées.

    Returns:
        dict avec keys: bid, ask, mid, spread, spread_pct, typical_pct,
        spread_pips, ratio, quality, score_adjustment.
    """
    typical_pct = TYPICAL_SPREAD_PCT.get(pair, 0.00020)
    spread_pct = typical_pct * spread_multiplier
    half = mid * spread_pct / 2.0
    bid = mid - half
    ask = mid + half
    spread = ask - bid

    # Pip = 0.0001 pour la plupart des paires, 0.01 pour les paires JPY.
    pip_size = 0.01 if "JPY" in pair else 0.0001
    spread_pips = spread / pip_size

    ratio = spread_pct / typical_pct if typical_pct else 1.0
    quality, adjustment = "Peu liquide", -0.30
    for r_max, label, adj in _QUALITY_BANDS:
        if ratio <= r_max:
            quality, adjustment = label, adj
            break

    return {
        "pair": pair,
        "mid": round(mid, 6),
        "bid": round(bid, 6),
        "ask": round(ask, 6),
        "spread": round(spread, 6),
        "spread_pct": round(spread_pct, 6),
        "typical_pct": typical_pct,
        "spread_pips": round(spread_pips, 2),
        "ratio": round(ratio, 3),
        "quality": quality,
        "score_adjustment": adjustment,
    }


def execution_price(spread_info: dict, decision: str) -> float | None:
    """Retourne le prix d'exécution selon la décision.

    BUY  → Ask (le trader achète au prix vendeur de la banque)
    SELL → Bid (le trader vend au prix acheteur de la banque)
    HOLD → mid (référence, aucune exécution)
    """
    if not spread_info:
        return None
    if decision == "BUY":
        return spread_info.get("ask")
    if decision == "SELL":
        return spread_info.get("bid")
    return spread_info.get("mid")
