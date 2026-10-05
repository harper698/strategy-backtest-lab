import numpy as np
import pandas as pd
import pytest

from backtest_lab import rsi_signal, sma_signal, wilder_rsi


def test_sma_warmup_and_strict_comparison():
    assert sma_signal(pd.Series([10, 10, 11, 8, 8]), fast=1, slow=2).tolist() == [0, 0, 1, 0, 0]


def test_wilder_seed_and_recursive_update_hand_calculation():
    # Changes +1, -1, +2: seed gains=1, losses=1/3 -> RSI 75.
    # Next change -1: gains=2/3, losses=5/9 -> RSI=600/11.
    result = wilder_rsi(pd.Series([10, 11, 10, 12, 11]), period=3)
    assert result.iloc[:3].isna().all()
    assert result.iloc[3] == pytest.approx(75)
    assert result.iloc[4] == pytest.approx(600 / 11)


@pytest.mark.parametrize("values, expected", [
    ([1, 2, 3, 4, 5], 100), ([5, 4, 3, 2, 1], 0), ([4, 4, 4, 4, 4], 50),
])
def test_wilder_zero_gain_loss_and_flat(values, expected):
    result = wilder_rsi(pd.Series(values), 2)
    assert result.iloc[:2].isna().all()
    assert result.iloc[2:].tolist() == [expected] * 3


def test_rsi_hysteresis_and_warmup():
    values = pd.Series([10, 9, 8, 8, 8.5, 10, 10])
    assert rsi_signal(values, period=2).tolist() == [0, 0, 1, 1, 1, 0, 0]


def test_rsi_short_series_remains_unwarmed():
    assert wilder_rsi(pd.Series([1, 2]), 3).isna().all()
    assert rsi_signal(pd.Series([1, 2]), 3).tolist() == [0, 0]


def test_large_finite_prices_do_not_silently_erase_rsi():
    rsi = wilder_rsi(pd.Series([1.0, 1e308] * 16), period=14)
    assert np.isfinite(rsi.iloc[14:]).all()
    assert rsi.iloc[14] == pytest.approx(50)
    assert rsi.iloc[15] > 50


@pytest.mark.parametrize("period", [0, -1, 2.5, True])
def test_invalid_rsi_period(period):
    with pytest.raises(ValueError, match="integer"):
        wilder_rsi(pd.Series([1, 2, 3]), period)


@pytest.mark.parametrize("fast, slow", [(0, 2), (2, 2), (3, 2), (1, True), (1, 2.5)])
def test_invalid_sma_periods(fast, slow):
    with pytest.raises(ValueError):
        sma_signal(pd.Series([1, 2, 3]), fast, slow)


@pytest.mark.parametrize("lower, upper", [(0, 70), (30, 100), (70, 30), (30, np.nan)])
def test_invalid_rsi_thresholds(lower, upper):
    with pytest.raises(ValueError, match="thresholds"):
        rsi_signal(pd.Series([1, 2, 3]), 2, lower, upper)


@pytest.mark.parametrize("values", [[], [1, np.nan], [1, 0], [1, np.inf]])
def test_strategy_api_rejects_bad_prices(values):
    with pytest.raises(ValueError, match="prices"):
        wilder_rsi(pd.Series(values))
