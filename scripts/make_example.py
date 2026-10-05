"""Rebuild the synthetic example without network access or randomness."""

import csv
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

destination = Path(__file__).resolve().parents[1] / "examples" / "prices.csv"
destination.parent.mkdir(parents=True, exist_ok=True)
start = datetime(2025, 1, 1, tzinfo=UTC)
with destination.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["timestamp", "close"])
    for i in range(300):
        price = 100 * math.exp(0.0006 * i + 0.12 * math.sin(i / 13) + 0.035 * math.sin(i / 4))
        writer.writerow([(start + timedelta(days=i)).isoformat(), f"{price:.8f}"])
print(destination)
