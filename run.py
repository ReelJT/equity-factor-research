"""Run the factor backtest and the screener.

Examples:
    python run.py                         # momentum backtest + screener on real data
    python run.py --factor low_vol
    python run.py --fundamentals          # adds valuation/quality fields to the screen (slow)
    python run.py --demo                  # offline test with fake data
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from backtest import quintile_returns, summary
from data import load_prices, synthetic_prices
from factors import FACTORS
from screener import screen

OUT = Path(__file__).parent / "output"


def plot(results, factor, path):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    curves = (1 + results[["Q5", "Q1", "benchmark"]]).cumprod()
    curves.columns = ["Top quintile", "Bottom quintile", "Benchmark (SPY)"]
    curves.plot(ax=axes[0], color=["#1f6f8b", "#c8553d", "#888888"], lw=1.8)
    axes[0].set_title(f"{factor}: growth of $1")
    axes[0].set_ylabel("Value")

    ann = results[[f"Q{i}" for i in range(1, 6)]].mean() * 12
    ann.plot.bar(ax=axes[1], color="#1f6f8b")
    axes[1].set_title("Average annual return by quintile (Q5 = highest score)")
    axes[1].yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    axes[1].tick_params(axis="x", rotation=0)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--factor", default="momentum", choices=list(FACTORS))
    p.add_argument("--start", default="2012-01-01")
    p.add_argument("--fundamentals", action="store_true")
    p.add_argument("--refresh", action="store_true", help="re-download prices")
    p.add_argument("--demo", action="store_true", help="use fake data, no internet")
    args = p.parse_args()

    OUT.mkdir(exist_ok=True)
    daily = synthetic_prices() if args.demo else load_prices(start=args.start, refresh=args.refresh)

    results = quintile_returns(daily, args.factor)
    table = summary(results)
    pd.options.display.float_format = "{:,.3f}".format
    pd.options.display.width = 200
    pd.options.display.max_columns = 20
    print(f"\n=== {args.factor} backtest, {results.index[0]:%Y-%m} to {results.index[-1]:%Y-%m} ===")
    print(table)
    print(f"\nAverage monthly turnover in top quintile: {results['turnover'].mean():.0%}")

    results.to_csv(OUT / f"{args.factor}_monthly_returns.csv")
    table.to_csv(OUT / f"{args.factor}_summary.csv")
    plot(results, args.factor, OUT / f"{args.factor}_backtest.png")

    picks = screen(daily, fundamentals=args.fundamentals and not args.demo)
    picks.to_csv(OUT / "screen_today.csv")
    print("\n=== Top 15 from today's screen ===")
    print(picks.head(15))
    print(f"\nSaved results to {OUT}/")


if __name__ == "__main__":
    main()
