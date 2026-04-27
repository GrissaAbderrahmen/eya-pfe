"""
AI-Based Trading Room Decision Support System — Attijari Bank (PFE Eya).

Architecture en 7 modules (cf. cahier des charges) :
    1. DataCollectionModule        — Collecte des données yfinance (infrastructure)
    2. MarketDataModule            — Legacy / fallback simulation (compat)
    3. ForexAnalysisModule         — Analyse technique (poids 40%)
    4. TreasuryManagementModule    — Gestion de trésorerie (poids 25%)
    5. RiskManagementModule        — Évaluation du risque (poids 25%)
    6. ComplianceModule            — Conformité réglementaire BCT (poids 10%)
    7. AIDecisionEngine            — Moteur de décision pondéré (infrastructure)
    +  TraderInteractionModule     — Chat IA Gemini (cf. app/core/chat.py)

Formule du moteur de décision (cahier de charges) :
    Score global = Forex×0.4 + Trésorerie×0.25 + Risque×0.25 + Conformité×0.1
    Seuils       : > +0.5 → BUY   | < -0.5 → SELL   | sinon HOLD
    Bloqueurs    : Risque HIGH OU Conformité NON_COMPLIANT → HOLD forcé

Niveau de confiance (v2, 2026-04) :
    confidence = 30 + 50·|score global| + 20·accord_modules
    Cap à 25 si décision bloquée. Range 30-100 sinon.
"""

import random
from statistics import mean, pstdev, stdev

try:
    import requests
except ImportError:
    requests = None


# =========================================================
# 1) MARKET DATA MODULE
# =========================================================
class MarketDataModule:
    def __init__(self, pair="EUR/USD", use_api=True):
        self.pair = pair
        self.use_api = use_api
        self.price_history = []
        # Fallback ultime si yfinance et l'API échouent. Étendu aux 8 paires
        # supportées par le système (cf. yfinance_pairs.SIMULATED_BASE_PRICES).
        self.simulated_prices = {
            "EUR/USD": 1.09,
            "EUR/TND": 3.38,
            "USD/TND": 3.10,
            "GBP/USD": 1.27,
            "GBP/TND": 3.95,
            "USD/JPY": 154.0,
            "USD/CHF": 0.91,
            "EUR/GBP": 0.86,
        }

    def get_realtime_or_simulated_rate(self):
        if self.use_api:
            api_rate = self._get_rate_from_api()
            if api_rate is not None:
                self.price_history.append(api_rate)
                return api_rate, "API"

        simulated_rate = self._get_simulated_rate()
        self.price_history.append(simulated_rate)
        return simulated_rate, "SIMULATION"

    def _get_rate_from_api(self):
        if requests is None:
            return None
        try:
            base, quote = self.pair.split("/")
            url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={quote}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if "rates" in data and quote in data["rates"]:
                return float(data["rates"][quote])
            return None
        except Exception:
            return None

    def _get_simulated_rate(self):
        current_price = self.simulated_prices.get(self.pair, 1.00)
        movement = random.uniform(-0.005, 0.005)
        new_price = current_price * (1 + movement)
        self.simulated_prices[self.pair] = round(new_price, 4)
        return round(new_price, 4)


# =========================================================
# 2) FOREX ANALYSIS MODULE
# =========================================================
class ForexAnalysisModule:
    def calculate_moving_average(self, prices, period=5):
        if len(prices) < period:
            return mean(prices) if prices else 0
        return mean(prices[-period:])

    def calculate_volatility(self, prices, period=10):
        if len(prices) < 2:
            return 0
        sample = prices[-period:] if len(prices) >= period else prices
        if len(sample) < 2:
            return 0
        return round(stdev(sample), 6)

    def calculate_rsi(self, prices, period=14):
        if len(prices) < 2:
            return 50.0

        recent = prices[-(period + 1):] if len(prices) > period else prices
        gains, losses = [], []
        for i in range(1, len(recent)):
            change = recent[i] - recent[i - 1]
            if change > 0:
                gains.append(change)
            elif change < 0:
                losses.append(abs(change))

        avg_gain = mean(gains) if gains else 0.0
        avg_loss = mean(losses) if losses else 0.0

        if avg_gain == 0 and avg_loss == 0:
            return 50.0
        if avg_loss == 0:
            return 100.0
        if avg_gain == 0:
            return 0.0

        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    def calculate_macd(self, prices, short_period=5, long_period=12):
        if not prices:
            return 0
        short_ma = self.calculate_moving_average(prices, short_period)
        long_ma = self.calculate_moving_average(prices, long_period)
        return round(short_ma - long_ma, 6)

    def generate_signal(self, current_rate, prices):
        ma = self.calculate_moving_average(prices, period=5)
        vol = self.calculate_volatility(prices, period=10)
        rsi = self.calculate_rsi(prices, period=14)
        macd = self.calculate_macd(prices, short_period=5, long_period=12)

        score = 0
        # Règle 1 : prix vs moyenne mobile
        if current_rate > ma:
            score += 1
        elif current_rate < ma:
            score -= 1
        # Règle 2 : RSI (surachat / survente)
        if rsi < 30:
            score += 1
        elif rsi > 70:
            score -= 1
        # Règle 3 : MACD (momentum)
        if macd > 0:
            score += 1
        elif macd < 0:
            score -= 1
        # Règle 4 : pénalité volatilité
        if vol > 0.01:
            score = score - 1 if score > 0 else score + 1 if score < 0 else 0

        if score >= 2:
            signal = "BUY"
        elif score <= -2:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "current_rate": round(current_rate, 4),
            "moving_average": round(ma, 4),
            "volatility": vol,
            "rsi": rsi,
            "macd": macd,
            "signal": signal,
            "signal_score": score,
        }


# =========================================================
# 3) TREASURY MANAGEMENT MODULE
# =========================================================
class TreasuryManagementModule:
    def evaluate_treasury_position(self, cash_inflow, cash_outflow,
                                   liquidity_level, interbank_rate):
        net_cash = cash_inflow - cash_outflow

        if net_cash > 0 and liquidity_level >= 0.6:
            recommendation = "SURPLUS -> INVEST"
        elif net_cash < 0 or liquidity_level < 0.4:
            recommendation = "DEFICIT -> BORROW"
        else:
            recommendation = "BALANCED -> HOLD"

        return {
            "cash_inflow": cash_inflow,
            "cash_outflow": cash_outflow,
            "net_cash": net_cash,
            "liquidity_level": liquidity_level,
            "interbank_rate": interbank_rate,
            "treasury_recommendation": recommendation,
        }


# =========================================================
# 4) RISK MANAGEMENT MODULE
# =========================================================
class RiskManagementModule:
    def assess_risk(self, inflation, central_bank_rate, fx_volatility, exposure_level):
        risk_score = 0

        if inflation > 7:
            risk_score += 2
        elif inflation > 4:
            risk_score += 1

        if central_bank_rate > 7:
            risk_score += 2
        elif central_bank_rate > 4:
            risk_score += 1

        if fx_volatility > 0.02:
            risk_score += 2
        elif fx_volatility > 0.01:
            risk_score += 1

        if exposure_level > 0.7:
            risk_score += 2
        elif exposure_level > 0.4:
            risk_score += 1

        if risk_score <= 2:
            risk_level = "LOW"
        elif risk_score <= 5:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        return {
            "inflation": inflation,
            "central_bank_rate": central_bank_rate,
            "fx_volatility": fx_volatility,
            "exposure_level": exposure_level,
            "risk_score": risk_score,
            "risk_level": risk_level,
        }


# =========================================================
# 5) COMPLIANCE MODULE (NEW — aligné sur cahier de charges)
# =========================================================
class ComplianceModule:
    """Vérifie la conformité réglementaire (inspiration BCT).

    Trois règles :
        1. Liquidity Coverage Ratio (LCR) >= 100 %
        2. Position absolue par devise <= limite
        3. Exposition globale <= 80 %
    """

    def check_compliance(self, lcr, position_eur, position_usd,
                         position_limit, exposure_level):
        flags = []     # violations dures (font basculer le statut)
        warnings = []  # bandes proches du seuil — informatives, n'impactent pas le statut

        # --- LCR ---
        if lcr < 1.00:
            flags.append(
                f"LCR à {lcr * 100:.0f}% — sous le seuil réglementaire BCT de 100%"
            )
        elif lcr < 1.10:
            warnings.append(
                f"LCR à {lcr * 100:.0f}% — proche du seuil réglementaire (zone 100-110%)"
            )

        # --- Positions par devise ---
        if abs(position_eur) > position_limit:
            flags.append(
                f"Position EUR ({position_eur:,.0f}) dépasse la limite par devise "
                f"({position_limit:,.0f})"
            )
        if abs(position_usd) > position_limit:
            flags.append(
                f"Position USD ({position_usd:,.0f}) dépasse la limite par devise "
                f"({position_limit:,.0f})"
            )

        # --- Exposition globale ---
        if exposure_level > 0.80:
            flags.append(
                f"Exposition globale à {exposure_level * 100:.0f}% — au-dessus du "
                f"plafond BCT de 80%"
            )
        elif exposure_level > 0.70:
            warnings.append(
                f"Exposition globale à {exposure_level * 100:.0f}% — proche du plafond "
                f"(zone 70-80%)"
            )

        if not flags:
            status, score = "COMPLIANT", 1.0
        elif len(flags) == 1:
            status, score = "WARNING", 0.3
        else:
            status, score = "NON_COMPLIANT", -1.0

        return {
            "status": status,
            "flags": flags,
            "warnings": warnings,
            "compliance_score": score,
            "lcr": lcr,
            "position_eur": position_eur,
            "position_usd": position_usd,
            "position_limit": position_limit,
            "exposure_level": exposure_level,
        }


# =========================================================
# 6) AI DECISION ENGINE (refactor — formule pondérée du cahier de charges)
# =========================================================
class AIDecisionEngine:
    WEIGHTS = {"forex": 0.4, "treasury": 0.25, "risk": 0.25, "compliance": 0.1}
    BUY_THRESHOLD = 0.5
    SELL_THRESHOLD = -0.5

    def _normalize_forex(self, forex_result):
        # signal_score ∈ ~[-4, +4] → mappé sur [-1, +1]
        score = forex_result.get("signal_score", 0)
        return max(-1.0, min(1.0, score / 4.0))

    def _normalize_treasury(self, treasury_result):
        # Normalisation continue (2026-04 v2) : combine net_cash et liquidité.
        # Évite que BALANCED produise systématiquement 0.00 (barre invisible).
        # Rétro-compat : si net_cash absent, fallback sur le step function de la
        # recommandation textuelle (pour les anciens tests qui forgent un dict
        # minimal).
        net = treasury_result.get("net_cash")
        if net is None:
            rec = treasury_result.get("treasury_recommendation", "")
            if "SURPLUS" in rec:
                return 1.0
            if "DEFICIT" in rec:
                return -1.0
            return 0.0
        liquidity = treasury_result.get("liquidity_level", 0.5)
        cash_factor = max(-1.0, min(1.0, net / 1_000_000))      # ±1M TND → ±1.0
        liquidity_factor = max(-1.0, min(1.0, (liquidity - 0.5) * 2))
        return round((cash_factor + liquidity_factor) / 2, 4)

    def _normalize_risk(self, risk_result):
        # Normalisation continue (2026-04 v2) : utilise risk_score brut (0-8)
        # mappé linéairement sur [+1, -1]. Évite que MEDIUM produise pile 0.0
        # (la moitié des scénarios pré-chargés tombaient dans cette bande →
        # barre invisible dans le graphique normalized_scores_bar).
        # Rétro-compat : si risk_score absent, fallback sur le step function
        # 3 niveaux (LOW/MEDIUM/HIGH).
        raw = risk_result.get("risk_score")
        if raw is None:
            level = risk_result.get("risk_level", "MEDIUM")
            return {"LOW": 1.0, "MEDIUM": 0.0, "HIGH": -1.0}.get(level, 0.0)
        return round(max(-1.0, min(1.0, 1.0 - 2.0 * raw / 8.0)), 4)

    def _normalize_compliance(self, compliance_result):
        if compliance_result is None:
            return 1.0
        return compliance_result.get("compliance_score", 0.0)

    def combine_decisions(self, forex_result, treasury_result, risk_result,
                          compliance_result=None):
        """Combine les sorties des 4 modules en une décision finale.

        compliance_result est optionnel (None → traité comme COMPLIANT)
        pour rester rétro-compatible avec les anciens tests.
        """
        n_forex = self._normalize_forex(forex_result)
        n_treasury = self._normalize_treasury(treasury_result)
        n_risk = self._normalize_risk(risk_result)
        n_compliance = self._normalize_compliance(compliance_result)

        global_score = (
            self.WEIGHTS["forex"] * n_forex
            + self.WEIGHTS["treasury"] * n_treasury
            + self.WEIGHTS["risk"] * n_risk
            + self.WEIGHTS["compliance"] * n_compliance
        )

        if global_score > self.BUY_THRESHOLD:
            soft_decision = "BUY"
        elif global_score < self.SELL_THRESHOLD:
            soft_decision = "SELL"
        else:
            soft_decision = "HOLD"

        blocking_reasons = []
        if risk_result.get("risk_level") == "HIGH":
            blocking_reasons.append("Risque global élevé (HIGH)")
        if compliance_result is not None and compliance_result.get("status") == "NON_COMPLIANT":
            blocking_reasons.append("Non-conformité réglementaire")

        decision_blocked = bool(blocking_reasons)
        final_decision = "HOLD" if decision_blocked else soft_decision

        # Confiance v2 (2026-04) — formule à 3 facteurs :
        #   - magnitude   : |score global| ∈ [0, 1]   (50 pts max)
        #   - agreement   : 1 - écart-type des scores normalisés (20 pts max)
        #   - base        : 30 pts incompressibles (un score est toujours informatif)
        # Cap à 25 si la décision est bloquée par risque ou non-conformité.
        ns_values = list({"forex": n_forex, "treasury": n_treasury,
                          "risk": n_risk, "compliance": n_compliance}.values())
        magnitude = min(1.0, abs(global_score))
        agreement = max(0.0, 1.0 - pstdev(ns_values))  # std max ≈ 1 si scores opposés
        confidence = 30.0 + 50.0 * magnitude + 20.0 * agreement
        if decision_blocked:
            confidence = min(confidence, 25.0)
        confidence = max(0.0, min(100.0, round(confidence, 1)))
        confidence_breakdown = {
            "base": 30.0,
            "magnitude_pts": round(50.0 * magnitude, 1),
            "agreement_pts": round(20.0 * agreement, 1),
            "magnitude_factor": round(magnitude, 3),
            "agreement_factor": round(agreement, 3),
        }

        return {
            "final_decision": final_decision,
            "soft_decision": soft_decision,
            "global_score": round(global_score, 4),
            "confidence_score": confidence,
            "confidence_breakdown": confidence_breakdown,
            "decision_blocked": decision_blocked,
            "blocking_reasons": blocking_reasons,
            "normalized_scores": {
                "forex": round(n_forex, 4),
                "treasury": round(n_treasury, 4),
                "risk": round(n_risk, 4),
                "compliance": round(n_compliance, 4),
            },
            "weights": dict(self.WEIGHTS),
            "thresholds": {"buy": self.BUY_THRESHOLD, "sell": self.SELL_THRESHOLD},
            # Rétro-compatibilité avec l'ancienne API
            "risk_level": risk_result.get("risk_level"),
            "treasury_recommendation": treasury_result.get("treasury_recommendation"),
        }


# =========================================================
# 7) MODULES D'INFRASTRUCTURE — packaging académique 7 modules
# =========================================================
class DataCollectionModule:
    """Module 1 — Collecte des données. Wrap yfinance + cache.

    Module d'infrastructure (poids 0% dans le score). Sa qualité conditionne
    cependant la fiabilité de tous les autres modules : sans historique, le
    Forex et le Risque retournent leur valeur neutre.
    """

    def __init__(self):
        # Import paresseux pour éviter une dépendance dure à yfinance dans les tests
        from .market_data import fetch_history_ohlc, fetch_latest_rate
        self._fetch_history = fetch_history_ohlc
        self._fetch_latest = fetch_latest_rate

    def fetch_history(self, pair: str, period: str = "3mo"):
        return self._fetch_history(pair, period)

    def fetch_latest_rate(self, pair: str):
        return self._fetch_latest(pair)

    @staticmethod
    def assess_data_quality(history_length: int) -> dict:
        """Score de qualité [0, 1] basé sur la longueur de l'historique disponible."""
        ratio = min(1.0, history_length / 30.0)
        if ratio >= 1.0:
            label = "HIGH"
        elif ratio >= 0.5:
            label = "MEDIUM"
        else:
            label = "LOW"
        return {"history_length": history_length, "quality_ratio": round(ratio, 3),
                "quality_label": label}


# Alias sémantique pour la documentation académique :
# le moteur de décision est aussi appelé "Moteur de décision intelligent"
# dans le tableau des 7 modules de la page d'accueil.
IntelligentDecisionEngine = AIDecisionEngine


class TraderInteractionModule:
    """Module 7 — Interaction trader (chat IA Gemini).

    Le wrapping concret de Gemini est dans `app/core/chat.py` ; cette classe
    sert juste de point d'entrée nommé pour la présentation académique des
    7 modules. Module d'infrastructure (poids 0% dans le score).
    """

    def __init__(self):
        from .chat import ChatService
        self._chat = ChatService()

    def ask(self, question: str, simulation_context: dict | None = None) -> str:
        return self._chat.ask(question, simulation_context)

    def is_available(self) -> bool:
        from .chat import ChatService
        return ChatService.is_available()


# =========================================================
# 8) TESTS (étendus)
# =========================================================
def run_simple_tests():
    forex = ForexAnalysisModule()
    treasury = TreasuryManagementModule()
    risk = RiskManagementModule()
    compliance = ComplianceModule()
    engine = AIDecisionEngine()

    # --- RSI edge cases ---
    assert forex.calculate_rsi([1.0]) == 50.0
    assert forex.calculate_rsi([1.0, 1.0, 1.0, 1.0]) == 50.0
    assert forex.calculate_rsi([1.0, 1.1, 1.2, 1.3]) == 100.0
    assert forex.calculate_rsi([1.3, 1.2, 1.1, 1.0]) == 0.0

    # --- MA & volatility ---
    assert round(forex.calculate_moving_average([1, 2, 3, 4, 5], 5), 2) == 3.00
    assert forex.calculate_volatility([1.0]) == 0

    # --- Treasury ---
    assert treasury.evaluate_treasury_position(120, 100, 0.8, 6.0)["treasury_recommendation"] == "SURPLUS -> INVEST"
    assert treasury.evaluate_treasury_position(100, 140, 0.8, 6.0)["treasury_recommendation"] == "DEFICIT -> BORROW"
    assert treasury.evaluate_treasury_position(100, 100, 0.5, 6.0)["treasury_recommendation"] == "BALANCED -> HOLD"

    # --- Risk ---
    assert risk.assess_risk(2.0, 2.0, 0.005, 0.2)["risk_level"] == "LOW"
    assert risk.assess_risk(6.0, 5.0, 0.015, 0.5)["risk_level"] == "MEDIUM"
    assert risk.assess_risk(8.0, 8.0, 0.03, 0.8)["risk_level"] == "HIGH"

    # --- Compliance (NEW) ---
    c_ok = compliance.check_compliance(
        lcr=1.2, position_eur=500_000, position_usd=400_000,
        position_limit=1_000_000, exposure_level=0.5,
    )
    assert c_ok["status"] == "COMPLIANT"
    assert c_ok["compliance_score"] == 1.0
    assert c_ok["flags"] == []

    c_warn = compliance.check_compliance(
        lcr=0.9, position_eur=500_000, position_usd=400_000,
        position_limit=1_000_000, exposure_level=0.5,
    )
    assert c_warn["status"] == "WARNING"
    assert c_warn["compliance_score"] == 0.3
    assert len(c_warn["flags"]) == 1

    c_ko = compliance.check_compliance(
        lcr=0.7, position_eur=1_500_000, position_usd=400_000,
        position_limit=1_000_000, exposure_level=0.85,
    )
    assert c_ko["status"] == "NON_COMPLIANT"
    assert c_ko["compliance_score"] == -1.0
    assert len(c_ko["flags"]) >= 2

    # --- AI engine — rétro-compat (sans conformité) ---
    legacy = engine.combine_decisions(
        {"signal": "BUY", "signal_score": 2},
        {"treasury_recommendation": "SURPLUS -> INVEST"},
        {"risk_level": "HIGH"},
    )
    assert legacy["final_decision"] == "HOLD"  # risque HIGH force HOLD
    assert legacy["decision_blocked"] is True

    # --- AI engine — formule pondérée : BUY ---
    buy_case = engine.combine_decisions(
        {"signal": "BUY", "signal_score": 4},
        {"treasury_recommendation": "SURPLUS -> INVEST"},
        {"risk_level": "LOW"},
        {"status": "COMPLIANT", "compliance_score": 1.0},
    )
    assert buy_case["final_decision"] == "BUY"
    assert buy_case["global_score"] == 1.0
    assert buy_case["decision_blocked"] is False

    # --- AI engine — formule pondérée : SELL ---
    sell_case = engine.combine_decisions(
        {"signal": "SELL", "signal_score": -4},
        {"treasury_recommendation": "DEFICIT -> BORROW"},
        {"risk_level": "MEDIUM"},
        {"status": "WARNING", "compliance_score": 0.3},
    )
    # 0.4*-1 + 0.25*-1 + 0.25*0 + 0.1*0.3 = -0.62
    assert sell_case["final_decision"] == "SELL"
    assert sell_case["global_score"] < -0.5

    # --- AI engine — blocage par non-conformité ---
    blocked_case = engine.combine_decisions(
        {"signal": "BUY", "signal_score": 4},
        {"treasury_recommendation": "SURPLUS -> INVEST"},
        {"risk_level": "LOW"},
        {"status": "NON_COMPLIANT", "compliance_score": -1.0},
    )
    assert blocked_case["final_decision"] == "HOLD"
    assert blocked_case["decision_blocked"] is True
    assert "Non-conformité réglementaire" in blocked_case["blocking_reasons"]

    print("All engine tests passed ({} assertions).".format(
        "RSI+MA+TRESO+RISK+COMPLIANCE+DECISION"
    ))


if __name__ == "__main__":
    run_simple_tests()
