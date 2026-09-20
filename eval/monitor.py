"""Drift monitor and retrain triggers (model governance policy, section 5).

    python -m eval.monitor                          # check the approved model
    python -m eval.monitor --simulate-shift 0.35    # demo: new crop year, micronaire +0.35
    python -m eval.monitor --fail-on-trigger        # exit 3 if any trigger fires (cron / CI)

Triggers checked:
  * PSI > PSI_ALERT on any key blend feature, recent laydowns vs the model's
    own training distribution (snapshot stored in the model artifact);
  * rolling prediction MAE over the last ROLLING_MAE_WINDOW laydowns
    > ROLLING_MAE_ALERT_RATIO x the model's golden-set MAE;
  * >= CORRECTIONS_RETRAIN_TRIGGER master 'adjust' decisions logged against it;
  * an origin in inventory that the model never saw in training.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from config import (CORRECTIONS_RETRAIN_TRIGGER, ORIGINS, PSI_ALERT, PSI_KEY_FEATURES,
                    QUALITY_TARGETS, ROLLING_MAE_ALERT_RATIO, ROLLING_MAE_WINDOW)
from data.quality_physics import predict_quality
from models import registry
from models.dataset import build_xy, load_bales, load_laydowns

# PSI on a small window has a sampling floor of roughly (bins - 1) / n, so the
# comparison window must be large enough for 0.2 to mean real drift.
PSI_WINDOW = 100


@dataclass
class Trigger:
    name: str
    fired: bool
    detail: str


def psi(edges: np.ndarray, ref_props: np.ndarray, values, eps: float = 1e-4) -> float:
    """Population stability index of ``values`` against a binned reference.
    Values outside the reference range fall into the edge bins."""
    counts, _ = np.histogram(np.clip(np.asarray(values, dtype=float), edges[0], edges[-1]), bins=edges)
    cur = counts / max(counts.sum(), 1)
    e = np.clip(ref_props, eps, None)
    a = np.clip(cur, eps, None)
    return float(np.sum((a - e) * np.log(a / e)))


def feature_psi(model, X: pd.DataFrame, features=PSI_KEY_FEATURES) -> dict:
    bins = model.train_ref_["bins"]
    return {f: round(psi(bins[f]["edges"], bins[f]["props"], X[f]), 4) for f in features}


def rolling_mae(model, X: pd.DataFrame, y: pd.DataFrame) -> dict:
    pred = model.predict(X)
    return {t: round(float(np.mean(np.abs(pred[t].to_numpy() - y[t].to_numpy()))), 3)
            for t in QUALITY_TARGETS}


def reference_mae(entry: dict) -> dict:
    src = entry.get("golden_metrics") or {"quality": entry["metrics"]}
    return {t: src["quality"][t]["mae"] for t in QUALITY_TARGETS}


def unseen_origins(model, bales: pd.DataFrame) -> list[str]:
    mu = model.train_ref_["mu"]
    seen = {o for o in ORIGINS if mu.get(f"origin_frac_{o}", 0.0) > 0}
    return sorted(set(bales["origin"]) - seen)


def simulate_crop_shift(X: pd.DataFrame, mic_shift: float, seed: int = 0):
    """Shift blend micronaire (a new crop year) and relabel with the ground-truth physics."""
    Xs = X.copy()
    Xs["w_mean_micronaire"] += mic_shift
    rng = np.random.default_rng(seed)
    ys = pd.DataFrame([predict_quality(r, rng=rng, add_noise=True).as_dict()
                       for r in Xs.to_dict("records")])[QUALITY_TARGETS]
    return Xs, ys


def check_triggers(model, entry: dict, X_recent: pd.DataFrame, y_recent: pd.DataFrame,
                   bales: pd.DataFrame, corrections: int) -> tuple[list[Trigger], dict]:
    psis = feature_psi(model, X_recent)
    drifted = {f: v for f, v in psis.items() if v > PSI_ALERT}

    window_X, window_y = X_recent.tail(ROLLING_MAE_WINDOW), y_recent.tail(ROLLING_MAE_WINDOW)
    mae = rolling_mae(model, window_X, window_y)
    ref = reference_mae(entry)
    ratios = {t: round(mae[t] / ref[t], 2) for t in QUALITY_TARGETS}
    mae_bad = {t: r for t, r in ratios.items() if r > ROLLING_MAE_ALERT_RATIO}

    new_origins = unseen_origins(model, bales)
    triggers = [
        Trigger("feature_drift_psi", bool(drifted),
                f"PSI > {PSI_ALERT}: {drifted}" if drifted else f"max PSI {max(psis.values()):.3f}"),
        Trigger("rolling_mae", bool(mae_bad),
                f"MAE ratio > {ROLLING_MAE_ALERT_RATIO}: {mae_bad}" if mae_bad
                else f"max MAE ratio {max(ratios.values()):.2f} over last {len(window_X)} laydowns"),
        Trigger("master_corrections", corrections >= CORRECTIONS_RETRAIN_TRIGGER,
                f"{corrections} 'adjust' decisions logged (trigger at {CORRECTIONS_RETRAIN_TRIGGER})"),
        Trigger("new_origin", bool(new_origins),
                f"origins never seen in training: {new_origins}" if new_origins else "none"),
    ]
    detail = dict(psi=psis, rolling_mae=mae, reference_golden_mae=ref, mae_ratio=ratios)
    return triggers, detail


def main() -> None:
    from app.decisions_db import count_actions
    from optimiser.common import load_current_model, load_model

    ap = argparse.ArgumentParser()
    ap.add_argument("--version", help="monitor a specific registered model (default: approved)")
    ap.add_argument("--simulate-shift", type=float, default=0.0, metavar="MIC",
                    help="demo a crop-year shift of blend micronaire by MIC")
    ap.add_argument("--fail-on-trigger", action="store_true")
    args = ap.parse_args()

    model = load_model(args.version) if args.version else load_current_model()
    entry = registry.get(model.version)
    bales = load_bales()
    recent = load_laydowns().sort_values("date").tail(PSI_WINDOW)
    X, y = build_xy(recent, bales)
    if args.simulate_shift:
        X, y = simulate_crop_shift(X, args.simulate_shift)

    triggers, detail = check_triggers(model, entry, X, y, bales,
                                      corrections=count_actions("adjust", model.version))
    print(json.dumps(dict(model_version=model.version, status=entry["status"],
                          window=len(X), simulated_micronaire_shift=args.simulate_shift,
                          **detail, triggers=[asdict(t) for t in triggers]), indent=2))
    fired = [t.name for t in triggers if t.fired]
    print(f"\nRETRAIN TRIGGERED by: {', '.join(fired)}" if fired else "\nno retrain trigger fired")
    if fired and args.fail_on_trigger:
        sys.exit(3)


if __name__ == "__main__":
    main()
