"""Fast smoke + property tests. Assumes `make data && make train` have run."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from config import QUALITY_TARGETS
from data.features import blend_profile, feature_columns
from data.quality_physics import predict_quality
from tests.conftest import needs_data

pytestmark = pytest.mark.filterwarnings("ignore")


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
@needs_data
def test_blend_profile_shapes_and_weights(bales):
    sub = bales.head(40)
    prof = blend_profile(sub, np.ones(40))
    assert set(feature_columns()).issubset(prof)
    fr = sum(v for k, v in prof.items() if k.startswith("origin_frac_"))
    assert fr == pytest.approx(1.0, abs=1e-6)
    assert 1.0 <= prof["n_bales_effective"] <= 40.0


@needs_data
def test_weight_normalisation_invariance(bales):
    sub = bales.head(30)
    w = np.random.default_rng(1).random(30)
    p1 = blend_profile(sub, w)
    p2 = blend_profile(sub, w * 7.0)
    assert p1["w_mean_micronaire"] == pytest.approx(p2["w_mean_micronaire"])


@needs_data
def test_bales_carry_a_price_date(bales):
    assert pd.to_datetime(bales["price_as_of"]).notna().all()


# --- model ---------------------------------------------------------------
def _profile_features():
    p = _profile()
    p.setdefault("origin_frac_India_Shankar6", 0.5)
    p.setdefault("origin_frac_US_Pima", 0.2)
    p.setdefault("origin_frac_West_African", 0.1)
    p.setdefault("origin_frac_Egyptian_Giza", 0.2)
    p.setdefault("n_bales_effective", 35.0)
    return {c: p.get(c, 0.0) for c in feature_columns()}


@needs_data
def test_model_predicts_with_intervals(model):
    X = pd.DataFrame([_profile_features()], columns=feature_columns())
    pred = model.predict(X).iloc[0]
    for t in QUALITY_TARGETS:
        assert pred[f"{t}_p10"] <= pred[t] <= pred[f"{t}_p90"]
    assert set(model.calib_q_) == set(QUALITY_TARGETS)


@needs_data
def test_support_ratio_separates_history_from_extrapolation(model, bales):
    from models.dataset import build_xy, load_laydowns
    X, _ = build_xy(load_laydowns().head(40), bales)
    assert np.median(model.support_ratio(X)) < 1.0
    far = X.head(5).copy()
    far["origin_frac_West_African"] = 0.95
    far["w_mean_short_fibre_content_pct"] += 4.0
    assert (model.support_ratio(far) > 1.0).all()


# --- optimiser ---------------------------------------------------------
@needs_data
def test_lp_blend_respects_hard_constraints(model):
    from optimiser.common import make_scenario
    from optimiser.lp import solve_lp
    sc = make_scenario("30s_Ne", inventory_size=90, seed=42)
    res = solve_lp(sc, model)
    w = np.array(res.weights)
    assert w.sum() == pytest.approx(1.0, abs=1e-5)
    assert (w > 1e-4).sum() <= sc.max_bales
    assert w.max() <= 0.12 + 1e-6
    d_mic = abs(res.profile["w_mean_micronaire"] - sc.rolling_profile["w_mean_micronaire"])
    assert d_mic <= sc.mic_tol + 1e-3


@needs_data
def test_lp_caps_contamination_prone_origin(model):
    """Without the cap this cheap-inventory 20s scenario leans >50% West African."""
    from optimiser.common import make_scenario
    from optimiser.lp import solve_lp
    sc = make_scenario("20s_Ne", inventory_size=120)
    res = solve_lp(sc, model)
    cap = sc.origin_caps["West_African"]
    assert res.profile["origin_frac_West_African"] <= cap + 1e-6
    assert not any(b.startswith("VIOLATED origin cap") for b in res.binding_constraints)


@needs_data
def test_optimisers_refuse_stale_prices(model):
    from optimiser.common import make_scenario
    from optimiser.ga import solve_ga
    from optimiser.guards import StalePriceError
    from optimiser.lp import solve_lp
    sc = make_scenario("40s_Ne", inventory_size=60, seed=3)
    sc.as_of = sc.planning_date + pd.Timedelta(days=30)
    with pytest.raises(StalePriceError):
        solve_lp(sc, model)
    with pytest.raises(StalePriceError):
        solve_ga(sc, model, pop_size=10, n_gen=1)


@needs_data
def test_ga_runs_and_penalises_origin_excess(model):
    from optimiser.common import make_scenario
    from optimiser.ga import _batch_penalised_cost, solve_ga
    sc = make_scenario("40s_Ne", inventory_size=60, seed=5)
    res = solve_ga(sc, model, pop_size=20, n_gen=3)
    assert res.method == "ga_deap" and np.isclose(sum(res.weights), 1.0)

    wa = (sc.inventory["origin"] == "West_African").to_numpy()
    assert wa.any()
    heavy = np.where(wa, 1.0, 0.05)
    share = heavy[wa].sum() / heavy.sum()
    excess = share - sc.origin_caps["West_African"]
    assert excess > 0
    capped = _batch_penalised_cost(sc, [heavy], model)[0]
    sc.origin_caps = {}
    uncapped = _batch_penalised_cost(sc, [heavy], model)[0]
    assert capped - uncapped == pytest.approx(3000.0 * excess, rel=1e-6)


@needs_data
def test_confidence_policy_on_real_blend(model):
    from optimiser.common import make_scenario
    from optimiser.confidence import assess
    from optimiser.lp import solve_lp
    sc = make_scenario("40s_Ne", inventory_size=120, seed=11)
    res = solve_lp(sc, model)
    conf = assess(res, sc.spec, model)
    assert conf.level in {"HIGH", "MEDIUM", "LOW"}
    assert conf.support_ratio is not None and conf.support_ratio > 0
    if conf.support_ratio > 1:
        assert conf.level != "HIGH"


# --- monitoring ------------------------------------------------------
@needs_data
def test_monitor_quiet_on_history_and_fires_on_crop_shift(model, bales):
    from eval.monitor import PSI_WINDOW, check_triggers, simulate_crop_shift
    from models.dataset import build_xy, load_laydowns
    entry = dict(golden_metrics=None,
                 metrics={"csp": dict(mae=25.0), "u_pct": dict(mae=0.15),
                          "imperfections": dict(mae=18.0), "ends_down": dict(mae=0.45)})
    X, y = build_xy(load_laydowns().sort_values("date").tail(PSI_WINDOW), bales)
    quiet, _ = check_triggers(model, entry, X, y, bales, corrections=0)
    assert not {t.name: t.fired for t in quiet}["feature_drift_psi"]
    Xs, ys = simulate_crop_shift(X, 0.35)
    loud, detail = check_triggers(model, entry, Xs, ys, bales, corrections=25)
    fired = {t.name: t.fired for t in loud}
    assert fired["feature_drift_psi"] and fired["master_corrections"]
    assert detail["psi"]["w_mean_micronaire"] > 0.2


# --- explainer -------------------------------------------------------
def test_retriever_returns_hits():
    from explainer.retriever import retrieve
    hits, backend = retrieve("why does short fibre content hurt yarn strength", k=3)
    assert len(hits) == 3 and backend


@needs_data
def test_explainer_templated_fallback(monkeypatch, model):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from optimiser.common import make_scenario, naive_baseline
    from optimiser.lp import solve_lp
    from explainer.generate import explain_blend
    sc = make_scenario("40s_Ne", inventory_size=80, seed=7)
    res = solve_lp(sc, model)
    exp = explain_blend(sc, res, naive_baseline(sc, model))
    assert exp.llm_model == "templated-fallback"
    assert len(exp.rationale) > 200
