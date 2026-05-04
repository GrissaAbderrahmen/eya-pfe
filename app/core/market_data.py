"""Récupération des données de marché OHLC — Yahoo Finance Chart API directe.

Trois couches de robustesse :

1. **Yahoo Chart API** (source primaire) : `query1.finance.yahoo.com/v8/finance/chart`
   appelée directement en HTTP. Sert le **vrai intraday FX** (5m, 15m, 1h)
   contrairement à la lib `yfinance` qui retourne souvent vide sur les tickers `=X`.
   Le champ `meta.regularMarketPrice` donne le **prix en temps réel**.

2. **CSV bundlé** (`app/data/*.csv`) : 1 an d'historique pré-téléchargé
   committé dans le repo. Fallback si Yahoo est indisponible (rate limit,
   blocage Cloudflare, panne réseau).

3. **Taux simulé** (`yfinance_pairs.SIMULATED_BASE_PRICES`) : valeur de
   référence si même les CSV manquent.

Cache `@st.cache_data(ttl=60)` (60 s) — données fraîches à la minute, exigence
salle de marché. Le bouton « Rafraîchir » force un re-fetch immédiat.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

from .yfinance_pairs import PAIR_TO_TICKER, SIMULATED_BASE_PRICES

_DATA_DIR = Path(__file__).parent.parent / "data"
_PERIOD_DAYS = {"5d": 5, "1mo": 22, "3mo": 66, "6mo": 132, "1y": 260, "2y": 520}
_YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_HTTP_TIMEOUT = 8  # secondes — coupe court si Yahoo lag

# Mapping timeframe UI → (range Yahoo, interval Yahoo, label FR).
# 1D et 1W passent en intraday 5m/15m pour du *vrai* temps réel.
TIMEFRAMES = {
    "1D": {"range": "1d",  "interval": "5m",  "label": "1 jour (5 min)"},
    "1W": {"range": "5d",  "interval": "15m", "label": "1 semaine (15 min)"},
    "1M": {"range": "1mo", "interval": "1h",  "label": "1 mois (1 h)"},
    "3M": {"range": "3mo", "interval": "1d",  "label": "3 mois (1 j)"},
    "6M": {"range": "6mo", "interval": "1d",  "label": "6 mois (1 j)"},
    "1Y": {"range": "1y",  "interval": "1d",  "label": "1 an (1 j)"},
}


def _cache(ttl: int):
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


def _fetch_yahoo_chart(pair: str, range_: str, interval: str) -> tuple[pd.DataFrame, dict]:
    """Appelle directement l'API Yahoo Chart. Retourne (df_ohlc, meta).

    Plus fiable que la lib yfinance pour l'intraday FX (`=X` tickers).
    Le `meta` contient notamment `regularMarketPrice` (prix temps réel).
    """
    if requests is None:
        return pd.DataFrame(), {}
    ticker = PAIR_TO_TICKER.get(pair)
    if ticker is None:
        return pd.DataFrame(), {}
    url = _YAHOO_CHART_URL.format(ticker=ticker)
    try:
        resp = requests.get(
            url,
            params={"range": range_, "interval": interval},
            headers={"User-Agent": _USER_AGENT},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return pd.DataFrame(), {}

    chart = payload.get("chart", {}) or {}
    if chart.get("error") or not chart.get("result"):
        return pd.DataFrame(), {}

    result = chart["result"][0]
    meta = result.get("meta", {}) or {}
    timestamps = result.get("timestamp") or []
    indicators = (result.get("indicators") or {}).get("quote") or [{}]
    quote = indicators[0]
    if not timestamps or not quote.get("close"):
        return pd.DataFrame(), meta

    idx = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None)
    df = pd.DataFrame({
        "Open": quote.get("open"),
        "High": quote.get("high"),
        "Low": quote.get("low"),
        "Close": quote.get("close"),
    }, index=idx).dropna()
    return df, meta


@_cache(ttl=60)
def fetch_history_ohlc(pair: str, period: str = "3mo") -> pd.DataFrame:
    """Historique OHLC quotidien — Yahoo Chart API d'abord, CSV bundlé en fallback.

    Cache 60 s. Le bouton Rafraîchir vide ce cache à la demande.
    """
    df, _ = _fetch_yahoo_chart(pair, range_=period, interval="1d")
    if not df.empty:
        return df
    return _load_bundled_csv(pair, period)


@_cache(ttl=60)
def fetch_history_by_timeframe(pair: str, timeframe: str = "3M") -> pd.DataFrame:
    """Historique selon un timeframe UI (1D, 1W, 1M, 3M, 6M, 1Y).

    1D / 1W / 1M passent en intraday (5 min / 15 min / 1 h) — vrai temps réel.
    3M / 6M / 1Y restent en daily. Cache 60 s.
    """
    spec = TIMEFRAMES.get(timeframe)
    if spec is None:
        return fetch_history_ohlc(pair, period="3mo")
    df, _ = _fetch_yahoo_chart(pair, range_=spec["range"], interval=spec["interval"])
    if not df.empty:
        return df
    # Fallback CSV : équivalent daily approximatif.
    fallback_period = spec["range"] if spec["interval"] == "1d" else "5d"
    return _load_bundled_csv(pair, fallback_period)


@_cache(ttl=60)
def fetch_realtime_price(pair: str) -> tuple[float | None, str, datetime | None]:
    """Retourne (prix temps réel, source, timestamp) — `meta.regularMarketPrice`.

    C'est le **dernier prix coté** par Yahoo (rafraîchi en quasi-temps-réel sur
    les paires majeures). À utiliser pour l'affichage du taux courant plutôt
    que le dernier Close du DataFrame, qui peut être en retard de quelques minutes.
    """
    _, meta = _fetch_yahoo_chart(pair, range_="1d", interval="5m")
    price = meta.get("regularMarketPrice") if meta else None
    ts_unix = meta.get("regularMarketTime") if meta else None
    ts = datetime.fromtimestamp(ts_unix, tz=timezone.utc) if ts_unix else None
    if price is not None:
        return float(price), "API", ts
    fallback = SIMULATED_BASE_PRICES.get(pair)
    if fallback is None:
        return None, "—", None
    return fallback, "SIMULATION", None


def fetch_latest_rate(pair: str) -> tuple[float | None, str]:
    """Compat : retourne (taux, source). Utilise désormais le prix temps réel."""
    price, source, _ = fetch_realtime_price(pair)
    return price, source


def get_data_source(pair: str) -> str:
    """Indique la source effective des données pour cette paire (debug/UI)."""
    df, meta = _fetch_yahoo_chart(pair, range_="5d", interval="1d")
    if not df.empty or meta.get("regularMarketPrice") is not None:
        return "Yahoo Finance"
    if not _load_bundled_csv(pair, "5d").empty:
        return "CSV bundlé"
    return "simulation"
