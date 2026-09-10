"""Linear surrogate of the ML quality model for use inside the LP.

The real quality model is a non-linear GBM whose inputs include weighted
*variances* -- quadratic in the blend weights, so unusable in a linear program.
The surrogate is an OLS fit on only the features that are linear in the bale
weights (weighted means + origin fractions). It is deliberately weaker; the LP
solves fast and exactly against it, then the full model re-scores the result and
the HITL UI shows any gap. See docs/lp_vs_metaheuristic.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LinearRegression

from config import FIBRE_PROPS, ORIGINS, QUALITY_TARGETS
from models.dataset import build_xy

LINEAR_FEATURES = [f"w_mean_{p}" for p in FIBRE_PROPS] + [f"origin_frac_{o}" for o in ORIGINS]


@dataclass
class LinearSurrogate:
    coef_: dict           # target -> np.ndarray over LINEAR_FEATURES
    intercept_: dict      # target -> float
    features: list

    @staticmethod
    def fit() -> "LinearSurrogate":
        X, y = build_xy()
        Xl = X[LINEAR_FEATURES]
        coef, inter = {}, {}
        for t in QUALITY_TARGETS:
            lr = LinearRegression().fit(Xl, y[t])
            coef[t] = lr.coef_.astype(float)
            inter[t] = float(lr.intercept_)
        return LinearSurrogate(coef_=coef, intercept_=inter, features=list(LINEAR_FEATURES))

    def linear_expr_coeffs(self, target: str, inventory) -> tuple[np.ndarray, float]:
        """Return (per-bale coefficient vector, constant) s.t.
        target_hat = const + sum_i c_i * w_i  for a blend over ``inventory``.
        """
        c = self.coef_[target]
        feat_index = {f: k for k, f in enumerate(self.features)}
        per_bale = np.zeros(len(inventory))
        for p in FIBRE_PROPS:
            k = feat_index[f"w_mean_{p}"]
            per_bale += c[k] * inventory[p].to_numpy(dtype=float)
        origin = inventory["origin"].to_numpy()
        for o in ORIGINS:
            k = feat_index[f"origin_frac_{o}"]
            per_bale += c[k] * (origin == o).astype(float)
        return per_bale, self.intercept_[target]
