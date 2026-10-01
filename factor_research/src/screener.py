"""Stock screener: ranks today's universe on price based metrics,
with optional fundamentals pulled from yfinance.
"""
import numpy as np
import pandas as pd

from data import BENCHMARK


def price_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    stocks = daily.drop(columns=[BENCHMARK], errors="ignore")
    rets = stocks.pct_change()
    last = stocks.iloc[-1]
    bench = daily[BENCHMARK].pct_change() if BENCHMARK in daily else None

    df = pd.DataFrame({
        "price": last,
        "ret_1m": last / stocks.iloc[-22] - 1,
        "mom_12_1": stocks.iloc[-22] / stocks.iloc[-253] - 1,
        "vol_6m": rets.iloc[-126:].std() * np.sqrt(252),
        "pct_off_52w_high": last / stocks.iloc[-252:].max() - 1,
        "above_200dma": last > stocks.iloc[-200:].mean(),
    })
    if bench is not None:
        window = rets.iloc[-252:]
        b = bench.iloc[-252:]
        df["beta_1y"] = window.apply(lambda s: s.cov(b) / b.var())
    return df


def add_fundamentals(df: pd.DataFrame) -> pd.DataFrame:
    """Pull a few valuation and quality fields. Slow: one request per ticker."""
    import yfinance as yf

    fields = {
        "forwardPE": "fwd_pe",
        "priceToBook": "pb",
        "returnOnEquity": "roe",
        "debtToEquity": "debt_to_equity",
        "dividendYield": "div_yield",
        "sector": "sector",
    }
    rows = {}
    for t in df.index:
        try:
            info = yf.Ticker(t).info
            rows[t] = {new: info.get(old) for old, new in fields.items()}
        except Exception:
            rows[t] = {}
    return df.join(pd.DataFrame(rows).T)


def composite_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Blend momentum (higher better) and volatility (lower better) into one score.
    Uses percentile ranks so different units are comparable."""
    score = df["mom_12_1"].rank(pct=True) + (-df["vol_6m"]).rank(pct=True)
    if "roe" in df and df["roe"].notna().sum() > 5:
        score = score + pd.to_numeric(df["roe"], errors="coerce").rank(pct=True)
    if "fwd_pe" in df and df["fwd_pe"].notna().sum() > 5:
        pe = pd.to_numeric(df["fwd_pe"], errors="coerce").where(lambda x: x > 0)
        score = score + (-pe).rank(pct=True)
    return df.assign(score=score).sort_values("score", ascending=False)


def screen(daily, fundamentals=False, max_vol=None, require_uptrend=False):
    df = price_metrics(daily)
    if fundamentals:
        df = add_fundamentals(df)
    if max_vol is not None:
        df = df[df["vol_6m"] <= max_vol]
    if require_uptrend:
        df = df[df["above_200dma"]]
    return composite_rank(df)
