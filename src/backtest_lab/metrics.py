"""Explicit annualization; undefined metrics serialize as JSON null."""

import math

import numpy as np
import pandas as pd


def validate_annualization(bars_per_year: int, annual_risk_free: float) -> None:
    if (
        isinstance(bars_per_year, bool) or not isinstance(bars_per_year, int)
        or not 1 <= bars_per_year <= 1_000_000
    ):
        raise ValueError("bars_per_year must be an integer from 1 to 1000000")
    if not math.isfinite(annual_risk_free) or annual_risk_free <= -1:
        raise ValueError("annual_risk_free must be finite and greater than -1")


def _finite(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


def performance_metrics(
    equity: pd.Series, bars_per_year: int = 365, annual_risk_free: float = 0.0,
) -> dict[str, float | int | None]:
    """Compute metrics from equity including the initial capital as row zero.

    Annualization uses len(equity)-1 actual intervals. Volatility and Sharpe use
    sample standard deviation (ddof=1), excluding any initial placeholder return.
    Max drawdown is a nonpositive fraction, measured from running equity peaks.
    """
    validate_annualization(bars_per_year, annual_risk_free)
    values = pd.Series(equity, copy=True).astype(float)
    if len(values) < 2 or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("equity requires at least two finite positive values")
    returns = values.pct_change(fill_method=None).iloc[1:]
    if not np.isfinite(returns).all():
        raise ValueError("equity produces nonfinite interval returns")
    intervals = len(returns)
    total_return = float(values.iloc[-1] / values.iloc[0] - 1)
    try:
        cagr = _finite(math.expm1(math.log1p(total_return) * bars_per_year / intervals))
    except (OverflowError, ValueError):
        cagr = None
    standard_deviation = float(returns.std(ddof=1)) if intervals >= 2 else math.nan
    tolerance = 4 * np.finfo(float).eps * max(1.0, float(returns.abs().max()))
    if standard_deviation <= tolerance:
        standard_deviation = 0.0
    volatility = _finite(standard_deviation * math.sqrt(bars_per_year))
    risk_free_per_bar = math.expm1(math.log1p(annual_risk_free) / bars_per_year)
    sharpe = None
    if standard_deviation > 0 and math.isfinite(standard_deviation):
        sharpe = _finite(
            (float(returns.mean()) - risk_free_per_bar)
            / standard_deviation * math.sqrt(bars_per_year)
        )
    return {
        "intervals": intervals,
        "bars_per_year": bars_per_year,
        "annual_risk_free": annual_risk_free,
        "total_return": _finite(total_return),
        "cagr": cagr,
        "annualized_volatility": volatility,
        "sharpe_ratio": sharpe,
        "max_drawdown": float((values / values.cummax() - 1).min()),
    }
