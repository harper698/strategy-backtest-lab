import json
import math

import numpy as np
import pandas as pd
import pytest

from backtest_lab import performance_metrics


def test_hand_calculated_returns_drawdown_and_sample_sharpe():
    metrics = performance_metrics(pd.Series([100, 110, 99, 108.9]), bars_per_year=3)
    returns = np.array([0.1, -0.1, 0.1])
    assert metrics["intervals"] == 3
    assert metrics["total_return"] == pytest.approx(0.089)
    assert metrics["cagr"] == pytest.approx(0.089)
    assert metrics["max_drawdown"] == pytest.approx(-0.1)
    assert metrics["annualized_volatility"] == pytest.approx(returns.std(ddof=1) * math.sqrt(3))
    assert metrics["sharpe_ratio"] == pytest.approx(
        returns.mean() / returns.std(ddof=1) * math.sqrt(3),
    )


def test_cagr_counts_intervals_not_rows():
    metrics = performance_metrics(pd.Series([100, 105, 110]), bars_per_year=4)
    assert metrics["cagr"] == pytest.approx(1.1**2 - 1)


def test_initial_equity_in_drawdown():
    metrics = performance_metrics(pd.Series([100, 90, 81]), bars_per_year=365)
    assert metrics["max_drawdown"] == pytest.approx(-0.19)


def test_risk_free_is_compounded_to_per_bar():
    equity = pd.Series([100, 110, 99, 108.9])
    metrics = performance_metrics(equity, bars_per_year=3, annual_risk_free=0.331)
    expected = ((0.1 - 0.1 + 0.1) / 3 - 0.1) / np.std([0.1, -0.1, 0.1], ddof=1) * math.sqrt(3)
    assert metrics["sharpe_ratio"] == pytest.approx(expected)


def test_flat_equity_and_insufficient_intervals_are_json_safe():
    flat = performance_metrics(pd.Series([100, 100, 100]))
    assert flat["sharpe_ratio"] is None
    assert flat["annualized_volatility"] == 0
    one = performance_metrics(pd.Series([100, 101]))
    assert one["annualized_volatility"] is None
    assert one["sharpe_ratio"] is None
    json.dumps([flat, one], allow_nan=False)


def test_unrepresentable_cagr_returns_null():
    metrics = performance_metrics(pd.Series([1, 100]), bars_per_year=365)
    assert metrics["cagr"] is None
    json.dumps(metrics, allow_nan=False)


@pytest.mark.parametrize("start, end, rows, expected", [
    (1e20, 1.0, 21, -0.9),
    (1e-200, 1e200, 401, 9.0),
])
def test_finite_cagr_survives_extreme_cumulative_return(start, end, rows, expected):
    with np.errstate(over="ignore"):
        metrics = performance_metrics(pd.Series(np.geomspace(start, end, rows)), bars_per_year=1)
    assert metrics["cagr"] == pytest.approx(expected)
    json.dumps(metrics, allow_nan=False)


def test_constant_growth_has_undefined_sharpe_despite_roundoff():
    metrics = performance_metrics(pd.Series([100.0 * 1.1**i for i in range(8)]))
    assert metrics["sharpe_ratio"] is None
    assert metrics["annualized_volatility"] == 0


def test_small_real_variance_is_preserved():
    equity = pd.Series(np.cumprod(1 + np.array([0, 1e-12, -1e-12, 2e-12])))
    metrics = performance_metrics(equity)
    assert metrics["annualized_volatility"] > 0
    assert metrics["sharpe_ratio"] is not None


@pytest.mark.parametrize("bars", [0, -1, 1.5, True, 10**400])
def test_invalid_bars_per_year(bars):
    with pytest.raises(ValueError, match="bars_per_year"):
        performance_metrics(pd.Series([1, 2]), bars)


@pytest.mark.parametrize("risk", [-1, -2, np.nan, np.inf])
def test_invalid_risk_free(risk):
    with pytest.raises(ValueError, match="risk_free"):
        performance_metrics(pd.Series([1, 2]), annual_risk_free=risk)


@pytest.mark.parametrize("equity", [[1], [1, 0], [1, -1], [1, np.nan], [1, np.inf]])
def test_bad_equity_rejected(equity):
    with pytest.raises(ValueError, match="equity"):
        performance_metrics(pd.Series(equity))
