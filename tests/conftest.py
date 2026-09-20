"""Shared fixtures. Model-dependent tests use the approved model when one exists,
otherwise the latest registered candidate (the CI case: train -> eval -> test)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import BALES_PARQUET, LAYDOWNS_PARQUET  # noqa: E402

HAVE_DATA = BALES_PARQUET.exists() and LAYDOWNS_PARQUET.exists()
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="run `make data` first")


@pytest.fixture(scope="session")
def bales():
    if not HAVE_DATA:
        pytest.skip("run `make data` first")
    import pandas as pd
    return pd.read_parquet(BALES_PARQUET)


@pytest.fixture(scope="session")
def model():
    if not HAVE_DATA:
        pytest.skip("run `make data` first")
    from optimiser.common import NoApprovedModelError, load_current_model, load_model
    try:
        m = load_current_model()
    except NoApprovedModelError:
        try:
            m = load_model()
        except FileNotFoundError:
            pytest.skip("run `make train` first")
    if not getattr(m, "train_ref_", None):
        pytest.skip(f"model {m.version} predates the current QualityModel; retrain it")
    return m
