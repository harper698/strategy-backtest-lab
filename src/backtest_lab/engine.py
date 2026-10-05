"""A next-close, long-only simulator; positions refer to holdings after fills."""

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .data import validate_prices
from .metrics import performance_metrics, validate_annualization
from .strategies import rsi_signal, sma_signal, wilder_rsi


@dataclass(frozen=True)
class BacktestConfig:
    strategy: str = "sma"
    fast: int = 5
    slow: int = 20
    rsi_period: int = 14
    rsi_lower: float = 30.0
    rsi_upper: float = 70.0
    initial_equity: float = 10_000.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    bars_per_year: int = 365
    annual_risk_free: float = 0.0

    def validate(self) -> None:
        if self.strategy not in {"sma", "rsi"}:
            raise ValueError("strategy must be sma or rsi")
        if not math.isfinite(self.initial_equity) or self.initial_equity <= 0:
            raise ValueError("initial_equity must be finite and positive")
        if not all(math.isfinite(v) and v >= 0 for v in (self.fee_bps, self.slippage_bps)):
            raise ValueError("fee_bps and slippage_bps must be finite and nonnegative")
        if self.fee_bps + self.slippage_bps >= 10_000:
            raise ValueError("combined fee and slippage must be below 10000 bps per side")
        validate_annualization(self.bars_per_year, self.annual_risk_free)


@dataclass
class BacktestResult:
    equity: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, Any]


def run_backtest(prices: pd.DataFrame, config: BacktestConfig | None = None) -> BacktestResult:
    """Run without mutating inputs. No leverage, shorting, or terminal liquidation."""
    config = config or BacktestConfig()
    config.validate()
    frame = validate_prices(prices)
    close = frame["close"]
    if config.strategy == "sma":
        target = sma_signal(close, config.fast, config.slow)
        minimum = config.slow + 2
        frame["fast_sma"] = close.rolling(config.fast).mean()
        frame["slow_sma"] = close.rolling(config.slow).mean()
    else:
        target = rsi_signal(close, config.rsi_period, config.rsi_lower, config.rsi_upper)
        minimum = config.rsi_period + 2
        frame["rsi"] = wilder_rsi(close, config.rsi_period)
    if len(frame) < minimum:
        raise ValueError(f"{config.strategy} requires at least {minimum} daily prices for warmup")

    # A target produced at close t fills at close t+1. Only the holdings already
    # present after close t-1 earn the price change ending at close t.
    frame["target_signal"] = target
    frame["position"] = target.shift(1, fill_value=0).astype(int)
    previous_position = frame["position"].shift(1, fill_value=0)
    frame["price_return"] = close.pct_change(fill_method=None).fillna(0)
    frame["gross_return"] = previous_position * frame["price_return"]
    turnover = (frame["position"] - previous_position).abs()
    frame["turnover"] = turnover
    frame["cost_fraction"] = turnover * (config.fee_bps + config.slippage_bps) / 10_000
    gross_factor = 1 + frame["gross_return"]
    frame["net_return"] = gross_factor * (1 - frame["cost_fraction"]) - 1
    frame["equity"] = config.initial_equity * (1 + frame["net_return"]).cumprod()
    frame["benchmark_gross_equity"] = config.initial_equity * (close / close.iloc[0])
    numeric = frame[["equity", "net_return", "benchmark_gross_equity"]].to_numpy()
    if not np.isfinite(numeric).all() or (frame["equity"] <= 0).any():
        raise ValueError("price magnitudes cause numeric overflow or equity underflow")
    before_cost = frame["equity"].shift(1, fill_value=config.initial_equity) * gross_factor
    frame["fee_cost"] = before_cost * turnover * (config.fee_bps / 10_000)
    frame["slippage_cost"] = before_cost * turnover * (config.slippage_bps / 10_000)
    cost_totals = frame[["fee_cost", "slippage_cost"]].sum()
    if not np.isfinite(frame[["fee_cost", "slippage_cost"]]).all().all() or not (
        np.isfinite(cost_totals).all()
    ):
        raise ValueError("price magnitudes cause transaction cost numeric overflow")
    frame["drawdown"] = frame["equity"] / frame["equity"].cummax() - 1
    fills = frame.loc[turnover > 0, [
        "timestamp", "close", "position", "fee_cost", "slippage_cost", "equity",
    ]].copy()
    fills.insert(1, "action", np.where(fills["position"] == 1, "BUY", "SELL"))
    fills.insert(1, "signal_timestamp", frame["timestamp"].shift(1).loc[turnover > 0])
    fills = fills.rename(columns={"close": "reference_close", "equity": "equity_after_fill"})
    metrics: dict[str, Any] = {
        "schema_version": 1,
        "config": asdict(config),
        "execution_model": "signal_at_close_t_fill_at_close_t_plus_1",
        "terminal_liquidation": False,
        "data": {
            "start": frame["timestamp"].iloc[0].isoformat(),
            "end": frame["timestamp"].iloc[-1].isoformat(),
            "rows": len(frame),
            "calendar": "every_calendar_day_00:00_UTC",
        },
        "strategy": performance_metrics(frame["equity"], config.bars_per_year,
                                         config.annual_risk_free),
        "benchmark_gross_buy_and_hold": performance_metrics(
            frame["benchmark_gross_equity"], config.bars_per_year, config.annual_risk_free,
        ),
        "fills": len(fills),
        "entries": int((fills["action"] == "BUY").sum()),
        "exits": int((fills["action"] == "SELL").sum()),
        "ending_position": int(frame["position"].iloc[-1]),
        "final_target_signal": int(target.iloc[-1]),
        "final_signal_requires_future_fill": bool(target.iloc[-1] != frame["position"].iloc[-1]),
        "total_fee_cost": float(frame["fee_cost"].sum()),
        "total_slippage_cost": float(frame["slippage_cost"].sum()),
        "final_equity": float(frame["equity"].iloc[-1]),
    }
    return BacktestResult(frame, fills.reset_index(drop=True), metrics)
