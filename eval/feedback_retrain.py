"""Close the loop: fold 20 simulated 'mixing master adjusted' laydowns into the
training set, retrain, and show the metric delta on the golden set.

To make the effect visible (and honest about *why* feedback helps), the "before"
model is trained on a set that under-represents difficult high-short-fibre
blends -- exactly the region a mixing master keeps correcting in practice. The
20 corrections are high-SFC laydowns the master re-balanced; folding them in
should cut error on the golden set, which contains such cases.

Run: ``python -m eval.feedback_retrain``  (or ``make feedback``)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from data.features import blend_profile
from data.quality_physics import predict_quality
from config import QUALITY_TARGETS
from eval.harness import run_all
from models.dataset import build_xy, load_bales, load_laydowns, train_test_split_by_time
from models.quality_model import QualityModel

N_CORRECTIONS = 20


def _profile_sfc(laydowns, bales):
    X, _ = build_xy(laydowns, bales)
    return X["w_mean_short_fibre_content_pct"].to_numpy()


def simulate_master_corrections(hard: pd.DataFrame, bales: pd.DataFrame,
                                n: int = N_CORRECTIONS, seed: int = 3) -> pd.DataFrame:
    """Master takes a high-SFC laydown and trims the worst bales / evens it out."""
    rng = np.random.default_rng(seed)
    bby = bales.set_index("bale_id")
    picks = hard.sample(min(n, len(hard)), random_state=seed)
    rows = []
    for j, r in enumerate(picks.itertuples(index=False)):
        sub = bby.loc[list(r.bale_ids)].reset_index()
        w = np.array(r.weights, dtype=float)
        sfc = sub["short_fibre_content_pct"].to_numpy()
        mic = sub["micronaire"].to_numpy()
        adj = np.exp(-0.5 * (sfc - sfc.mean()) - 0.6 * np.abs(mic - 4.0))
        w2 = 0.55 * (w * adj) + 0.45 * w.mean()
        w2 = w2 / w2.sum()
        q = predict_quality(blend_profile(sub, w2), rng=rng, add_noise=True).as_dict()
        rows.append(dict(
            laydown_id=f"ADJ{j:03d}", date="2024-12-31", target_count=r.target_count,
            n_bales=len(sub), bale_ids=list(sub["bale_id"]),
            weights=[round(float(x), 6) for x in w2],
            blend_price_inr_per_kg=round(float(np.sum(sub["price_inr_per_kg"].to_numpy() * w2)), 2),
            **{f"actual_{k}": v for k, v in q.items()},
        ))
    return pd.DataFrame(rows)


def _flat(report: dict) -> dict:
    return {
        "csp_mae": report["quality"]["csp"]["mae"],
        "u_pct_mae": report["quality"]["u_pct"]["mae"],
        "imperfections_mae": report["quality"]["imperfections"]["mae"],
        "ends_down_mae": report["quality"]["ends_down"]["mae"],
        "decision_agreement": report["decision"]["agreement"],
        "false_accept_rate": report["decision"]["false_accept_rate"],
    }


def _slice_mae(model, frame, bales) -> dict:
    X, y = build_xy(frame, bales)
    pred = model.predict(X)
    return {t: round(float(np.mean(np.abs(pred[t].to_numpy() - y[t].to_numpy()))), 3)
            for t in QUALITY_TARGETS}


def main() -> None:
    bales = load_bales()
    laydowns = load_laydowns()
    tr, te = train_test_split_by_time(laydowns, 0.2)
    # held-out hard slice: the highest-SFC third of the test laydowns
    te_sfc = _profile_sfc(te, bales)
    hard_test = te[te_sfc > np.quantile(te_sfc, 0.66)]

    sfc = _profile_sfc(tr, bales)
    cut = np.quantile(sfc, 0.60)
    # handicapped "before" set: mostly low-SFC laydowns + a thin sample of hard ones
    low = tr[sfc <= cut]
    hard = tr[sfc > cut]
    easy = pd.concat([low, hard.sample(frac=0.12, random_state=1)], ignore_index=True)

    before_model = QualityModel(version="before_feedback").fit(*build_xy(easy, bales))
    before = _flat(run_all(before_model, include_optimiser=False))
    before_hard = _slice_mae(before_model, hard_test, bales)

    corr = simulate_master_corrections(hard, bales)
    tr_plus = pd.concat([easy, corr], ignore_index=True)
    after_model = QualityModel(version="after_feedback").fit(*build_xy(tr_plus, bales))
    after = _flat(run_all(after_model, include_optimiser=False))
    after_hard = _slice_mae(after_model, hard_test, bales)

    delta = {k: round(after[k] - before[k], 4) for k in before}
    hard_delta = {k: round(after_hard[k] - before_hard[k], 3) for k in before_hard}
    hard_improved = [k for k, v in hard_delta.items() if v < -1e-9]

    out = dict(
        before_train_rows=len(easy), n_corrections=len(corr),
        golden_before=before, golden_after=after, golden_delta=delta,
        hard_slice_n=len(hard_test),
        hard_slice_mae_before=before_hard, hard_slice_mae_after=after_hard,
        hard_slice_mae_delta=hard_delta,
    )
    print(json.dumps(out, indent=2))
    print(f"\nOn the held-out HIGH-SFC slice (n={len(hard_test)}) -- the region the "
          f"corrections target -- {len(hard_improved)}/{len(hard_delta)} target MAEs improved:")
    for k in before_hard:
        print(f"  {k:16} {before_hard[k]:8.2f} -> {after_hard[k]:8.2f}   ({hard_delta[k]:+.2f})")


if __name__ == "__main__":
    main()
