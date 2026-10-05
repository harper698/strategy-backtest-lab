import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from backtest_lab.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "prices.csv"


@pytest.mark.parametrize("strategy", ["sma", "rsi"])
def test_cli_outputs_inspectable_report(tmp_path, strategy):
    directory = tmp_path / strategy
    assert main(["--input", str(EXAMPLE), "--strategy", strategy,
                 "--output", str(directory)]) == 0
    metrics = json.loads((directory / "metrics.json").read_text())
    equity = pd.read_csv(directory / "equity.csv")
    fills = pd.read_csv(directory / "trades.csv")
    assert metrics["data"]["rows"] == len(equity) == 300
    assert metrics["fills"] == len(fills)
    assert (directory / "equity.png").read_bytes().startswith(b"\x89PNG")
    assert "<svg" in (directory / "equity.svg").read_text(encoding="utf-8")
    json.dumps(metrics, allow_nan=False)


def test_module_cli_is_runnable():
    process = subprocess.run([sys.executable, "-m", "backtest_lab.cli", "--help"],
                             capture_output=True, text=True, check=False)
    assert process.returncode == 0
    assert "--fee-bps" in process.stdout


def test_cli_invalid_input_has_clear_exit_code(tmp_path, capsys):
    assert main(["--input", str(tmp_path / "missing.csv")]) == 2
    assert "cannot read prices CSV" in capsys.readouterr().err


def test_cli_invalid_config_does_not_write_report(tmp_path, capsys):
    report = tmp_path / "bad"
    assert main(["--input", str(EXAMPLE), "--fee-bps", "-1", "--output", str(report)]) == 2
    assert "nonnegative" in capsys.readouterr().err
    assert not report.exists()
