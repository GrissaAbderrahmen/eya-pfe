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
    """Le risk_score brut (0-8) doit produire des valeurs continues, pas juste {-1, 0, +1}."""
    e = AIDecisionEngine()
    # risk_score=0 → +1.0
    assert e._normalize_risk({"risk_score": 0, "risk_level": "LOW"}) == 1.0
    # risk_score=4 (milieu) → 0.0
    assert e._normalize_risk({"risk_score": 4, "risk_level": "MEDIUM"}) == 0.0
    # risk_score=5 (MEDIUM mais légèrement risqué) → −0.25 (visible !)
    assert e._normalize_risk({"risk_score": 5, "risk_level": "MEDIUM"}) == -0.25
    # risk_score=8 → −1.0
    assert e._normalize_risk({"risk_score": 8, "risk_level": "HIGH"}) == -1.0
    # Rétro-compat : sans risk_score, fallback sur level
    assert e._normalize_risk({"risk_level": "LOW"}) == 1.0
    assert e._normalize_risk({"risk_level": "MEDIUM"}) == 0.0
    assert e._normalize_risk({"risk_level": "HIGH"}) == -1.0


def test_normalize_treasury_continuous():
    """net_cash + liquidité doivent produire des valeurs continues, pas juste {-1, 0, +1}."""
    e = AIDecisionEngine()
    # Cash positif modéré + liquidité moyenne → valeur intermédiaire visible
    v = e._normalize_treasury({"net_cash": 600_000, "liquidity_level": 0.7,
                               "treasury_recommendation": "SURPLUS -> INVEST"})
    assert 0.1 < v < 0.6, f"Attendu valeur continue intermédiaire, eu {v}"
    # Cash neutre + liquidité neutre → proche de 0 mais pas EXACTEMENT 0 dans tous les cas
    v_neutral = e._normalize_treasury({"net_cash": 0, "liquidity_level": 0.5,
                                       "treasury_recommendation": "BALANCED -> HOLD"})
    assert v_neutral == 0.0  # Cas vraiment neutre, OK qu'il soit 0
    # Cash très positif + bonne liquidité → +1
    v_max = e._normalize_treasury({"net_cash": 2_000_000, "liquidity_level": 1.0,
                                   "treasury_recommendation": "SURPLUS -> INVEST"})
    assert v_max == 1.0
    # Rétro-compat : sans net_cash, fallback sur recommendation
    assert e._normalize_treasury({"treasury_recommendation": "SURPLUS -> INVEST"}) == 1.0
    assert e._normalize_treasury({"treasury_recommendation": "DEFICIT -> BORROW"}) == -1.0


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
