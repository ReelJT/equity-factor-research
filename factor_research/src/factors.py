"""Factor definitions. Every factor uses only data available on the date it is computed."""
import pandas as pd


def momentum_12_1(monthly: pd.DataFrame) -> pd.DataFrame:
    """Return over the past 12 months, skipping the most recent month.

    Skipping the last month is standard because very short term returns
    tend to reverse, which would muddy the momentum signal.
    """
    return monthly.shift(1) / monthly.shift(12) - 1


def low_volatility(daily: pd.DataFrame, window=126) -> pd.DataFrame:
    """Negative of trailing 6 month daily volatility, sampled month end.

    Negated so that a higher score always means "more attractive".
    """
    vol = daily.pct_change().rolling(window).std() * (252 ** 0.5)
    return -vol.resample("ME").last()


def short_term_reversal(monthly: pd.DataFrame) -> pd.DataFrame:
    """Negative of last month's return (last month's losers score high)."""
    return -(monthly / monthly.shift(1) - 1)


FACTORS = {
    "momentum": lambda daily, monthly: momentum_12_1(monthly),
    "low_vol": lambda daily, monthly: low_volatility(daily),
    "reversal": lambda daily, monthly: short_term_reversal(monthly),
}
