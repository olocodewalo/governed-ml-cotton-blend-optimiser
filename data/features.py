"""Turn a bale laydown (bales + weights) into the blend-aggregate feature vector.

Used identically by:
  * the synthetic generator (to label historical laydowns),
  * the ML quality model (features -> quality),
  * both optimisers (candidate blend -> features -> predicted quality).

Keeping it in one place guarantees train/serve parity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import FIBRE_PROPS, ORIGINS

# Properties whose weighted VARIANCE across the blend matters physically.
VARIANCE_PROPS = ["micronaire", "short_fibre_content_pct"]


def _weighted_mean(values: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(values * w))


def _weighted_var(values: np.ndarray, w: np.ndarray) -> float:
    m = np.sum(values * w)
    return float(np.sum(w * (values - m) ** 2))


def blend_profile(bales: pd.DataFrame, weights: np.ndarray) -> dict:
    """Aggregate fibre profile of a blend.

    Parameters
    ----------
    bales : DataFrame with columns FIBRE_PROPS + 'origin' (one row per bale)
    weights : array of non-negative weights, same length as ``bales``; normalised
        internally to sum to 1.

    Returns
    -------
    dict with keys:
        w_mean_<prop> for every prop in FIBRE_PROPS
        w_var_<prop>  for every prop in VARIANCE_PROPS
        origin_frac_<origin> for every origin in ORIGINS
        n_bales_effective (inverse Herfindahl -- how spread the blend is)
    """
    w = np.asarray(weights, dtype=float)
    if w.sum() <= 0:
        raise ValueError("weights sum to zero")
    w = w / w.sum()

    prof: dict = {}
    for p in FIBRE_PROPS:
        vals = bales[p].to_numpy(dtype=float)
        prof[f"w_mean_{p}"] = _weighted_mean(vals, w)
    for p in VARIANCE_PROPS:
        vals = bales[p].to_numpy(dtype=float)
        prof[f"w_var_{p}"] = _weighted_var(vals, w)

    origin = bales["origin"].to_numpy()
    for o in ORIGINS:
        prof[f"origin_frac_{o}"] = float(w[origin == o].sum())

    prof["n_bales_effective"] = float(1.0 / np.sum(w ** 2))
    return prof


def feature_columns() -> list[str]:
    cols = [f"w_mean_{p}" for p in FIBRE_PROPS]
    cols += [f"w_var_{p}" for p in VARIANCE_PROPS]
    cols += [f"origin_frac_{o}" for o in ORIGINS]
    cols += ["n_bales_effective"]
    return cols


def profiles_to_frame(profiles: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(profiles, columns=feature_columns())
