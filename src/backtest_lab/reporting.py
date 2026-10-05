"""Inspectable CSV/JSON evidence and static charts; no network calls."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

from .engine import BacktestResult  # noqa: E402


def write_report(result: BacktestResult, directory: str | Path) -> Path:
    """Write a report directory. Existing report filenames are replaced."""
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    result.equity.to_csv(destination / "equity.csv", index=False, float_format="%.10g")
    result.trades.to_csv(destination / "trades.csv", index=False, float_format="%.10g")
    (destination / "metrics.json").write_text(
        json.dumps(result.metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10,
                         "svg.hashsalt": "strategy-backtest-lab"}):
        figure, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [2.5, 1]})
        frame = result.equity
        axes[0].plot(frame["timestamp"], frame["equity"], color="#116466", lw=2,
                     label="Strategy (after fees + slippage)")
        axes[0].plot(frame["timestamp"], frame["benchmark_gross_equity"], color="#8c95a1",
                     lw=1.5, label="Buy & hold (gross, no costs)")
        axes[0].set_ylabel("Equity (input currency units)")
        axes[0].legend(loc="upper left", frameon=False)
        axes[0].set_title(
            f"{result.metrics['config']['strategy'].upper()} | next-close execution",
            loc="left", fontweight="bold", pad=14,
        )
        axes[1].fill_between(frame["timestamp"], frame["drawdown"], 0,
                             color="#ce6b50", alpha=0.3)
        axes[1].plot(frame["timestamp"], frame["drawdown"], color="#b65238", lw=1)
        axes[1].yaxis.set_major_formatter(PercentFormatter(1))
        axes[1].set_ylabel("Strategy drawdown")
        for axis in axes:
            axis.grid(alpha=0.15)
            axis.spines[["top", "right"]].set_visible(False)
        figure.text(0.08, 0.015,
                    "Simulation only. Input provenance determines interpretation; "
                    "the bundled example is synthetic.", fontsize=9, color="#555555")
        figure.tight_layout(rect=(0, 0.05, 1, 1))
        figure.savefig(destination / "equity.png", dpi=160)
        figure.savefig(destination / "equity.svg", metadata={"Date": None})
        plt.close(figure)
    return destination.resolve()
