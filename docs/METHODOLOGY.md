# Execution and metric specification

## Calendar and state

One instrument, one close observation each UTC calendar day. Every timestamp must explicitly include a timezone and normalize to 00:00 UTC. The engine rejects gaps, repeated or unordered observations, nonpositive/nonfinite closes, and ambiguous duplicate CSV headers. It never sorts, fills, or adjusts prices. Corporate actions and exchange session calendars require an upstream model and are unsupported here.

Let close prices be `C[t]`, target signals `s[t] ∈ {0,1}`, and the actual position **after** the close fill be `p[t]`. The initial position is flat. No borrowing, shorts, leverage, cash interest, fractional-unit rounding, or final liquidation is modeled.

```text
p[t] = s[t-1], with out-of-range signal values treated as 0
q[t] = C[t] / C[t-1] - 1, with q[0] = 0
g[t] = p[t-1] × q[t]
turnover[t] = abs(p[t] - p[t-1])
c[t] = turnover[t] × (fee_bps + slippage_bps) / 10000
n[t] = (1 + g[t]) × (1 - c[t]) - 1
E[0] = initial_equity
E[t] = E[t-1] × (1 + n[t])
```

This is **next-close execution**: a signal at close t does not earn the return ending at t or t+1. Its fill occurs at t+1; its first possible return ends at t+2. A sell fill still earns the interval return up to that close, then pays exit costs.

Cost amounts are `E[t-1] × (1+g[t]) × turnover[t] × rate_per_side`. Fees and slippage are separate proportional deductions from equity before the fill's costs. Slippage is an approximation, not a simulated execution-price adjustment. At entry, remaining capital becomes a fractional instrument holding; at exit, remaining capital becomes cash. The sum of fee and slippage must be less than 10000 basis points per side.

The last signal is recorded but has no future close at which to fill. `final_signal_requires_future_fill` indicates whether it requests a position change from the ending position. Open positions are marked at the final observed close with **no hypothetical liquidation fee**. `entries` and `exits` count BUY and SELL fills; no win-rate statistic is provided.

## Strategies

**SMA:** require integer `1 ≤ fast < slow`. Target 1 when the trailing fast simple average is strictly greater than the trailing slow average; otherwise 0. Full windows are required, so the first possible signal index is `slow-1`. The engine requires at least `slow+2` prices, allowing an initial signal to fill and one subsequent interval to exist.

**Wilder RSI:** calculate price changes, gains `max(change,0)`, and losses `max(-change,0)`. The first RSI occurs at index `period`, using the simple mean of the first `period` changes. Subsequent averages follow:

```text
avg_gain[t] = (1 - 1/period) × avg_gain[t-1] + gain[t]/period
avg_loss[t] = (1 - 1/period) × avg_loss[t-1] + loss[t]/period
RSI = 100 × avg_gain / (avg_gain + avg_loss)
```

Implementation rescales the ratio to avoid overflowing large finite magnitudes. With zero average loss and positive gains RSI is 100; with zero gain and positive losses it is 0; when both are zero it is 50. Leading warmup values are undefined (`NaN` in the indicator column, blank in CSV), and the target remains flat.

Target enters when RSI is strictly below `lower`, exits when strictly above `upper`, and persists between thresholds or at equality. Require `0 < lower < upper < 100`. The engine requires at least `period+2` prices, allowing the first RSI signal to fill; that last fill may not yet have a subsequent return interval.

## Performance

Metrics use all N equity rows, including initial capital in row 0. The number of return intervals is `M = N - 1`; the initial zero-return placeholder is excluded. Default annualization `B = 365`; `--bars-per-year` accepts integers 1 through 1000000 and affects annualization only. It cannot enable a different market calendar.

```text
returns = E[1:] / E[:-1] - 1
total_return = E[-1] / E[0] - 1
CAGR = (E[-1] / E[0]) ** (B / M) - 1
annualized_volatility = sample_std(returns, ddof=1) × sqrt(B)
risk_free_per_bar = (1 + annual_risk_free) ** (1/B) - 1
Sharpe = mean(returns - risk_free_per_bar) / sample_std(returns, ddof=1) × sqrt(B)
drawdown[t] = E[t] / max(E[:t+1]) - 1
max_drawdown = min(drawdown)
```

Returns, CAGR, volatility, and drawdown are fractions, not percentages; Sharpe is dimensionless. Maximum drawdown is nonpositive. Including initial equity ensures a first loss is measured against starting capital. With fewer than two return intervals, sample volatility and Sharpe are `null`. With zero variance, volatility is 0 and Sharpe is `null`. Floating-point standard deviation at or below `4 × machine_epsilon × max(1, max(abs(returns)))` is treated as zero to avoid spurious enormous Sharpe values for mathematically constant returns. Tests preserve small real variance above that tolerance.

An annualized result outside finite floating-point range becomes `null`, never JSON `NaN`/`Infinity`. An unrepresentable execution ledger or transaction cost causes a validation error. All meaningful strategy signals and filled positions remain finite. Annual risk-free rate must be finite and greater than -1; it is used in Sharpe only, while actual cash interest stays zero.

These formulas assume equally spaced calendar-daily observations and conventional square-root-of-time volatility scaling. They do not correct autocorrelation or estimate statistical significance. Warmup remains part of the observation horizon; the initial flat period is not removed to improve metrics.

## Benchmark

```text
gross_buy_and_hold_equity[t] = initial_equity × C[t] / C[0]
```

The benchmark holds from the first price, including the strategy's warmup. It excludes trading costs and uses the same metric formulas. It is named `benchmark_gross_buy_and_hold` in JSON and clearly labeled on the chart. Differences from the strategy include both exposure timing and costs; it is a descriptive reference, not a like-for-like cost comparison.

## Synthetic example provenance

`scripts/make_example.py` generates 300 UTC daily closes beginning 2025-01-01, rounded to eight decimal places:

```text
close[i] = 100 × exp(0.0006 × i + 0.12 × sin(i/13) + 0.035 × sin(i/4))
```

This deterministic oscillating series exists to exercise signals and accounting, not to estimate live profitability or validate the economic merits of either strategy. Chart output may differ across plotting-library versions; the source data and numerical logic are inspectable.
