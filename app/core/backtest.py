"""Backtesting du modèle de décision sur historique réel yfinance.

Définition assumée (à défendre devant le jury) :
  - On rejoue le modèle Forex chaque jour sur l'historique disponible.
  - Trésorerie / Risque / Conformité sont fixés à des valeurs « moyennes »
    paramétrables — limitation honnête puisque nous n'avons pas l'historique
    réel de ces variables internes à la banque.
  - Pour chaque décision BUY ou SELL, on simule l'entrée au Close du jour J
    et la sortie au Close du jour J + N (holding_days). PnL = variation %.
  - Métriques : nombre de trades, % gagnants, PnL moyen, PnL cumulé,
    max drawdown, Sharpe simplifié (PnL/std × sqrt(252/holding_days)).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from .engine import (
    AIDecisionEngine,
    ComplianceModule,
    ForexAnalysisModule,
    RiskManagementModule,
    TreasuryManagementModule,
)
from .market_data import fetch_history_ohlc


@dataclass
class BacktestParams:
    pair: str = "EUR/USD"
    period: str = "1y"
    holding_days: int = 5
    rolling_window: int = 30
    # Valeurs moyennes fixées (limitation documentée)
    inflation: float = 6.0
    central_bank_rate: float = 8.0
    exposure_level: float = 0.50
    cash_inflow: float = 1_200_000
    cash_outflow: float = 950_000
    liquidity_level: float = 0.65
    interbank_rate: float = 6.25
    lcr: float = 1.20
    position_eur: float = 400_000
    position_usd: float = 300_000
    position_limit: float = 2_000_000


@dataclass
class Trade:
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    direction: str  # BUY ou SELL
    entry_price: float
    exit_price: float
    pnl_pct: float
    confidence: float
    global_score: float


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    decisions: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def n_wins(self) -> int:
        return sum(1 for t in self.trades if t.pnl_pct > 0)

    @property
    def win_rate(self) -> float:
        return (self.n_wins / self.n_trades * 100) if self.n_trades else 0.0

    @property
    def total_return_pct(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        return float((self.equity_curve.iloc[-1] - 1.0) * 100)

    @property
    def max_drawdown_pct(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        running_max = self.equity_curve.cummax()
        drawdown = (self.equity_curve - running_max) / running_max
        return float(drawdown.min() * 100)

    @property
    def sharpe_simplified(self) -> float:
        if not self.trades:
            return 0.0
        pnls = [t.pnl_pct / 100 for t in self.trades]
        if len(pnls) < 2:
            return 0.0
        mean_pnl = sum(pnls) / len(pnls)
        var = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
        std = math.sqrt(var)
        if std == 0:
            return 0.0
        # Annualisé : ~252 jours ouvrés / holding_days périodes par an
        return mean_pnl / std * math.sqrt(252 / max(1, self.trades[0].entry_date and 5))

    def trades_dataframe(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(columns=["entry_date", "direction", "entry_price",
                                         "exit_date", "exit_price", "pnl_pct",
                                         "confidence", "global_score"])
        return pd.DataFrame([
            {
                "entry_date": t.entry_date.strftime("%Y-%m-%d"),
                "direction": t.direction,
                "entry_price": round(t.entry_price, 4),
                "exit_date": t.exit_date.strftime("%Y-%m-%d"),
                "exit_price": round(t.exit_price, 4),
                "pnl_pct": round(t.pnl_pct, 3),
                "confidence": round(t.confidence, 1),
                "global_score": round(t.global_score, 3),
            }
            for t in self.trades
        ])


def run_backtest(params: BacktestParams) -> BacktestResult:
    """Exécute le backtest et retourne le résultat structuré."""
    df = fetch_history_ohlc(params.pair, period=params.period)
    if df.empty or len(df) < params.rolling_window + params.holding_days + 1:
        return BacktestResult()

    forex = ForexAnalysisModule()
    treasury = TreasuryManagementModule()
    risk_mod = RiskManagementModule()
    compliance = ComplianceModule()
    engine = AIDecisionEngine()

    # Pré-calcule les modules statiques (Trésorerie / Conformité ne dépendent pas du temps)
    treasury_result = treasury.evaluate_treasury_position(
        params.cash_inflow, params.cash_outflow,
        params.liquidity_level, params.interbank_rate,
    )
    compliance_result = compliance.check_compliance(
        params.lcr, params.position_eur, params.position_usd,
        params.position_limit, params.exposure_level,
    )

    closes = df["Close"]
    decisions_rows = []
    trades: list[Trade] = []

    for i in range(params.rolling_window, len(closes) - params.holding_days):
        window = closes.iloc[i - params.rolling_window: i + 1].tolist()
        current_rate = window[-1]
        forex_result = forex.generate_signal(current_rate, window)
        risk_result = risk_mod.assess_risk(
            params.inflation, params.central_bank_rate,
            forex_result["volatility"], params.exposure_level,
        )
        decision = engine.combine_decisions(
            forex_result, treasury_result, risk_result, compliance_result,
        )

        date = closes.index[i]
        decisions_rows.append({
            "date": date,
            "close": current_rate,
            "decision": decision["final_decision"],
            "global_score": decision["global_score"],
            "confidence": decision["confidence_score"],
            "rsi": forex_result["rsi"],
        })

        if decision["final_decision"] in ("BUY", "SELL") and not decision["decision_blocked"]:
            entry_price = current_rate
            exit_idx = i + params.holding_days
            exit_price = float(closes.iloc[exit_idx])
            exit_date = closes.index[exit_idx]
            pnl_dir = 1 if decision["final_decision"] == "BUY" else -1
            pnl_pct = pnl_dir * (exit_price - entry_price) / entry_price * 100
            trades.append(Trade(
                entry_date=date,
                exit_date=exit_date,
                direction=decision["final_decision"],
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_pct=pnl_pct,
                confidence=decision["confidence_score"],
                global_score=decision["global_score"],
            ))

    decisions_df = pd.DataFrame(decisions_rows).set_index("date") if decisions_rows else pd.DataFrame()

    # Equity curve : 1 + pnl cumulés (chaque trade est un investissement %)
    equity_curve = pd.Series(dtype=float)
    if trades:
        equity_curve = pd.Series(
            [1.0 * (1 + sum(t.pnl_pct / 100 for t in trades[:i + 1])) for i in range(len(trades))],
            index=[t.exit_date for t in trades],
        )

    return BacktestResult(trades=trades, equity_curve=equity_curve, decisions=decisions_df)


def naive_buy_and_hold_return(pair: str, period: str = "1y") -> float | None:
    """Rendement naïf : acheter au début, vendre à la fin de la période."""
    df = fetch_history_ohlc(pair, period=period)
    if df.empty or len(df) < 2:
        return None
    return float((df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0] * 100)
