import pandas as pd
import pytest

from app import config


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))


@pytest.fixture
def prices():
    return pd.Series([100 + i * 0.5 + (i % 7) for i in range(300)], dtype=float)
