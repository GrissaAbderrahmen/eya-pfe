"""Mapping des paires de devises vers les tickers Yahoo Finance.

Yahoo utilise le suffixe `=X` pour les paires FX. Convention :
- USD comme base : on peut écrire soit `USDJPY=X` soit `JPY=X` (alias).
  On garde la forme explicite pour la lisibilité.
- Pour les autres paires : `EURUSD=X`, `EURGBP=X`, etc.

Ces 8 paires couvrent tout le périmètre demandé par le feedback de l'ami :
EUR/USD, EUR/TND, USD/TND, GBP/USD, GBP/TND, USD/JPY, USD/CHF, EUR/GBP.
"""

PAIR_TO_TICKER = {
    "EUR/USD": "EURUSD=X",
    "EUR/TND": "EURTND=X",
    "USD/TND": "USDTND=X",
    "GBP/USD": "GBPUSD=X",
    "GBP/TND": "GBPTND=X",
    "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X",
    "EUR/GBP": "EURGBP=X",
}

PAIRS = list(PAIR_TO_TICKER.keys())

# Fallback si yfinance échoue ou si le ticker n'a pas de données récentes.
SIMULATED_BASE_PRICES = {
    "EUR/USD": 1.09,
    "EUR/TND": 3.38,
    "USD/TND": 3.10,
    "GBP/USD": 1.27,
    "GBP/TND": 3.95,
    "USD/JPY": 154.0,
    "USD/CHF": 0.91,
    "EUR/GBP": 0.86,
}
