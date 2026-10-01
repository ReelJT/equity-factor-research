"""Monthly rebalanced quintile backtest for a single factor.

Each month end: rank stocks by factor score, split into 5 buckets,
hold each bucket equal weighted for the next month. Compare the top
bucket (Q5) against the bottom (Q1) and the benchmark.
"""
import numpy as np
import pandas as pd

from data import BENCHMARK
from factors import FACTORS


def quintile_returns(daily: pd.DataFrame, factor: str, n_buckets=5, cost_bps=10):
    stocks = daily.drop(columns=[BENCHMARK])
    monthly = stocks.resample("ME").last()
    scores = FACTORS[factor](stocks, monthly)
    fwd = monthly.pct_change().shift(-1)  # next month's return, the thing we try to predict

    rows, prev_top = [], set()
    for date in scores.index:
        s = scores.loc[date].dropna()
        r = fwd.loc[date]
        valid = s.index.intersection(r.dropna().index)
        if len(valid) < n_buckets * 3:
            continue
        buckets = pd.qcut(s[valid].rank(method="first"), n_buckets, labels=False) + 1
        row = {f"Q{b}": r[valid][buckets == b].mean() for b in range(1, n_buckets + 1)}

        # Rough trading cost on the top bucket: cost x fraction of names replaced
        top = set(buckets[buckets == n_buckets].index)
        turnover = 1.0 if not prev_top else len(top - prev_top) / len(top)
        row[f"Q{n_buckets}_net"] = row[f"Q{n_buckets}"] - turnover * cost_bps / 1e4 * 2
        row["turnover"] = turnover
        prev_top = top
        rows.append(pd.Series(row, name=date))

    out = pd.DataFrame(rows)
    out["long_short"] = out[f"Q{n_buckets}"] - out["Q1"]
    bench = daily[BENCHMARK].resample("ME").last().pct_change().shift(-1)
    out["benchmark"] = bench.reindex(out.index)
    # Label each row by the month the return was earned, not when it was formed
    out.index = out.index + pd.offsets.MonthEnd(1)
    return out.dropna(subset=["benchmark"])


def stats(r: pd.Series, rf_annual=0.0) -> dict:
    r = r.dropna()
    years = len(r) / 12
    growth = (1 + r).prod()
    cagr = growth ** (1 / years) - 1
    vol = r.std() * np.sqrt(12)
    sharpe = (r.mean() * 12 - rf_annual) / vol if vol else np.nan
    curve = (1 + r).cumprod()
    max_dd = (curve / curve.cummax() - 1).min()
    return {
        "CAGR": cagr,
        "Volatility": vol,
        "Sharpe": sharpe,
        "Max drawdown": max_dd,
        "Hit rate": (r > 0).mean(),
        "Months": len(r),
    }


def summary(results: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in results.columns if c.startswith("Q") or c in ("long_short", "benchmark")]
    return pd.DataFrame({c: stats(results[c]) for c in cols}).T
