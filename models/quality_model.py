"""Multi-output gradient-boosted quality model with prediction intervals.

For each target (CSP, U%, imperfections, ends_down) we fit three LightGBM
regressors:
  * mean  (L2 objective)
  * P10   (quantile objective, alpha=0.1)
  * P90   (quantile objective, alpha=0.9)

The P10/P90 pair is the uncertainty band shown to the mixing master and used by
the optimiser as a safety margin (it can require the *P10* CSP to clear the spec
floor, not just the mean).

Raw quantile heads on ~400 laydowns over-fit and come out too narrow, so the
band is calibrated with 5-fold cross-conformalized quantile regression (CQR,
Romano et al. 2019): out-of-fold conformity scores ``max(lo - y, y - hi)`` give
an additive widening per target, with the finite-sample quantile correction.

The model also carries a snapshot of its training feature distribution, used
for the out-of-support check (confidence policy) and PSI drift monitoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.model_selection import KFold
from sklearn.neighbors import NearestNeighbors

from config import PSI_BINS, QUALITY_TARGETS, SUPPORT_KNN_K, SUPPORT_QUANTILE
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

CALIBRATION_FOLDS = 5


@dataclass
class QualityModel:
    features: list[str] = field(default_factory=feature_columns)
    targets: list[str] = field(default_factory=lambda: list(QUALITY_TARGETS))
    mean_: dict = field(default_factory=dict)
    p10_: dict = field(default_factory=dict)
    p90_: dict = field(default_factory=dict)
    calib_q_: dict = field(default_factory=dict)   # per-target additive CQR widening
    train_ref_: dict = field(default_factory=dict)  # training distribution snapshot
    version: str = "unversioned"

    # ---- training -------------------------------------------------------
    def _fit_heads(self, X, y):
        for t in self.targets:
            self.mean_[t] = LGBMRegressor(objective="regression", **_BASE_PARAMS).fit(X, y[t])
            self.p10_[t] = LGBMRegressor(objective="quantile", alpha=0.1, **_BASE_PARAMS).fit(X, y[t])
            self.p90_[t] = LGBMRegressor(objective="quantile", alpha=0.9, **_BASE_PARAMS).fit(X, y[t])

    def _raw_band(self, X, t):
        a, b = self.p10_[t].predict(X), self.p90_[t].predict(X)
        return np.minimum(a, b), np.maximum(a, b)

    def fit(self, X: pd.DataFrame, y: pd.DataFrame, target_coverage: float = 0.8) -> "QualityModel":
        X = X[self.features].reset_index(drop=True)
        y = y.reset_index(drop=True)
        n = len(X)

        # cross-conformal calibration: out-of-fold conformity scores per target
        scores = {t: np.zeros(n) for t in self.targets}
        folds = KFold(CALIBRATION_FOLDS, shuffle=True, random_state=0)
        for fit_idx, cal_idx in folds.split(X):
            fold = QualityModel(features=self.features, targets=self.targets)
            fold._fit_heads(X.iloc[fit_idx], y.iloc[fit_idx])
            Xc = X.iloc[cal_idx]
            for t in self.targets:
                lo, hi = fold._raw_band(Xc, t)
                yt = y[t].to_numpy()[cal_idx]
                scores[t][cal_idx] = np.maximum(lo - yt, yt - hi)
        level = min(1.0, np.ceil((n + 1) * target_coverage) / n)
        self.calib_q_ = {t: float(np.quantile(scores[t], level)) for t in self.targets}

        # refit heads on ALL data for best point accuracy; keep calibrated widening
        self._fit_heads(X, y)
        self.train_ref_ = _training_reference(X)
        return self

    # ---- inference -----------------------------------------------------
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X[self.features]
        out = {}
        for t in self.targets:
            mean = self.mean_[t].predict(X)
            lo, hi = self._raw_band(X, t)
            q = self.calib_q_.get(t, 0.0)
            out[f"{t}"] = mean
            # the mean always sits inside its own band
            out[f"{t}_p10"] = np.minimum(lo - q, mean)
            out[f"{t}_p90"] = np.maximum(hi + q, mean)
        return pd.DataFrame(out, index=X.index)

    def predict_blend(self, bales: pd.DataFrame, weights: np.ndarray) -> dict:
        prof = blend_profile(bales, np.asarray(weights, dtype=float))
        row = pd.DataFrame([prof], columns=self.features)
        pred = self.predict(row).iloc[0].to_dict()
        pred["_profile"] = prof
        return pred

    # ---- training support ----------------------------------------------
    def support_ratio(self, X: pd.DataFrame) -> np.ndarray:
        """Mean kNN distance to the training blends (standardised features), as a
        multiple of the training set's own ``SUPPORT_QUANTILE`` kNN distance.
        <= 1 means the blend looks like something the model was trained on."""
        ref = self.train_ref_
        if not ref:
            raise RuntimeError(f"model {self.version} has no training reference; retrain it")
        Z = ((X[self.features] - ref["mu"]) / ref["sd"]).to_numpy()
        nn = NearestNeighbors(n_neighbors=ref["k"]).fit(ref["Z"])
        d, _ = nn.kneighbors(Z)
        return d.mean(axis=1) / ref["threshold"]

    # ---- persistence -------------------------------------------------
    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @staticmethod
    def load(path: str | Path) -> "QualityModel":
        return joblib.load(path)


def _training_reference(X: pd.DataFrame) -> dict:
    mu = X.mean()
    sd = X.std().replace(0.0, 1.0)
    Z = ((X - mu) / sd).to_numpy()
    k = min(SUPPORT_KNN_K, len(X) - 1)
    d, _ = NearestNeighbors(n_neighbors=k + 1).fit(Z).kneighbors(Z)
    self_excluded = d[:, 1:].mean(axis=1)
    bins = {}
    for c in X.columns:
        edges = np.unique(np.quantile(X[c], np.linspace(0, 1, PSI_BINS + 1)))
        counts, _ = np.histogram(np.clip(X[c], edges[0], edges[-1]), bins=edges)
        bins[c] = dict(edges=edges, props=counts / counts.sum())
    return dict(mu=mu, sd=sd, Z=Z, k=k,
                threshold=float(np.quantile(self_excluded, SUPPORT_QUANTILE)),
                bins=bins, n=len(X))
