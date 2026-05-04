"""Tests pour la couche market_data (Yahoo Chart API + cache)."""

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
    """Mock _fetch_yahoo_chart et vérifie qu'on récupère les 4 colonnes OHLC."""
    fake_df = pd.DataFrame(
        {
            "Open": [1.0, 1.01, 1.02],
            "High": [1.05, 1.06, 1.07],
            "Low": [0.99, 1.00, 1.01],
            "Close": [1.02, 1.03, 1.04],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )
    market_data.fetch_history_ohlc.clear()
    with patch.object(market_data, "_fetch_yahoo_chart",
                      return_value=(fake_df, {"regularMarketPrice": 1.04})):
        result = market_data.fetch_history_ohlc("EUR/USD", period="3mo")
    assert list(result.columns) == ["Open", "High", "Low", "Close"]
    assert len(result) == 3


def test_fetch_history_unknown_pair_returns_empty():
    market_data.fetch_history_ohlc.clear()
    result = market_data.fetch_history_ohlc("XXX/YYY", period="3mo")
    assert result.empty


def test_fetch_history_handles_yahoo_failure_uses_csv_bundle():
    """Si Yahoo échoue, le CSV bundlé doit prendre le relais."""
    market_data.fetch_history_ohlc.clear()
    with patch.object(market_data, "_fetch_yahoo_chart",
                      return_value=(pd.DataFrame(), {})):
        result = market_data.fetch_history_ohlc("EUR/USD", period="3mo")
    # Le CSV bundlé existe pour EUR/USD → résultat non-vide
    assert not result.empty
    assert list(result.columns) == ["Open", "High", "Low", "Close"]


def test_fetch_history_returns_empty_when_all_sources_fail():
    """Si Yahoo ET CSV bundlé échouent, on retourne un DataFrame vide."""
    market_data.fetch_history_ohlc.clear()
    with patch.object(market_data, "_fetch_yahoo_chart",
                      return_value=(pd.DataFrame(), {})), \
         patch.object(market_data, "_load_bundled_csv",
                      return_value=pd.DataFrame()):
        result = market_data.fetch_history_ohlc("EUR/USD", period="3mo")
    assert result.empty


def test_fetch_realtime_price_falls_back_to_simulation():
    """Si Yahoo ne retourne pas de regularMarketPrice, fallback simulé."""
    market_data.fetch_realtime_price.clear()
    with patch.object(market_data, "_fetch_yahoo_chart",
                      return_value=(pd.DataFrame(), {})):
        rate, source, _ts = market_data.fetch_realtime_price("EUR/TND")
    assert source == "SIMULATION"
    assert rate == SIMULATED_BASE_PRICES["EUR/TND"]


def test_fetch_realtime_price_uses_yahoo_when_available():
    market_data.fetch_realtime_price.clear()
    meta = {"regularMarketPrice": 3.42, "regularMarketTime": 1730000000}
    with patch.object(market_data, "_fetch_yahoo_chart",
                      return_value=(pd.DataFrame(), meta)):
        rate, source, ts = market_data.fetch_realtime_price("EUR/TND")
    assert source == "API"
    assert rate == 3.42
    assert ts is not None


def test_fetch_latest_rate_compat_wrapper():
    """fetch_latest_rate délègue à fetch_realtime_price (rétro-compat)."""
    market_data.fetch_realtime_price.clear()
    meta = {"regularMarketPrice": 1.0925, "regularMarketTime": 1730000000}
    with patch.object(market_data, "_fetch_yahoo_chart",
                      return_value=(pd.DataFrame(), meta)):
        rate, source = market_data.fetch_latest_rate("EUR/USD")
    assert source == "API"
    assert rate == 1.0925
