# Verification record

## Initial verification — 2026-10-04

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

## Joint verification — 2026-10-07

Task reference: `c2c_a490`. The initial checkout was clean at
`813fcab22b7abc89d2bfea3a6de5e1ba4ca03fc0`. Verification used the existing Windows
virtual environment, Python 3.12.10, without dependency upgrades. This section
records local work and the completed independent ChatGPT review described below.

| Check | Actual result |
|---|---|
| Initial Git status, diff, and `git diff --check` | Clean |
| `python -m pip check` | Passed; no broken requirements |
| `ruff check .` | Passed before and after the numerical fix |
| Baseline `ruff format --check .` | Exit 1: 12 existing files would be reformatted; no bulk formatting was applied |
| Original test suite | 100 passed |
| New CAGR regressions before the fix | 2 failed, reproducing the defect |
| Metrics tests after the fix | 24 passed |
| Final full test suite | 102 passed |
| Independent acceptance checks after the fix | 11 groups passed |
| Source archive and wheel build | Passed with `python -m build` |
| SMA and RSI command-line reports | Both passed after the fix; 300 rows each |

The formatter discrepancy predates this change and is not a configured CI gate.
It is retained as an explicit unmet style check; this record does not claim
that every command passed. The formatter count was captured before the repair;
the formatter was not rerun afterward. Lint and functional verification are
separate results.

### Reproduced defect and minimal repair

The original CAGR calculation reconstructed the growth ratio from
`log1p(total_return)`. For equity declining geometrically from `1e20` to `1` over
20 intervals, the total return rounds to `-1` before the logarithm. With one
interval per year, CAGR should be `-0.9`, but it was returned as `null`. A second
case grows from `1e-200` to `1e200` over 400 intervals: the cumulative ratio
overflows even though its annualized result, `9.0` with one interval per year,
is finite.

Two parameterized cases were added to `tests/test_metrics.py` and observed to
fail before changing the implementation. `performance_metrics` now takes the
log of the growth ratio directly, falling back to the difference of endpoint
logs when the ratio itself overflows or underflows. The accounting, strategies,
dependencies, and report layout were not changed. Truly unrepresentable
annualized outputs still use JSON `null`.

### Independent numerical evidence

The separate acceptance script checks behavior using a hand fixture and a
40-digit Decimal ledger, rather than comparing only with another execution of
the vectorized implementation. A six-price fixture verifies that an entry at
150 earns neither the preceding rise to 120 nor the rise to 150, then earns the
changes through 180, 90, and the exit at 45. With 70 bps fees and 30 bps slippage,
the expected equity path is `[1000, 1000, 990, 1188, 594, 294.03]`.

For both full synthetic demonstrations, each daily net balance, each entry or
exit timestamp, and every fee/slippage amount reconciled with the independent
Decimal ledger. The SMA run has 8 fills and the RSI run has 7. Changing or
removing future observations leaves prior outputs identical for both strategies.
The checks also cover an unliquidated ending position, the final pending signal,
Wilder's initial averages and recursive step, monotonic/flat RSI, exact warmup
lengths, N−1 annualization, sample volatility, compounded risk-free Sharpe,
drawdown from initial capital, constant versus tiny real variance, extreme
finite values, UTC conversion, unordered/duplicate timestamps, missing days,
bad prices, and duplicate CSV headers with leading blank lines.

Fresh outputs are in the ignored local directory
`output/c2c-verification-20261007/`: `evidence.log` preserves command arguments,
stdout, stderr, exit codes, and timings; `summary.json` contains the same
structured evidence; `independent-checks.json` records the 11 acceptance groups;
and `sma/` and `rsi/` hold CSV, strict JSON, PNG, and SVG reports. Both PNG charts
were visually inspected: legends identify net strategy versus gross benchmark,
date/axis labels and synthetic-data text are readable, and drawdown panels are
not clipped. Tracked example reports were not overwritten.

### Hosted CI and integration boundary

The coordinating session rechecked the existing [CI run 37257692202](https://github.com/harper698/strategy-backtest-lab/actions/runs/37257692202)
on 2026-10-07: Python 3.11, 3.12, and 3.13 all passed for the initial commit
`813fcab22b7abc89d2bfea3a6de5e1ba4ca03fc0`, which also matched remote `main`.
This was a check of an existing hosted run, not a newly triggered run, and does
not validate the CAGR repair introduced during this verification on those Python versions.

After the numerical fix, the coordinating session reran the separate integration
checks. Seven synthetic ETH daily closes from the pipeline, shifted from candle
start to close observation times, produced six intervals. SMA(2,3) generated a
signal at close 24, entered at the following close 26, deducted 15 in costs, and
ended at `9985 × 30 / 26 = 11521.153846153846`, matching the independent hand
calculation. Preserving two missing BTC values made the CLI exit with code 2 and
produce no report, as required by the data contract.

A new public Coinbase acquisition also supplied 31 BTC daily closes. After the
one-day timestamp conversion, close observations span 2025-01-02 through
2025-02-01, yielding 30 intervals. The bridge produced all five report files,
finite JSON metrics, and fill timestamps exactly one day after signal timestamps;
the coordinating session also visually inspected its equity/drawdown chart.
Evidence is retained separately in
`output/c2c-integration-20261007/summary.json` and `evidence.log`. An initial
verification-script console print encountered Windows GBK encoding for a local
Chinese path; correcting that script's output encoding and rerunning succeeded.
That was a verification-tool issue, not a product defect.

### Independent final review

ChatGPT returned `STATE: DONE` for task `c2c_a490`, iteration 1, on 2026-10-07.
The reviewer read all 19 execution-evidence parts across the three repositories
and independently inspected the five changed files. The numerical repair and its
fail-before/pass-after regressions were approved; no further implementation
change was requested. The known baseline formatter failure was accepted as a
non-blocking residual, with the explicit qualification that its file count was
not remeasured after the repair. This conclusion concerns the reviewed local
changes; the baseline hosted CI result above does not cover the new repair.
