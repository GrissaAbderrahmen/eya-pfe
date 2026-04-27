"""Récupération des données de marché OHLC via yfinance, avec cache Streamlit.

Ce module remplace l'ancien appel `Frankfurter /latest` qui ne donnait qu'un
point de cotation. yfinance fournit l'historique journalier complet (Open,
High, Low, Close) sur toutes les paires demandées, y compris les paires TND
qui n'étaient pas couvertes par Frankfurter.

Le cache `@st.cache_data(ttl=3600)` évite de retaper Yahoo à chaque rerender.
En l'absence de Streamlit (tests, scripts), `st.cache_data` se comporte comme
un appel de fonction normal — pas d'erreur.
"""

from __future__ import annotations

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

from .yfinance_pairs import PAIR_TO_TICKER, SIMULATED_BASE_PRICES


def _cache(ttl: int = 3600):
    """Decorator that uses st.cache_data when Streamlit est disponible, no-op sinon."""
    if _HAS_STREAMLIT:
        return st.cache_data(ttl=ttl, show_spinner=False)
    def passthrough(fn):
        return fn
    return passthrough


@_cache(ttl=3600)
def fetch_history_ohlc(pair: str, period: str = "3mo") -> pd.DataFrame:
    """Récupère l'historique OHLC journalier pour une paire.

    Retourne un DataFrame indexé par date avec colonnes Open/High/Low/Close.
    Renvoie un DataFrame vide en cas d'échec — l'appelant doit gérer ce cas.
    """
    ticker = PAIR_TO_TICKER.get(pair)
    if ticker is None or yf is None:
        return pd.DataFrame()

    try:
        df = yf.download(
            ticker,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    cols = [c for c in ("Open", "High", "Low", "Close") if c in df.columns]
    if len(cols) < 4:
        return pd.DataFrame()

    return df[cols].dropna()


def fetch_latest_rate(pair: str) -> tuple[float | None, str]:
    """Retourne (taux, source) pour la paire — dernier Close yfinance ou fallback simulé."""
    df = fetch_history_ohlc(pair, period="5d")
    if not df.empty:
        return float(df["Close"].iloc[-1]), "API"
    fallback = SIMULATED_BASE_PRICES.get(pair)
    if fallback is None:
        return None, "—"
    return fallback, "SIMULATION"
