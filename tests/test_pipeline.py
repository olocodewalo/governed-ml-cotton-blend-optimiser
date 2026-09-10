"""Fast smoke + property tests. Assumes `make data && make train` have run."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from config import BALES_PARQUET, LAYDOWNS_PARQUET, QUALITY_TARGETS, YARN_COUNT_SPECS
from data.features import blend_profile, feature_columns
from data.quality_physics import predict_quality

pytestmark = pytest.mark.filterwarnings("ignore")

_HAVE_DATA = BALES_PARQUET.exists() and LAYDOWNS_PARQUET.exists()
_needs_data = pytest.mark.skipif(not _HAVE_DATA, reason="run `make data` first")


@pytest.fixture(scope="module")
def bales():
    return pd.read_parquet(BALES_PARQUET)


# --- physics -----------------------------------------------------------------
def _profile(**over):
    base = dict(w_mean_strength_gtex=30.0, w_mean_staple_length_mm=29.0,
                w_mean_uniformity_pct=81.0, w_mean_short_fibre_content_pct=9.0,
                w_mean_micronaire=4.1, w_mean_trash_pct=3.0,
                w_var_micronaire=0.05, w_var_short_fibre_content_pct=1.0)
    base.update(over)
    return base


def test_sfc_penalty_is_superlinear():
    q_low = predict_quality(_profile(w_mean_short_fibre_content_pct=8.0)).csp
    q_mid = predict_quality(_profile(w_mean_short_fibre_content_pct=10.0)).csp
    q_hi = predict_quality(_profile(w_mean_short_fibre_content_pct=12.0)).csp
    d1, d2 = q_low - q_mid, q_mid - q_hi
    assert d1 > 0 and d2 > 0
    assert d2 > d1 * 1.1          # accelerating penalty


def test_micronaire_variance_hurts_evenness():
    lo = predict_quality(_profile(w_var_micronaire=0.02)).u_pct
    hi = predict_quality(_profile(w_var_micronaire=0.30)).u_pct
    assert hi > lo


def test_noise_changes_output():
    rng = np.random.default_rng(0)
    a = predict_quality(_profile(), rng=rng, add_noise=True).csp
    b = predict_quality(_profile(), rng=rng, add_noise=True).csp
    assert a != b


# --- features --------------------------------------------------------------
@_needs_data
def test_blend_profile_shapes_and_weights(bales):
    sub = bales.head(40)
    prof = blend_profile(sub, np.ones(40))
    assert set(feature_columns()).issubset(prof)
    fr = sum(v for k, v in prof.items() if k.startswith("origin_frac_"))
    assert fr == pytest.approx(1.0, abs=1e-6)
    assert 1.0 <= prof["n_bales_effective"] <= 40.0


@_needs_data
def test_weight_normalisation_invariance(bales):
    sub = bales.head(30)
    w = np.random.default_rng(1).random(30)
    p1 = blend_profile(sub, w)
    p2 = blend_profile(sub, w * 7.0)
    assert p1["w_mean_micronaire"] == pytest.approx(p2["w_mean_micronaire"])


# --- model ---------------------------------------------------------------
@_needs_data
def test_model_predicts_with_intervals():
    from optimiser.common import load_current_model
    m = load_current_model()
    X = pd.DataFrame([_profile_features()], columns=feature_columns())
    pred = m.predict(X).iloc[0]
    for t in QUALITY_TARGETS:
        assert pred[f"{t}_p10"] <= pred[t] + 1e-6 <= pred[f"{t}_p90"] + 1e-6


def _profile_features():
    p = _profile()
    p.setdefault("origin_frac_India_Shankar6", 0.5)
    p.setdefault("origin_frac_US_Pima", 0.2)
    p.setdefault("origin_frac_West_African", 0.1)
    p.setdefault("origin_frac_Egyptian_Giza", 0.2)
    p.setdefault("n_bales_effective", 35.0)
    return {c: p.get(c, 0.0) for c in feature_columns()}


# --- optimiser ---------------------------------------------------------
@_needs_data
def test_lp_blend_respects_hard_constraints():
    from optimiser.common import load_current_model, make_scenario
    from optimiser.lp import solve_lp
    m = load_current_model()
    sc = make_scenario("30s_Ne", inventory_size=90, seed=42)
    res = solve_lp(sc, m)
    w = np.array(res.weights)
    assert w.sum() == pytest.approx(1.0, abs=1e-5)
    assert (w > 1e-4).sum() <= sc.max_bales
    d_mic = abs(res.profile["w_mean_micronaire"] - sc.rolling_profile["w_mean_micronaire"])
    assert d_mic <= sc.mic_tol + 1e-3


# --- explainer -------------------------------------------------------
def test_retriever_returns_hits():
    from explainer.retriever import retrieve
    hits, backend = retrieve("why does short fibre content hurt yarn strength", k=3)
    assert len(hits) == 3 and backend


@_needs_data
def test_explainer_templated_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from optimiser.common import load_current_model, make_scenario, naive_baseline
    from optimiser.lp import solve_lp
    from explainer.generate import explain_blend
    m = load_current_model()
    sc = make_scenario("40s_Ne", inventory_size=80, seed=7)
    res = solve_lp(sc, m)
    exp = explain_blend(sc, res, naive_baseline(sc, m))
    assert exp.llm_model == "templated-fallback"
    assert len(exp.rationale) > 200
