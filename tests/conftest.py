import pandas as pd
import pytest


@pytest.fixture
def prices():
    def make(values):
        return pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=len(values), freq="D", tz="UTC"),
            "close": values,
        })
    return make
