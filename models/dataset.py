"""Build the (features, targets) training frame from historical laydowns."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from config import (BALES_PARQUET, LAYDOWNS_PARQUET, QUALITY_TARGETS,
                    RANDOM_SEED)
from data.features import blend_profile, feature_columns


def load_bales() -> pd.DataFrame:
    return pd.read_parquet(BALES_PARQUET)


def load_laydowns() -> pd.DataFrame:
    return pd.read_parquet(LAYDOWNS_PARQUET)


def laydown_profile(bales_by_id: dict, bale_ids, weights) -> dict:
    sub = pd.DataFrame([bales_by_id[b] for b in bale_ids])
    return blend_profile(sub, np.asarray(weights, dtype=float))


def build_xy(laydowns: pd.DataFrame | None = None,
             bales: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    bales = load_bales() if bales is None else bales
    laydowns = load_laydowns() if laydowns is None else laydowns
    bales_by_id = bales.set_index("bale_id").to_dict("index")

    feats = []
    for row in laydowns.itertuples(index=False):
        feats.append(laydown_profile(bales_by_id, row.bale_ids, row.weights))
    X = pd.DataFrame(feats, columns=feature_columns())
    y = laydowns[[f"actual_{t}" for t in QUALITY_TARGETS]].copy()
    y.columns = QUALITY_TARGETS
    return X, y


def train_test_split_by_time(laydowns: pd.DataFrame, test_frac: float = 0.2):
    """Chronological split -- newer laydowns are the test set (realistic)."""
    ld = laydowns.sort_values("date").reset_index(drop=True)
    cut = int(len(ld) * (1 - test_frac))
    return ld.iloc[:cut].copy(), ld.iloc[cut:].copy()


def data_hash(*frames: pd.DataFrame) -> str:
    h = hashlib.sha256()
    for f in frames:
        h.update(f.to_json(orient="records").encode())
    return h.hexdigest()[:16]
