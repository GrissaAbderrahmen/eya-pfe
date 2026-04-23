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
