"""Strict data boundary: never sort, fill gaps, or silently repair prices."""

import csv
from pathlib import Path

import numpy as np
import pandas as pd


def validate_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with UTC timestamps and float closes; reject ambiguous data.

    Each row labels one daily close at 00:00 UTC. Inputs must already be ordered
    and contain every calendar day. Explicit non-UTC offsets are converted.
    """
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("prices must be a pandas DataFrame")
    if frame.columns.duplicated().any():
        raise ValueError("duplicate column names are not allowed")
    if not {"timestamp", "close"}.issubset(frame.columns):
        raise ValueError("prices require timestamp and close columns")
    if len(frame) < 2:
        raise ValueError("at least two daily prices are required")
    timestamps = []
    for raw in frame["timestamp"]:
        try:
            stamp = pd.Timestamp(raw)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"invalid timestamp: {raw!r}") from exc
        if pd.isna(stamp) or stamp.tzinfo is None:
            raise ValueError("timestamps must be nonmissing and explicitly timezone-aware")
        timestamps.append(stamp.tz_convert("UTC"))
    index = pd.DatetimeIndex(timestamps)
    if not index.equals(index.normalize()):
        raise ValueError("daily timestamps must align to 00:00:00 UTC")
    if index.has_duplicates:
        raise ValueError("duplicate timestamps are not allowed")
    if not index.is_monotonic_increasing:
        raise ValueError("timestamps must already be in increasing order")
    if not (index[1:] - index[:-1] == pd.Timedelta(days=1)).all():
        raise ValueError("missing calendar days: daily data must have exactly 24-hour spacing")
    if frame["close"].map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError("close prices must be finite positive numbers, not booleans")
    try:
        closes = pd.to_numeric(frame["close"], errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("close prices must be numeric") from exc
    if not np.isfinite(closes).all() or (closes <= 0).any():
        raise ValueError("close prices must be finite and strictly positive")
    return pd.DataFrame({"timestamp": index, "close": closes})


def load_prices(path: str | Path) -> pd.DataFrame:
    """Read and validate a single-instrument daily CSV."""
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            # pandas skips blank/whitespace-only lines before the header.
            header = next((row for row in csv.reader(stream)
                           if row and not (len(row) == 1 and not row[0].strip())), [])
            if len(header) != len(set(header)):
                raise ValueError("duplicate column names are not allowed in CSV headers")
            stream.seek(0)
            frame = pd.read_csv(stream)
    except (
        OSError, UnicodeError, csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError,
    ) as exc:
        raise ValueError(f"cannot read prices CSV: {exc}") from exc
    return validate_prices(frame)
