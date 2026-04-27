"""Tests pour la couche market_data (yfinance + cache)."""

import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core import market_data
from app.core.yfinance_pairs import PAIR_TO_TICKER, PAIRS, SIMULATED_BASE_PRICES


def test_pairs_consistency():
    """Les 3 dictionnaires de paires doivent rester alignés."""
    assert set(PAIRS) == set(PAIR_TO_TICKER.keys())
    assert set(PAIRS) == set(SIMULATED_BASE_PRICES.keys())
    assert len(PAIRS) == 8


def test_fetch_history_returns_ohlc_columns():
    """Mock yf.download et vérifie qu'on récupère les 4 colonnes OHLC."""
    fake_df = pd.DataFrame(
        {
            "Open": [1.0, 1.01, 1.02],
            "High": [1.05, 1.06, 1.07],
            "Low": [0.99, 1.00, 1.01],
            "Close": [1.02, 1.03, 1.04],
            "Volume": [1000, 1100, 1200],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )
    market_data.fetch_history_ohlc.clear()  # vide le cache
    with patch.object(market_data, "yf") as mock_yf:
        mock_yf.download.return_value = fake_df
        result = market_data.fetch_history_ohlc("EUR/USD", period="3mo")
    assert list(result.columns) == ["Open", "High", "Low", "Close"]
    assert len(result) == 3


def test_fetch_history_unknown_pair_returns_empty():
    market_data.fetch_history_ohlc.clear()
    result = market_data.fetch_history_ohlc("XXX/YYY", period="3mo")
    assert result.empty


def test_fetch_history_handles_yfinance_failure():
    """Si yfinance lève, on doit retourner un DataFrame vide (pas planter la page)."""
    market_data.fetch_history_ohlc.clear()
    with patch.object(market_data, "yf") as mock_yf:
        mock_yf.download.side_effect = RuntimeError("network down")
        result = market_data.fetch_history_ohlc("EUR/USD", period="3mo")
    assert result.empty


def test_fetch_latest_rate_falls_back_when_empty():
    market_data.fetch_history_ohlc.clear()
    with patch.object(market_data, "yf") as mock_yf:
        mock_yf.download.return_value = pd.DataFrame()
        rate, source = market_data.fetch_latest_rate("EUR/TND")
    assert source == "SIMULATION"
    assert rate == SIMULATED_BASE_PRICES["EUR/TND"]


def test_fetch_latest_rate_uses_yfinance_when_available():
    fake_df = pd.DataFrame(
        {"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [3.42]},
        index=pd.date_range("2026-04-25", periods=1, freq="D"),
    )
    market_data.fetch_history_ohlc.clear()
    with patch.object(market_data, "yf") as mock_yf:
        mock_yf.download.return_value = fake_df
        rate, source = market_data.fetch_latest_rate("EUR/TND")
    assert source == "API"
    assert rate == 3.42
