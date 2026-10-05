# Verification record

Local validation was performed on Windows with Python 3.12.10. The checked-in CI workflow is configured for Ubuntu 24.04 and Python 3.11, 3.12, and 3.13; consult the linked GitHub Actions run for actual cloud results rather than treating workflow configuration as proof of completion.

This record covers the final local implementation. Commands are run from the repository with its virtual environment active.

| Check | Command / evidence |
|---|---|
| Behavioral and numerical tests | `pytest -q` — 100 tests passed |
| Static checks | `ruff check .` |
| Package build | `python -m build` — source archive and wheel |
| Dependency consistency | `python -m pip check` — no broken requirements |
| SMA report | `backtest-lab --input examples/prices.csv --strategy sma --output examples/demo-output/sma` |
| RSI report | `backtest-lab --input examples/prices.csv --strategy rsi --output examples/demo-output/rsi` |

Tests independently hand-calculate signal lag, entry/exit cost timing, net equity, CAGR interval count, sample volatility, compounded risk-free Sharpe, and maximum drawdown. Future-price perturbation and prefix-truncation tests cover both strategies. Additional tests cover Wilder initialization, flat/monotonic prices, duplicate CSV headers, timezone normalization, gaps, missing/nonfinite prices, invalid parameters, CLI exit behavior, strict JSON, and extreme numeric magnitudes.

An independent review identified and corrected duplicate-header mangling, extreme-price RSI overflow, cost multiplication overflow, impractically large annualization values, and roundoff-only variance producing an artificial Sharpe ratio. Regression cases are retained in the test suite.

## Companion pipeline integration

A separate local smoke run consumed 31 real BTC-USD daily closes from the companion Market Data Pipeline's `output/live/closes.csv`. The bridge selected BTC-USD, renamed it `close`, and shifted the Coinbase candle-start timestamps by one day to the close observation convention. SMA(5,20), 10 bps fees, and 5 bps slippage produced a valid report with 31 rows and 30 return intervals. PNG layout, legends, and drawdown axes were visually inspected. No additional network request was made by the backtester. The real-price local output is excluded from version control; checked-in demonstration reports use synthetic prices only.

This is an execution and software-validation record, not investment-performance verification.
