"""Command-line interface for reproducible offline runs."""

import argparse
import json
import sys

from .data import load_prices
from .engine import BacktestConfig, run_backtest
from .reporting import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditable close-only daily strategy backtest.")
    parser.add_argument("--input", required=True, help="CSV: timezone-aware timestamp,close")
    parser.add_argument("--strategy", choices=["sma", "rsi"], default="sma")
    parser.add_argument("--fast", type=int, default=5)
    parser.add_argument("--slow", type=int, default=20)
    parser.add_argument("--rsi-period", type=int, default=14)
    parser.add_argument("--rsi-lower", type=float, default=30)
    parser.add_argument("--rsi-upper", type=float, default=70)
    parser.add_argument("--initial-equity", type=float, default=10_000)
    parser.add_argument("--fee-bps", type=float, default=10)
    parser.add_argument("--slippage-bps", type=float, default=5)
    parser.add_argument("--bars-per-year", type=int, default=365)
    parser.add_argument("--annual-risk-free", type=float, default=0)
    parser.add_argument("--output", default="output/backtest",
                        help="Directory; reports are replaced")
    arguments = vars(parser.parse_args(argv))
    input_path, output = arguments.pop("input"), arguments.pop("output")
    try:
        result = run_backtest(load_prices(input_path), BacktestConfig(**arguments))
        destination = write_report(result, output)
    except (ValueError, OSError) as exc:
        print(f"backtest-lab: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(destination), "strategy": result.metrics["strategy"]},
                     indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
