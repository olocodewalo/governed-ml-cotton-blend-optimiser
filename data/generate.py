"""Synthetic data generator for the Cotton Blend Optimisation prototype.

Produces two parquet files:
  data/bales.parquet     ~2000 bale test records (HVI/AFIS-style)
  data/laydowns.parquet  ~500 historical laydowns + their ACTUAL spun-yarn QC

Run: ``python -m data.generate``  (or ``make data``)
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from config import (BALES_PARQUET, DATA_DIR, LAYDOWNS_PARQUET, ORIGINS,
                    RANDOM_SEED, ROLLING_WINDOW, YARN_COUNT_SPECS)
from data.features import blend_profile
from data.quality_physics import predict_quality

N_BALES = 2000
N_LAYDOWNS = 500

# Per-origin fibre-property means; spreads are shared. Values chosen to stay
# inside the global ranges in the spec after clipping.
ORIGIN_PROFILE = {
    "India_Shankar6": dict(micronaire=4.3, staple=28.5, strength=28.0, uniformity=81.0,
                           sfc=9.5, trash=3.2, maturity=0.86, price_premium=0.0,
                           weight=0.42),
    "US_Pima":        dict(micronaire=4.0, staple=31.3, strength=33.0, uniformity=84.0,
                           sfc=7.0, trash=1.6, maturity=0.90, price_premium=55.0,
                           weight=0.18),
    "West_African":   dict(micronaire=3.9, staple=27.6, strength=28.5, uniformity=80.0,
                           sfc=10.5, trash=4.1, maturity=0.83, price_premium=-8.0,
                           weight=0.22),
    "Egyptian_Giza":  dict(micronaire=4.1, staple=31.6, strength=32.0, uniformity=84.5,
                           sfc=7.4, trash=1.9, maturity=0.89, price_premium=48.0,
                           weight=0.18),
}

COLOUR_GRADES = ["31", "32", "41", "42", "51"]  # Middling .. Strict Low Middling


def _clip(x, lo, hi):
    return np.clip(x, lo, hi)


def generate_bales(rng: np.random.Generator) -> pd.DataFrame:
    origins = rng.choice(ORIGINS, size=N_BALES,
                         p=[ORIGIN_PROFILE[o]["weight"] for o in ORIGINS])
    rows = []
    for i, o in enumerate(origins):
        pr = ORIGIN_PROFILE[o]
        micronaire = _clip(rng.normal(pr["micronaire"], 0.45), 3.0, 5.5)
        staple = _clip(rng.normal(pr["staple"], 1.1), 26.0, 32.0)
        strength = _clip(rng.normal(pr["strength"], 1.8), 26.0, 34.0)
        uniformity = _clip(rng.normal(pr["uniformity"], 1.4), 78.0, 85.0)
        # SFC is anti-correlated with staple length and uniformity
        sfc = _clip(rng.normal(pr["sfc"], 1.3) - 0.35 * (staple - pr["staple"])
                    - 0.2 * (uniformity - pr["uniformity"]), 6.0, 14.0)
        trash = _clip(rng.gamma(2.0, pr["trash"] / 2.0), 0.5, 9.0)
        maturity = _clip(rng.normal(pr["maturity"], 0.03), 0.72, 0.95)

        # Price: quality-driven + origin premium + lot noise.
        price = (
            150.0
            + 4.2 * (staple - 26.0)
            + 3.6 * (strength - 26.0)
            - 5.5 * (sfc - 6.0)
            - 2.0 * (trash - 1.0)
            + 30.0 * (maturity - 0.80)
            + pr["price_premium"]
            + rng.normal(0, 4.0)
        )
        rows.append(dict(
            bale_id=f"B{i:05d}",
            lot_id=f"LOT{i // 12:04d}",
            origin=o,
            micronaire=round(float(micronaire), 2),
            staple_length_mm=round(float(staple), 1),
            strength_gtex=round(float(strength), 1),
            uniformity_pct=round(float(uniformity), 1),
            short_fibre_content_pct=round(float(sfc), 1),
            trash_pct=round(float(trash), 2),
            maturity_ratio=round(float(maturity), 3),
            colour_grade=rng.choice(COLOUR_GRADES, p=[0.28, 0.30, 0.22, 0.12, 0.08]),
            weight_kg=round(float(rng.normal(220, 8)), 1),
            price_inr_per_kg=round(float(_clip(price, 140.0, 340.0)), 2),
        ))
    return pd.DataFrame(rows)


def _sample_weights(rng: np.random.Generator, n: int) -> np.ndarray:
    # Dirichlet with alpha<1 -> a few dominant bales, many small -> realistic laydown
    w = rng.dirichlet(alpha=np.full(n, 0.9))
    return w


# The historical mixing master is cost-conscious but not optimising: a mild
# lean toward cheaper bales and, for finer counts, toward longer staple / lower
# SFC. Strong availability noise dominates, so the historical actual is a
# reasonable-but-beatable baseline rather than a random or an optimal one.
_COUNT_SELECTIVITY = {"20s_Ne": 0.2, "30s_Ne": 0.3, "40s_Ne": 0.45, "60s_Ne": 0.65}


def generate_laydowns(bales: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    counts = list(YARN_COUNT_SPECS.keys())
    start = np.datetime64("2023-01-02")
    n_all = len(bales)
    staple_z = (bales["staple_length_mm"] - bales["staple_length_mm"].mean()) / bales["staple_length_mm"].std()
    sfc_z = (bales["short_fibre_content_pct"] - bales["short_fibre_content_pct"].mean()) / bales["short_fibre_content_pct"].std()
    price_z = (bales["price_inr_per_kg"] - bales["price_inr_per_kg"].mean()) / bales["price_inr_per_kg"].std()
    rows = []
    for k in range(N_LAYDOWNS):
        n = int(rng.integers(30, 51))
        target = counts[int(rng.integers(0, len(counts)))]
        sel = _COUNT_SELECTIVITY[target]
        logit = sel * (0.7 * staple_z.to_numpy() - 0.7 * sfc_z.to_numpy() - 1.0 * price_z.to_numpy())
        logit += rng.normal(0, 1.6, n_all)          # week-to-week availability noise dominates
        p = np.exp(logit - logit.max())
        p = p / p.sum()
        idx = rng.choice(n_all, size=n, replace=False, p=p)
        sub = bales.iloc[idx].reset_index(drop=True)
        w = _sample_weights(rng, n)

        prof = blend_profile(sub, w)
        outcome = predict_quality(prof, rng=rng, add_noise=True)

        rows.append(dict(
            laydown_id=f"LD{k:04d}",
            date=str(start + np.timedelta64(int(k * 3.6), "D")),
            target_count=target,
            n_bales=n,
            bale_ids=list(sub["bale_id"]),
            weights=[round(float(x), 6) for x in w],
            blend_price_inr_per_kg=round(float(np.sum(sub["price_inr_per_kg"].to_numpy() * w)), 2),
            **{f"actual_{key}": val for key, val in outcome.as_dict().items()},
        ))
    return pd.DataFrame(rows)


def _hash_df(df: pd.DataFrame) -> str:
    # to_json handles list-valued cells (bale_ids / weights) that break the
    # native pandas hasher.
    return hashlib.sha256(df.to_json(orient="records").encode()).hexdigest()[:16]


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)

    bales = generate_bales(rng)
    laydowns = generate_laydowns(bales, rng)

    bales.to_parquet(BALES_PARQUET, index=False)
    laydowns.to_parquet(LAYDOWNS_PARQUET, index=False)

    manifest = dict(
        n_bales=len(bales),
        n_laydowns=len(laydowns),
        bales_hash=_hash_df(bales),
        laydowns_hash=_hash_df(laydowns),
        seed=RANDOM_SEED,
        rolling_window=ROLLING_WINDOW,
    )
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"wrote {BALES_PARQUET}  ({len(bales)} bales)")
    print(f"wrote {LAYDOWNS_PARQUET}  ({len(laydowns)} laydowns)")
    print("price range  : %.1f .. %.1f INR/kg" % (bales.price_inr_per_kg.min(), bales.price_inr_per_kg.max()))
    print("actual CSP   : %.0f .. %.0f" % (laydowns.actual_csp.min(), laydowns.actual_csp.max()))
    print("actual U%%    : %.2f .. %.2f" % (laydowns.actual_u_pct.min(), laydowns.actual_u_pct.max()))
    print("manifest     :", json.dumps(manifest))


if __name__ == "__main__":
    main()
