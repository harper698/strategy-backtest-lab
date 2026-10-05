import numpy as np
import pandas as pd
import pytest

from backtest_lab import load_prices, validate_prices


def test_validation_copies_and_normalizes_offset(prices):
    original = prices([100, 101])
    original["timestamp"] = ["2024-12-31T19:00:00-05:00", "2025-01-01T19:00:00-05:00"]
    result = validate_prices(original)
    assert str(result["timestamp"].dtype) == "datetime64[ns, UTC]"
    assert result["timestamp"].iloc[0] == pd.Timestamp("2025-01-01T00:00:00Z")
    result.loc[0, "close"] = 9
    assert original.loc[0, "close"] == 100


@pytest.mark.parametrize("value", [0, -1, np.nan, np.inf, -np.inf, "bad", True, None])
def test_bad_closes_rejected(prices, value):
    frame = prices([100, value])
    with pytest.raises(ValueError, match="close"):
        validate_prices(frame)


@pytest.mark.parametrize("timestamps, message", [
    (["2025-01-01", "2025-01-02"], "timezone"),
    (["invalid", "2025-01-02T00:00:00Z"], "timestamp"),
    ([None, "2025-01-02T00:00:00Z"], "timestamp"),
    (["2025-01-01T01:00:00Z", "2025-01-02T01:00:00Z"], "00:00"),
    (["2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z"], "duplicate"),
    (["2025-01-02T00:00:00Z", "2025-01-01T00:00:00Z"], "increasing"),
    (["2025-01-01T00:00:00Z", "2025-01-03T00:00:00Z"], "missing calendar"),
])
def test_bad_time_axis_rejected(prices, timestamps, message):
    frame = prices([100, 101])
    frame["timestamp"] = timestamps
    with pytest.raises(ValueError, match=message):
        validate_prices(frame)


def test_duplicates_after_timezone_conversion_rejected(prices):
    frame = prices([100, 101])
    frame["timestamp"] = ["2025-01-01T00:00:00Z", "2024-12-31T19:00:00-05:00"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_prices(frame)


@pytest.mark.parametrize("frame", [pd.DataFrame(), pd.DataFrame({"close": [1, 2]}), [1, 2]])
def test_missing_schema_rejected(frame):
    with pytest.raises(ValueError):
        validate_prices(frame)


def test_one_row_rejected(prices):
    with pytest.raises(ValueError, match="at least two"):
        validate_prices(prices([1]))


def test_duplicate_columns_rejected(prices):
    frame = prices([1, 2])
    frame = pd.concat([frame, frame[["close"]]], axis=1)
    with pytest.raises(ValueError, match="duplicate column"):
        validate_prices(frame)


def test_csv_roundtrip_and_missing_file(prices, tmp_path):
    path = tmp_path / "prices.csv"
    prices([10, 11]).to_csv(path, index=False)
    pd.testing.assert_frame_equal(load_prices(path), validate_prices(prices([10, 11])))
    with pytest.raises(ValueError, match="cannot read"):
        load_prices(tmp_path / "missing.csv")


def test_empty_file_rejected(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(ValueError, match="cannot read"):
        load_prices(path)


@pytest.mark.parametrize("prefix", ["", "\n", "   \n", "\n\t\n"])
def test_duplicate_csv_header_rejected_before_pandas_renames_it(tmp_path, prefix):
    path = tmp_path / "duplicate.csv"
    path.write_text(prefix + "timestamp,close,close\n"
                    "2025-01-01T00:00:00Z,1,2\n2025-01-02T00:00:00Z,2,3\n")
    with pytest.raises(ValueError, match="duplicate column"):
        load_prices(path)
