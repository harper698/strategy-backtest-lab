"""Transparent, close-only strategy simulations for calendar-daily data."""

from .data import load_prices, validate_prices
from .engine import BacktestConfig, BacktestResult, run_backtest
from .metrics import performance_metrics
from .strategies import rsi_signal, sma_signal, wilder_rsi

__all__ = [
    "BacktestConfig", "BacktestResult", "load_prices", "performance_metrics",
    "rsi_signal", "run_backtest", "sma_signal", "validate_prices", "wilder_rsi",
]
