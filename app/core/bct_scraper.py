"""Scraper minimaliste des taux officiels BCT (Banque Centrale de Tunisie).

La BCT publie les cours du jour sur son site institutionnel. Pas d'API publique
au format JSON — il faut parser du HTML. On fait un best-effort : si la
structure change ou si le site est down, on retourne un dict vide et
l'utilisateur voit « source BCT indisponible » dans l'UI.

Usage :
    from app.core.bct_scraper import fetch_bct_rates
    rates = fetch_bct_rates()  # {"USD": 3.10, "EUR": 3.38, ...}

Cache 24h (les taux BCT changent une fois par jour ouvré).
"""

from __future__ import annotations

import re
from typing import Any

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False


_BCT_URLS = [
    "https://www.bct.gov.tn/bct/siteprod/cours.jsp",
    "https://www.bct.gov.tn/bct/siteprod/cours_change.jsp",
]
_TIMEOUT = 8
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AttijariPFE/1.0)"}

_CURRENCY_PATTERNS = {
    "USD": re.compile(r"\b(USD|dollar)\b", re.IGNORECASE),
    "EUR": re.compile(r"\b(EUR|euro)\b", re.IGNORECASE),
    "GBP": re.compile(r"\b(GBP|sterling|livre)\b", re.IGNORECASE),
    "JPY": re.compile(r"\b(JPY|yen)\b", re.IGNORECASE),
    "CHF": re.compile(r"\b(CHF|franc suisse)\b", re.IGNORECASE),
}


def _cache(ttl: int = 86400):
    if _HAS_STREAMLIT:
        return st.cache_data(ttl=ttl, show_spinner=False)
    def passthrough(fn):
        return fn
    return passthrough


def _parse_rate(text: str) -> float | None:
    """Extrait le premier nombre décimal du texte."""
    if not text:
        return None
    cleaned = text.replace(",", ".").replace("\xa0", " ").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        v = float(match.group(0))
        return v if 0 < v < 100 else None  # plages plausibles pour TND
    except ValueError:
        return None


def _extract_from_html(html: str) -> dict[str, float]:
    """Cherche dans le HTML un tableau, identifie les lignes par devise, extrait le taux."""
    if not html or BeautifulSoup is None:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    rates: dict[str, float] = {}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            row_text = " ".join(cells)
            for code, pattern in _CURRENCY_PATTERNS.items():
                if code in rates or not pattern.search(row_text):
                    continue
                # On prend la dernière cellule numérique (souvent le cours d'achat ou vente)
                for cell in reversed(cells):
                    rate = _parse_rate(cell)
                    if rate is not None:
                        rates[code] = rate
                        break
    return rates


@_cache(ttl=86400)
def fetch_bct_rates() -> dict[str, Any]:
    """Retourne {currency: rate} ou {} si indisponible. Inclut un champ `_source`.

    Le résultat est mis en cache 24h.
    """
    for url in _BCT_URLS:
        try:
            r = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
            r.raise_for_status()
            rates = _extract_from_html(r.text)
            if rates:
                rates["_source"] = url
                return rates
        except Exception:
            continue
    return {}


def compare_with_yfinance(bct_rates: dict[str, Any], yf_close: float, pair: str) -> dict | None:
    """Calcule le delta % entre BCT et yfinance pour la devise non-TND de la paire.

    Renvoie None si on n'a pas de cours BCT pour cette paire.
    """
    if "/" not in pair:
        return None
    base, quote = pair.split("/")
    # On compare sur la devise « étrangère » côté BCT (taux en TND)
    foreign = base if quote == "TND" else (quote if base == "TND" else None)
    if foreign is None or foreign not in bct_rates:
        return None
    bct_rate = bct_rates[foreign]
    delta = (yf_close - bct_rate) / bct_rate * 100
    return {
        "currency": foreign,
        "bct_rate": bct_rate,
        "yfinance_rate": yf_close,
        "delta_pct": round(delta, 3),
    }
