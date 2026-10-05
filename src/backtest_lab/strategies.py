"""Causal target-position signals. Warmup targets remain flat."""

import numpy as np
import pandas as pd


def _period(value: int, name: str, minimum: int = 1) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _prices(close: pd.Series) -> pd.Series:
    try:
        values = pd.Series(close, copy=True).astype(float)
    except (ValueError, TypeError) as exc:
        raise ValueError("close must contain finite positive prices") from exc
    if values.empty or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("close must contain finite positive prices")
    return values


def sma_signal(close: pd.Series, fast: int = 5, slow: int = 20) -> pd.Series:
    """Target 1 when the fully warmed fast SMA exceeds the slow SMA, else 0."""
    _period(fast, "fast")
    _period(slow, "slow", 2)
    if fast >= slow:
        raise ValueError("fast must be less than slow")
    values = _prices(close)
    fast_average, slow_average = values.rolling(fast).mean(), values.rolling(slow).mean()
    if (
        not np.isfinite(fast_average.iloc[fast - 1:]).all()
        or not np.isfinite(slow_average.iloc[slow - 1:]).all()
    ):
        raise ValueError("price magnitudes cause SMA numeric overflow")
    return (fast_average > slow_average).astype(int)


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI seeded by the first period simple averages, then Wilder smoothing.

    The first value is at index period (period + 1 prices). Both averages zero
    means RSI 50, gains only means 100, and losses only means 0.
    """
    _period(period, "period")
    values = _prices(close)
    result = np.full(len(values), np.nan)
    if len(values) <= period:
        return pd.Series(result, index=values.index, name="rsi")
    changes = np.diff(values.to_numpy())
    gains, losses = np.maximum(changes, 0), np.maximum(-changes, 0)
    # Scale before summing/multiplication to avoid overflowing finite prices.
    average_gain = float(np.sum(gains[:period] / period))
    average_loss = float(np.sum(losses[:period] / period))
    for i in range(period, len(values)):
        if i > period:
            average_gain = (1 - 1 / period) * average_gain + gains[i - 1] / period
            average_loss = (1 - 1 / period) * average_loss + losses[i - 1] / period
        scale = max(average_gain, average_loss)
        if scale == 0:
            result[i] = 50.0
        else:
            gain, loss = average_gain / scale, average_loss / scale
            result[i] = 100.0 * gain / (gain + loss)
    if not np.isfinite(result[period:]).all():
        raise ValueError("price magnitudes cause RSI numeric overflow")
    return pd.Series(result, index=values.index, name="rsi")


def rsi_signal(
    close: pd.Series, period: int = 14, lower: float = 30, upper: float = 70,
) -> pd.Series:
    """Enter below lower; exit above upper; otherwise retain the prior target."""
    if not np.isfinite([lower, upper]).all() or not 0 < lower < upper < 100:
        raise ValueError("RSI thresholds must satisfy 0 < lower < upper < 100")
    values = wilder_rsi(close, period)
    position, result = 0, []
    for value in values:
        if value < lower:
            position = 1
        elif value > upper:
            position = 0
        result.append(position)
    return pd.Series(result, index=values.index, name="target", dtype=int)
