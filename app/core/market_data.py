"""Récupération des données de marché OHLC — yfinance + fallback CSV bundlé.

Trois couches de robustesse pour Streamlit Cloud (où Yahoo rate-limit les IPs partagées) :

1. **yfinance** (source primaire) : OHLC quotidien temps réel.
2. **CSV bundlé** (`app/data/*.csv`) : 1 an d'historique pré-téléchargé,
   committé dans le repo. Sert de fallback si yfinance retourne vide ou
   plante (rate limit, blocage Cloudflare, panne réseau).
3. **Taux simulé** (`yfinance_pairs.SIMULATED_BASE_PRICES`) : valeur de
   référence si même les CSV manquent.

Cache `@st.cache_data(ttl=86400)` (24 h) pour minimiser les appels yfinance —
on n'a pas besoin de cotations intra-day.
"""

from __future__ import annotations

from pathlib import Path

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

_DATA_DIR = Path(__file__).parent.parent / "data"
_PERIOD_DAYS = {"5d": 5, "1mo": 22, "3mo": 66, "6mo": 132, "1y": 260, "2y": 520}


def _cache(ttl: int = 86400):
    """Decorator : st.cache_data si Streamlit dispo, no-op sinon."""
    if _HAS_STREAMLIT:
        return st.cache_data(ttl=ttl, show_spinner=False)
    def passthrough(fn):
        return fn
    return passthrough


def _load_bundled_csv(pair: str, period: str) -> pd.DataFrame:
    """Charge le CSV pré-téléchargé pour cette paire, tronqué à `period`."""
    slug = pair.replace("/", "_")
    path = _DATA_DIR / f"{slug}.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    except Exception:
        return pd.DataFrame()
    n = _PERIOD_DAYS.get(period, 66)
    return df.tail(n).copy()


def _try_yfinance(pair: str, period: str) -> pd.DataFrame:
    """Tente un appel yfinance. Retourne DataFrame vide si échec ou rate limit."""
    ticker = PAIR_TO_TICKER.get(pair)
    if ticker is None or yf is None:
        return pd.DataFrame()
    try:
        df = yf.download(
            ticker, period=period, interval="1d",
            progress=False, auto_adjust=False, threads=False,
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


@_cache(ttl=86400)
def fetch_history_ohlc(pair: str, period: str = "3mo") -> pd.DataFrame:
    """Récupère l'historique OHLC quotidien — yfinance d'abord, CSV bundlé en fallback.

    Cache 24h. Retourne un DataFrame vide uniquement si toutes les sources
    sont indisponibles (rare en pratique grâce au CSV bundlé).
    """
    df = _try_yfinance(pair, period)
    if not df.empty:
        return df
    return _load_bundled_csv(pair, period)


def fetch_latest_rate(pair: str) -> tuple[float | None, str]:
    """Retourne (taux, source) pour la paire — dernier Close ou fallback simulé."""
    df = fetch_history_ohlc(pair, period="5d")
    if not df.empty:
        return float(df["Close"].iloc[-1]), "API"
    fallback = SIMULATED_BASE_PRICES.get(pair)
    if fallback is None:
        return None, "—"
    return fallback, "SIMULATION"


def get_data_source(pair: str) -> str:
    """Indique la source effective des données pour cette paire (debug/UI)."""
    if not _try_yfinance(pair, "5d").empty:
        return "yfinance"
    if not _load_bundled_csv(pair, "5d").empty:
        return "CSV bundlé"
    return "simulation"
