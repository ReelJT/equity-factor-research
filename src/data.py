"""Price data loading with a local cache.

Downloads daily adjusted close prices with yfinance and saves them to
data/prices.csv so you are not re-downloading every run.
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE = DATA_DIR / "prices.csv"

# A starter universe of large US stocks across sectors.
# Swap in your own list, or load the full S&P 500 from a CSV.
UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "ORCL", "CRM", "ADBE",
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "V", "MA",
    "UNH", "JNJ", "LLY", "PFE", "MRK", "ABBV", "TMO", "ABT", "AMGN", "CVS",
    "XOM", "CVX", "COP", "SLB", "EOG",
    "HD", "LOW", "MCD", "NKE", "SBUX", "TGT", "COST", "WMT", "PG", "KO", "PEP",
    "CAT", "DE", "HON", "GE", "UPS", "LMT", "RTX", "BA",
    "NEE", "DUK", "SO", "AMT", "PLD", "LIN",
]
BENCHMARK = "SPY"


def load_prices(tickers=None, start="2012-01-01", refresh=False) -> pd.DataFrame:
    """Return a DataFrame of daily adjusted closes (dates x tickers)."""
    tickers = list(tickers or UNIVERSE)
    if BENCHMARK not in tickers:
        tickers.append(BENCHMARK)

    if CACHE.exists() and not refresh:
        prices = pd.read_csv(CACHE, index_col=0, parse_dates=True)
        if set(tickers).issubset(prices.columns):
            return prices[tickers]

    import yfinance as yf  # imported here so the rest works without it

    raw = yf.download(tickers, start=start, auto_adjust=True, progress=False)
    prices = raw["Close"].dropna(how="all")
    DATA_DIR.mkdir(exist_ok=True)
    prices.to_csv(CACHE)
    return prices


def synthetic_prices(n_stocks=60, years=12, seed=7) -> pd.DataFrame:
    """Fake prices for testing the pipeline offline. Not real data."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2013-01-01", periods=252 * years)
    market = rng.normal(0.0004, 0.011, len(dates))
    cols = {}
    for i in range(n_stocks):
        beta = rng.uniform(0.6, 1.4)
        drift = rng.normal(0.0001, 0.0002)
        idio = rng.normal(0, rng.uniform(0.008, 0.02), len(dates))
        cols[f"STK{i:02d}"] = 100 * np.exp(np.cumsum(drift + beta * market + idio))
    cols[BENCHMARK] = 100 * np.exp(np.cumsum(market))
    return pd.DataFrame(cols, index=dates)
