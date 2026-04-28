"""Tests pytest du moteur. Délégue la majorité à run_simple_tests() côté engine."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.engine import (
    AIDecisionEngine,
    ComplianceModule,
    ForexAnalysisModule,
    RiskManagementModule,
    TreasuryManagementModule,
    run_simple_tests,
)


def test_engine_suite():
    run_simple_tests()


def test_compliance_compliant():
    c = ComplianceModule()
    r = c.check_compliance(lcr=1.2, position_eur=500_000, position_usd=400_000,
                           position_limit=1_000_000, exposure_level=0.5)
    assert r["status"] == "COMPLIANT"
    assert r["flags"] == []


def test_compliance_warning():
    c = ComplianceModule()
    r = c.check_compliance(lcr=0.9, position_eur=500_000, position_usd=400_000,
                           position_limit=1_000_000, exposure_level=0.5)
    assert r["status"] == "WARNING"
    assert len(r["flags"]) == 1


def test_compliance_non_compliant():
    c = ComplianceModule()
    r = c.check_compliance(lcr=0.7, position_eur=1_500_000, position_usd=400_000,
                           position_limit=1_000_000, exposure_level=0.85)
    assert r["status"] == "NON_COMPLIANT"
    assert len(r["flags"]) >= 2


def test_weighted_decision_buy():
    e = AIDecisionEngine()
    r = e.combine_decisions(
        {"signal_score": 4},
        {"treasury_recommendation": "SURPLUS -> INVEST"},
        {"risk_level": "LOW"},
        {"status": "COMPLIANT", "compliance_score": 1.0},
    )
    assert r["final_decision"] == "BUY"
    assert r["global_score"] == 1.0


def test_weighted_decision_sell():
    e = AIDecisionEngine()
    r = e.combine_decisions(
        {"signal_score": -4},
        {"treasury_recommendation": "DEFICIT -> BORROW"},
        {"risk_level": "MEDIUM"},
        {"status": "WARNING", "compliance_score": 0.3},
    )
    assert r["final_decision"] == "SELL"
    assert r["global_score"] < -0.5


def test_normalize_risk_continuous():
    """Risk_score brut (0-8) → continu sur [+1, -1] avec point neutre à score=3."""
    e = AIDecisionEngine()
    # Formule v3 (2026-04) : 1.0 - raw / 3.0, clampé
    # risk_score=0 → +1.0 (pas de risque)
    assert e._normalize_risk({"risk_score": 0, "risk_level": "LOW"}) == 1.0
    # risk_score=3 → 0.0 (point neutre)
    assert e._normalize_risk({"risk_score": 3, "risk_level": "MEDIUM"}) == 0.0
    # risk_score=4 (cas hyper commun) → -0.33 (visible, plus dans la bande morte !)
    assert e._normalize_risk({"risk_score": 4, "risk_level": "MEDIUM"}) == -0.3333
    # risk_score=6 → -1.0 (clampé, équivaut à HIGH)
    assert e._normalize_risk({"risk_score": 6, "risk_level": "HIGH"}) == -1.0
    # risk_score=8 → -1.0 (clampé)
    assert e._normalize_risk({"risk_score": 8, "risk_level": "HIGH"}) == -1.0
    # Rétro-compat : sans risk_score, fallback sur level (MEDIUM = -0.2 v3)
    assert e._normalize_risk({"risk_level": "LOW"}) == 1.0
    assert e._normalize_risk({"risk_level": "MEDIUM"}) == -0.2
    assert e._normalize_risk({"risk_level": "HIGH"}) == -1.0


def test_normalize_treasury_continuous():
    """net_cash + liquidité combinés par addition saturée si même sens."""
    e = AIDecisionEngine()
    # Cash positif + liquidité positive → addition saturée (signal fort)
    v = e._normalize_treasury({"net_cash": 600_000, "liquidity_level": 0.7,
                               "treasury_recommendation": "SURPLUS -> INVEST"})
    # 0.6 + 0.4 = 1.0 (clampé)
    assert v == 1.0, f"Addition saturée attendue, eu {v}"
    # Cash neutre + liquidité neutre → 0 exactement
    v_neutral = e._normalize_treasury({"net_cash": 0, "liquidity_level": 0.5,
                                       "treasury_recommendation": "BALANCED -> HOLD"})
    assert v_neutral == 0.0
    # Cash positif + liquidité négative (conflit) → moyenne
    v_conflict = e._normalize_treasury({"net_cash": 500_000, "liquidity_level": 0.3,
                                        "treasury_recommendation": "BALANCED -> HOLD"})
    # cash_factor=0.5, liquidity_factor=-0.4 → conflit → moyenne = 0.05
    assert abs(v_conflict - 0.05) < 0.01, f"Moyenne en conflit attendue, eu {v_conflict}"
    # Cash très positif + bonne liquidité → +1 (clampé)
    v_max = e._normalize_treasury({"net_cash": 2_000_000, "liquidity_level": 1.0,
                                   "treasury_recommendation": "SURPLUS -> INVEST"})
    assert v_max == 1.0
    # Rétro-compat : sans net_cash, fallback sur recommendation
    assert e._normalize_treasury({"treasury_recommendation": "SURPLUS -> INVEST"}) == 1.0
    assert e._normalize_treasury({"treasury_recommendation": "DEFICIT -> BORROW"}) == -1.0


def test_normalize_forex_decompressed():
    """signal_score / 2.0 (au lieu de /4.0) — Forex contribue jusqu'à ±0.4 max."""
    e = AIDecisionEngine()
    # signal_score=0 → 0
    assert e._normalize_forex({"signal_score": 0}) == 0.0
    # signal_score=1 (1 règle) → +0.5 (était +0.25)
    assert e._normalize_forex({"signal_score": 1}) == 0.5
    # signal_score=2 (2 règles alignées) → +1.0 plein (était +0.5)
    assert e._normalize_forex({"signal_score": 2}) == 1.0
    # signal_score=4 (cas extrême) → clampé à +1.0
    assert e._normalize_forex({"signal_score": 4}) == 1.0
    # Symétrique côté SELL
    assert e._normalize_forex({"signal_score": -1}) == -0.5
    assert e._normalize_forex({"signal_score": -3}) == -1.0


def test_thresholds_lowered():
    """Seuils BUY/SELL passés à ±0.30 (au lieu de ±0.50) — moins de HOLD systématique."""
    e = AIDecisionEngine()
    assert e.BUY_THRESHOLD == 0.30
    assert e.SELL_THRESHOLD == -0.30
    # Score modéré +0.35 doit déclencher BUY (avant : HOLD)
    r = e.combine_decisions(
        {"signal_score": 1},  # forex normalisé +0.5 → contrib +0.2
        {"treasury_recommendation": "SURPLUS -> INVEST"},  # +0.25
        {"risk_level": "LOW"},  # +0.25
        {"status": "COMPLIANT", "compliance_score": 1.0},  # +0.10
    )
    # Total ~ 0.80 → BUY clair
    assert r["final_decision"] == "BUY"


def test_weighted_decision_blocked_by_compliance():
    e = AIDecisionEngine()
    r = e.combine_decisions(
        {"signal_score": 4},
        {"treasury_recommendation": "SURPLUS -> INVEST"},
        {"risk_level": "LOW"},
        {"status": "NON_COMPLIANT", "compliance_score": -1.0},
    )
    assert r["final_decision"] == "HOLD"
    assert r["decision_blocked"] is True
    assert any("Non-conformité" in reason for reason in r["blocking_reasons"])
