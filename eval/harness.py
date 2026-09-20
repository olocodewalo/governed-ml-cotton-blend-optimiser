"""Golden-set evaluation harness.

Three questions, on data the model never trained on:
  1. Quality prediction error   -- MAE / RMSE / P10-P90 coverage per target.
  2. In-band decision quality    -- when the model says a blend meets the count
     spec, does the ground-truth physics agree? (false-accept rate)
  3. Optimiser value             -- rebuild each golden laydown's choice set,
     run the LP, and compare its cost + true quality to the historical actual.
     Every golden laydown is a scenario; savings and rates carry 95% intervals
     so a small-sample number is not over-read.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import QUALITY_TARGETS, YARN_COUNT_SPECS
from data.quality_physics import predict_quality
from models.dataset import build_xy, load_bales, load_laydowns
from optimiser.common import Scenario, rolling_profile
from optimiser.lp import solve_lp
from optimiser.surrogate import LinearSurrogate

GOLDEN_N = 50


def golden_laydowns() -> pd.DataFrame:
    ld = load_laydowns().sort_values("date").reset_index(drop=True)
    return ld.tail(GOLDEN_N).copy()


def _in_band(q: dict, spec: dict) -> bool:
    return (q["csp"] >= spec["min_csp"] and q["u_pct"] <= spec["max_u_pct"]
            and q["imperfections"] <= spec["max_imperfections"]
            and q["ends_down"] <= spec["max_ends_down"])


def bootstrap_mean_ci(values, n_boot: int = 2000, level: float = 0.95, seed: int = 0):
    v = np.asarray(values, dtype=float)
    if len(v) < 2:
        return [None, None]
    rng = np.random.default_rng(seed)
    means = rng.choice(v, size=(n_boot, len(v)), replace=True).mean(axis=1)
    a = (1 - level) / 2
    return [round(float(np.quantile(means, a)), 2), round(float(np.quantile(means, 1 - a)), 2)]


def wilson_ci(successes: int, n: int, z: float = 1.96):
    if n == 0:
        return [None, None]
    p = successes / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return [round(float(centre - half), 3), round(float(centre + half), 3)]


def quality_metrics(model, golden: pd.DataFrame, bales: pd.DataFrame) -> dict:
    X, y = build_xy(golden, bales)
    pred = model.predict(X)
    out = {}
    for t in QUALITY_TARGETS:
        err = pred[t].to_numpy() - y[t].to_numpy()
        inside = ((y[t].to_numpy() >= pred[f"{t}_p10"].to_numpy())
                  & (y[t].to_numpy() <= pred[f"{t}_p90"].to_numpy()))
        out[t] = dict(mae=round(float(np.mean(np.abs(err))), 3),
                      rmse=round(float(np.sqrt(np.mean(err ** 2))), 3),
                      pi_coverage=round(float(np.mean(inside)), 3),
                      pi_coverage_ci95=wilson_ci(int(inside.sum()), len(inside)))
    return out


def decision_metrics(model, golden: pd.DataFrame, bales: pd.DataFrame) -> dict:
    """Model's in-band call vs ground-truth physics, per golden laydown."""
    X, _ = build_xy(golden, bales)
    pred = model.predict(X)
    n, agree, false_accept, false_reject = 0, 0, 0, 0
    for i, row in enumerate(golden.itertuples(index=False)):
        spec = YARN_COUNT_SPECS[row.target_count]
        model_q = {t: float(pred.iloc[i][t]) for t in QUALITY_TARGETS}
        truth_q = predict_quality(X.iloc[i].to_dict(), add_noise=False).as_dict()
        m_ok, t_ok = _in_band(model_q, spec), _in_band(truth_q, spec)
        n += 1
        agree += (m_ok == t_ok)
        false_accept += (m_ok and not t_ok)
        false_reject += (t_ok and not m_ok)
    return dict(n=n, agreement=round(agree / n, 3),
                false_accept_rate=round(false_accept / n, 3),
                false_accept_ci95=wilson_ci(false_accept, n),
                false_reject_rate=round(false_reject / n, 3))


def optimiser_value(model, golden: pd.DataFrame, bales: pd.DataFrame,
                    sample: int | None = None, extra_bales: int = 90, seed: int = 7) -> dict:
    surrogate = LinearSurrogate.fit()
    rp = rolling_profile(bales=bales)
    rng = np.random.default_rng(seed)
    bby_id = bales.set_index("bale_id")
    rows = golden if sample is None else golden.sample(min(sample, len(golden)), random_state=seed)
    has_support = bool(getattr(model, "train_ref_", None))

    savings, matched_savings, in_band_flags, hist_in_band, in_support = [], [], [], [], []
    for r in rows.itertuples(index=False):
        used = list(r.bale_ids)
        others = bales[~bales["bale_id"].isin(used)].sample(extra_bales, random_state=int(rng.integers(1e6)))
        inv = pd.concat([bby_id.loc[used].reset_index(), others]).drop_duplicates("bale_id").reset_index(drop=True)
        base_spec = dict(YARN_COUNT_SPECS[r.target_count])
        scenario = Scenario(target_count=r.target_count, inventory=inv,
                            rolling_profile=rp, spec=base_spec)

        res = solve_lp(scenario, model, surrogate=surrogate)
        truth = predict_quality(res.profile, add_noise=False).as_dict()   # ground-truth
        opt_ok = _in_band(truth, base_spec)
        hist_q = {t: getattr(r, f"actual_{t}") for t in QUALITY_TARGETS}
        hist_ok = _in_band(hist_q, base_spec)

        if res.feasible:
            savings.append(100 * (r.blend_price_inr_per_kg - res.price_inr_per_kg) / r.blend_price_inr_per_kg)
            in_band_flags.append(opt_ok)
            hist_in_band.append(hist_ok)
            if has_support:
                row = pd.DataFrame([res.profile], columns=model.features)
                in_support.append(bool(model.support_ratio(row)[0] <= 1.0))

        # like-for-like: require the optimiser to at least match the historical
        # blend's OWN quality on every axis (the credible "saving at equal quality")
        if hist_ok:
            tight = dict(min_csp=max(base_spec["min_csp"], hist_q["csp"]),
                         max_u_pct=min(base_spec["max_u_pct"], hist_q["u_pct"]),
                         max_imperfections=min(base_spec["max_imperfections"], hist_q["imperfections"]),
                         max_ends_down=min(base_spec["max_ends_down"], hist_q["ends_down"]))
            sc2 = Scenario(target_count=r.target_count, inventory=inv,
                           rolling_profile=rp, spec=tight)
            res2 = solve_lp(sc2, model, surrogate=surrogate)
            if res2.feasible:
                matched_savings.append(100 * (r.blend_price_inr_per_kg - res2.price_inr_per_kg)
                                       / r.blend_price_inr_per_kg)

    savings_arr = np.array(savings) if savings else np.array([0.0])
    matched = np.array(matched_savings) if matched_savings else np.array([0.0])
    n = len(in_band_flags)
    return dict(
        n=n,
        mean_cost_saving_pct_vs_historical=round(float(np.mean(savings_arr)), 2),
        mean_cost_saving_pct_vs_historical_ci95=bootstrap_mean_ci(savings),
        median_cost_saving_pct_vs_historical=round(float(np.median(savings_arr)), 2),
        mean_cost_saving_pct_at_matched_quality=round(float(np.mean(matched)), 2),
        mean_cost_saving_pct_at_matched_quality_ci95=bootstrap_mean_ci(matched_savings),
        n_matched=len(matched_savings),
        optimiser_blend_in_band_rate=round(float(np.mean(in_band_flags)) if n else 0.0, 3),
        optimiser_blend_in_band_ci95=wilson_ci(int(np.sum(in_band_flags)), n),
        historical_blend_in_band_rate=round(float(np.mean(hist_in_band)) if hist_in_band else 0.0, 3),
        optimiser_blend_in_support_rate=(round(float(np.mean(in_support)), 3) if in_support else None),
    )


def run_all(model, include_optimiser: bool = True) -> dict:
    bales = load_bales()
    golden = golden_laydowns()
    out = dict(
        golden_n=len(golden),
        quality=quality_metrics(model, golden, bales),
        decision=decision_metrics(model, golden, bales),
    )
    if include_optimiser:
        out["optimiser"] = optimiser_value(model, golden, bales)
    return out
