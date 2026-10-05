import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from backtest_lab import BacktestConfig, run_backtest


def test_close_t_signal_next_close_fill_and_costs(prices):
    # SMA(1,2) targets [0,1,1,0,0]; entry at 121, exit at 98.01.
    # Entry bar earns no price return, and the exit bar still earns -10%.
    frame = prices([100, 110, 121, 108.9, 98.01])
    result = run_backtest(frame, BacktestConfig(fast=1, slow=2, initial_equity=100,
                                               fee_bps=100, slippage_bps=100))
    assert result.equity["target_signal"].tolist() == [0, 1, 1, 0, 0]
    assert result.equity["position"].tolist() == [0, 0, 1, 1, 0]
    assert result.equity["gross_return"].tolist() == pytest.approx([0, 0, 0, -0.1, -0.1])
    expected = [100, 100, 98, 88.2, 77.7924]
    assert result.equity["equity"].tolist() == pytest.approx(expected)
    assert result.metrics["final_equity"] == pytest.approx(100 * 0.98 * 0.9 * 0.9 * 0.98)
    assert result.metrics["entries"] == result.metrics["exits"] == 1
    assert result.metrics["fills"] == 2
    assert result.trades["action"].tolist() == ["BUY", "SELL"]
    assert result.trades["signal_timestamp"].tolist() == frame.loc[[1, 3], "timestamp"].tolist()
    assert result.trades["timestamp"].tolist() == frame.loc[[2, 4], "timestamp"].tolist()
    assert result.trades["fee_cost"].tolist() == pytest.approx([1, 0.7938])
    assert result.trades["slippage_cost"].tolist() == pytest.approx([1, 0.7938])
    assert result.metrics["benchmark_gross_buy_and_hold"]["total_return"] == pytest.approx(-0.0199)
    assert result.metrics["strategy"]["max_drawdown"] == pytest.approx(-0.222076)
    pd.testing.assert_frame_equal(frame, prices([100, 110, 121, 108.9, 98.01]))


def test_no_terminal_liquidation_and_last_signal_pending(prices):
    result = run_backtest(prices([10, 11, 12, 9]), BacktestConfig(fast=1, slow=2,
                                                               fee_bps=0, slippage_bps=0))
    assert result.metrics["ending_position"] == 1
    assert result.metrics["final_target_signal"] == 0
    assert result.metrics["final_signal_requires_future_fill"]
    assert result.metrics["entries"] == 1
    assert result.metrics["exits"] == 0
    assert result.metrics["final_equity"] == pytest.approx(7500)


@pytest.mark.parametrize("strategy", ["sma", "rsi"])
def test_future_prices_cannot_change_prefix(prices, strategy):
    values = 100 + np.arange(90) / 5 + 8 * np.sin(np.arange(90) / 3)
    original = prices(values)
    changed = original.copy()
    changed.loc[60:, "close"] *= np.linspace(3, 0.3, 30)
    config = BacktestConfig(strategy=strategy, fast=3, slow=8, rsi_period=5)
    base = run_backtest(original, config)
    altered = run_backtest(changed, config)
    prefix = run_backtest(original.iloc[:60], config)
    pd.testing.assert_frame_equal(base.equity.iloc[:60], altered.equity.iloc[:60])
    pd.testing.assert_frame_equal(base.equity.iloc[:60].reset_index(drop=True), prefix.equity)
    assert base.equity.loc[60, "position"] == altered.equity.loc[60, "position"]


@pytest.mark.parametrize("strategy", ["sma", "rsi"])
def test_flat_prices_produce_no_trades_and_safe_metrics(prices, strategy):
    result = run_backtest(prices([100] * 30), BacktestConfig(strategy=strategy))
    assert result.trades.empty
    assert result.metrics["fills"] == 0
    assert result.metrics["strategy"]["total_return"] == 0
    assert result.metrics["strategy"]["sharpe_ratio"] is None
    assert result.equity["equity"].eq(10000).all()
    json.dumps(result.metrics, allow_nan=False)


@pytest.mark.parametrize("change", [
    {"fee_bps": -1}, {"slippage_bps": -1}, {"fee_bps": np.inf},
    {"slippage_bps": np.nan}, {"fee_bps": 6000, "slippage_bps": 4000},
    {"initial_equity": 0}, {"initial_equity": np.inf}, {"strategy": "magic"},
    {"bars_per_year": True}, {"annual_risk_free": -1},
])
def test_bad_configuration_rejected(prices, change):
    with pytest.raises(ValueError):
        run_backtest(prices([100] * 30), replace(BacktestConfig(), **change))


@pytest.mark.parametrize("strategy, length", [("sma", 21), ("rsi", 15)])
def test_insufficient_warmup_rejected(prices, strategy, length):
    with pytest.raises(ValueError, match="warmup"):
        run_backtest(prices([100] * length), BacktestConfig(strategy=strategy))


def test_overflow_rejected(prices):
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        with pytest.raises(ValueError, match="overflow|underflow"):
            run_backtest(prices([1e-308, 1e308, 1e308, 1e308]), BacktestConfig(fast=1, slow=2))


def test_fee_fraction_is_applied_before_large_equity_multiplication(prices):
    result = run_backtest(prices([0.1, 0.2, 0.3, 0.4]), BacktestConfig(
        fast=1, slow=2, initial_equity=1e307, fee_bps=50, slippage_bps=0,
    ))
    assert result.metrics["total_fee_cost"] == pytest.approx(5e304)
    json.dumps(result.metrics, allow_nan=False)
