"""Shared optimiser plumbing: scenarios, baselines, quality evaluation, results."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config import (ARTIFACTS_DIR, LTB_MICRONAIRE_TOL, LTB_STRENGTH_TOL,
                    MAX_BALES_IN_LAYDOWN, QUALITY_TARGETS, RANDOM_SEED,
                    ROLLING_WINDOW, YARN_COUNT_SPECS)
from data.features import blend_profile, feature_columns
from models.dataset import build_xy, load_bales, load_laydowns
from models.quality_model import QualityModel

CURRENT_MODEL = ARTIFACTS_DIR / "quality_model_current.joblib"


@dataclass
class Scenario:
    target_count: str
    inventory: pd.DataFrame               # subset of bales.parquet
    rolling_profile: dict                 # mean fibre profile of last N laydowns
    spec: dict                            # YARN_COUNT_SPECS[target_count]
    max_bales: int = MAX_BALES_IN_LAYDOWN
    mic_tol: float = LTB_MICRONAIRE_TOL
    strength_tol: float = LTB_STRENGTH_TOL


@dataclass
class BlendResult:
    method: str
    bale_ids: list[str]
    weights: list[float]
    price_inr_per_kg: float
    predicted: dict                       # target -> dict(mean,p10,p90)
    profile: dict
    in_band: bool
    binding_constraints: list[str] = field(default_factory=list)
    feasible: bool = True
    note: str = ""

    def weight_table(self, inventory: pd.DataFrame) -> pd.DataFrame:
        m = inventory.set_index("bale_id")
        rows = []
        for b, w in zip(self.bale_ids, self.weights):
            if w <= 1e-4:
                continue
            r = m.loc[b]
            rows.append(dict(bale_id=b, weight_pct=round(100 * w, 2), origin=r["origin"],
                             micronaire=r["micronaire"], staple_length_mm=r["staple_length_mm"],
                             strength_gtex=r["strength_gtex"],
                             short_fibre_content_pct=r["short_fibre_content_pct"],
                             price_inr_per_kg=r["price_inr_per_kg"]))
        return pd.DataFrame(rows).sort_values("weight_pct", ascending=False)


def load_current_model() -> QualityModel:
    return QualityModel.load(CURRENT_MODEL)


def rolling_profile(laydowns: pd.DataFrame | None = None, bales: pd.DataFrame | None = None,
                    window: int = ROLLING_WINDOW) -> dict:
    laydowns = load_laydowns() if laydowns is None else laydowns
    bales = load_bales() if bales is None else bales
    recent = laydowns.sort_values("date").tail(window)
    X, _ = build_xy(recent, bales)
    return X.mean().to_dict()


def make_scenario(target_count: str = "40s_Ne", inventory_size: int = 120,
                  seed: int = RANDOM_SEED, bias: str | None = None) -> Scenario:
    """Build a weekly scenario: sample an inventory of bales available to blend.

    ``bias`` optionally skews the inventory ('cheap' or 'premium') to make the
    cost/quality trade-off sharper for demos.
    """
    bales = load_bales()
    rng = np.random.default_rng(seed)
    if bias == "cheap":
        p = 1.0 / (bales["price_inr_per_kg"].to_numpy() ** 2)
    elif bias == "premium":
        p = bales["strength_gtex"].to_numpy() ** 2
    else:
        p = np.ones(len(bales))
    p = p / p.sum()
    idx = rng.choice(len(bales), size=inventory_size, replace=False, p=p)
    inv = bales.iloc[idx].reset_index(drop=True)
    return Scenario(
        target_count=target_count,
        inventory=inv,
        rolling_profile=rolling_profile(bales=bales),
        spec=dict(YARN_COUNT_SPECS[target_count]),
    )


def evaluate_blend(scenario: Scenario, weights: np.ndarray, model: QualityModel,
                   method: str) -> BlendResult:
    inv = scenario.inventory
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    prof = blend_profile(inv, w)
    row = pd.DataFrame([prof], columns=feature_columns())
    pred_row = model.predict(row).iloc[0]
    predicted = {t: dict(mean=float(pred_row[t]), p10=float(pred_row[f"{t}_p10"]),
                         p90=float(pred_row[f"{t}_p90"])) for t in QUALITY_TARGETS}
    price = float(np.sum(inv["price_inr_per_kg"].to_numpy() * w))

    binding = _binding_constraints(scenario, prof, predicted)
    return BlendResult(
        method=method,
        bale_ids=list(inv["bale_id"]),
        weights=[float(x) for x in w],
        price_inr_per_kg=round(price, 2),
        predicted=predicted,
        profile=prof,
        in_band=len([b for b in binding if b.startswith("VIOLATED")]) == 0,
        binding_constraints=binding,
    )


def _binding_constraints(scenario: Scenario, prof: dict, predicted: dict,
                         tol: float = 0.02) -> list[str]:
    s = scenario.spec
    out = []

    eps = 1e-6

    def check(name, value, limit, kind):
        if kind == "min":
            if value < limit - eps - abs(limit) * 1e-4:
                out.append(f"VIOLATED {name}: {value:.1f} < {limit}")
            elif value <= limit * (1 + tol):
                out.append(f"binding {name}: {value:.1f} ~ min {limit}")
        else:
            if value > limit + eps + abs(limit) * 1e-4:
                out.append(f"VIOLATED {name}: {value:.1f} > {limit}")
            elif value >= limit * (1 - tol):
                out.append(f"binding {name}: {value:.1f} ~ max {limit}")

    check("CSP", predicted["csp"]["mean"], s["min_csp"], "min")
    check("U%", predicted["u_pct"]["mean"], s["max_u_pct"], "max")
    check("imperfections", predicted["imperfections"]["mean"], s["max_imperfections"], "max")
    check("ends_down", predicted["ends_down"]["mean"], s["max_ends_down"], "max")

    d_mic = abs(prof["w_mean_micronaire"] - scenario.rolling_profile["w_mean_micronaire"])
    d_str = abs(prof["w_mean_strength_gtex"] - scenario.rolling_profile["w_mean_strength_gtex"])
    if d_mic > scenario.mic_tol + 1e-4:
        out.append(f"VIOLATED long-term-blend micronaire drift: {d_mic:.3f} > {scenario.mic_tol}")
    elif d_mic >= scenario.mic_tol * 0.9:
        out.append(f"binding long-term-blend micronaire drift: {d_mic:.3f}")
    if d_str > scenario.strength_tol + 1e-3:
        out.append(f"VIOLATED long-term-blend strength drift: {d_str:.2f} > {scenario.strength_tol}")
    elif d_str >= scenario.strength_tol * 0.9:
        out.append(f"binding long-term-blend strength drift: {d_str:.2f}")
    return out


def naive_baseline(scenario: Scenario, model: QualityModel) -> BlendResult:
    """A realistic non-optimised blend, standing in for the spreadsheet status quo.

    Apply a coarse mixing-master quality filter (micronaire window, minimum
    staple, maximum SFC relative to the rolling average), then equal-weight the
    cheapest ``max_bales`` bales that pass it. Usually in-band but over-paying --
    the blend the optimiser is trying to beat on cost at equal predicted quality.
    """
    inv = scenario.inventory.reset_index(drop=True)
    rp = scenario.rolling_profile
    # mixing-master rule of thumb: a coarse quality filter, then buy the cheapest
    # bales that pass it, equal weight.
    ok = (
        ((inv["micronaire"] - rp["w_mean_micronaire"]).abs() <= scenario.mic_tol + 0.3)
        & (inv["staple_length_mm"] >= rp["w_mean_staple_length_mm"] - 0.6)
        & (inv["short_fibre_content_pct"] <= rp["w_mean_short_fibre_content_pct"] + 0.8)
    )
    pool = inv[ok] if ok.sum() >= scenario.max_bales else inv
    chosen = pool["price_inr_per_kg"].sort_values().head(scenario.max_bales).index
    w = np.zeros(len(inv))
    w[inv.index.isin(chosen)] = 1.0
    return evaluate_blend(scenario, w, model, method="naive_rule_of_thumb_equal_weight")
