"""Multi-output gradient-boosted quality model with prediction intervals.

For each target (CSP, U%, imperfections, ends_down) we fit three LightGBM
regressors:
  * mean  (L2 objective)
  * P10   (quantile objective, alpha=0.1)
  * P90   (quantile objective, alpha=0.9)

The P10/P90 pair is the uncertainty band shown to the mixing master and used by
the optimiser as a safety margin (it can require the *P10* CSP to clear the spec
floor, not just the mean).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from config import QUALITY_TARGETS
from data.features import blend_profile, feature_columns

_BASE_PARAMS = dict(
    n_estimators=400,
    learning_rate=0.03,
    num_leaves=31,
    min_child_samples=15,
    subsample=0.9,
    colsample_bytree=0.9,
    random_state=0,
    verbose=-1,
)


@dataclass
class QualityModel:
    features: list[str] = field(default_factory=feature_columns)
    targets: list[str] = field(default_factory=lambda: list(QUALITY_TARGETS))
    mean_: dict = field(default_factory=dict)
    p10_: dict = field(default_factory=dict)
    p90_: dict = field(default_factory=dict)
    calib_k_: dict = field(default_factory=dict)   # per-target interval widening factor
    version: str = "unversioned"

    # ---- training -------------------------------------------------------
    def _fit_heads(self, X, y):
        for t in self.targets:
            self.mean_[t] = LGBMRegressor(objective="regression", **_BASE_PARAMS).fit(X, y[t])
            self.p10_[t] = LGBMRegressor(objective="quantile", alpha=0.1, **_BASE_PARAMS).fit(X, y[t])
            self.p90_[t] = LGBMRegressor(objective="quantile", alpha=0.9, **_BASE_PARAMS).fit(X, y[t])

    def fit(self, X: pd.DataFrame, y: pd.DataFrame, target_coverage: float = 0.8) -> "QualityModel":
        X = X[self.features].reset_index(drop=True)
        y = y.reset_index(drop=True)

        # split-conformal calibration of the quantile band
        n = len(X)
        rng = np.random.default_rng(0)
        cal_idx = rng.choice(n, size=max(30, n // 5), replace=False)
        fit_mask = np.ones(n, dtype=bool)
        fit_mask[cal_idx] = False

        self._fit_heads(X[fit_mask], y[fit_mask])
        Xc = X.iloc[cal_idx]
        for t in self.targets:
            mean = self.mean_[t].predict(Xc)
            half = np.maximum(self.p90_[t].predict(Xc) - self.p10_[t].predict(Xc), 1e-6) / 2.0
            resid = np.abs(y[t].to_numpy()[cal_idx] - mean)
            k = np.quantile(resid / half, target_coverage)
            self.calib_k_[t] = float(max(k, 1.0))

        # refit heads on ALL data for best point accuracy; keep calibrated k
        self._fit_heads(X, y)
        return self

    # ---- inference -----------------------------------------------------
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X[self.features]
        out = {}
        for t in self.targets:
            mean = self.mean_[t].predict(X)
            raw_lo = np.minimum(self.p10_[t].predict(X), self.p90_[t].predict(X))
            raw_hi = np.maximum(self.p10_[t].predict(X), self.p90_[t].predict(X))
            k = self.calib_k_.get(t, 1.0)
            out[f"{t}"] = mean
            out[f"{t}_p10"] = mean - k * (mean - raw_lo)
            out[f"{t}_p90"] = mean + k * (raw_hi - mean)
        return pd.DataFrame(out, index=X.index)

    def predict_blend(self, bales: pd.DataFrame, weights: np.ndarray) -> dict:
        prof = blend_profile(bales, np.asarray(weights, dtype=float))
        row = pd.DataFrame([prof], columns=self.features)
        pred = self.predict(row).iloc[0].to_dict()
        pred["_profile"] = prof
        return pred

    # ---- persistence -------------------------------------------------
    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @staticmethod
    def load(path: str | Path) -> "QualityModel":
        return joblib.load(path)
