"""Governance controls: thresholds, regression gate, registry lifecycle, promotion,
confidence policy, price/origin guards, drift monitoring, audit log."""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from config import ACCEPTANCE_THRESHOLDS, ORIGIN_MAX_FRACTION, PRICE_MAX_AGE_DAYS, QUALITY_TARGETS

pytestmark = pytest.mark.filterwarnings("ignore")


def _report(**over):
    """A golden-set report that passes every threshold; override leaves by path."""
    rep = dict(
        model_version="v9",
        quality={t: dict(mae=m, pi_coverage=0.8) for t, m in
                 dict(csp=20.0, u_pct=0.1, imperfections=15.0, ends_down=0.4).items()},
        decision=dict(agreement=0.95, false_accept_rate=0.02),
        optimiser=dict(optimiser_blend_in_band_rate=0.95,
                       mean_cost_saving_pct_vs_historical=15.0,
                       mean_cost_saving_pct_at_matched_quality=5.0),
    )
    for path, v in over.items():
        d = rep
        keys = path.split(".")
        for k in keys[:-1]:
            d = d[k]
        d[keys[-1]] = v
    return rep


# --- acceptance thresholds -----------------------------------------------------
def test_thresholds_pass_on_good_report():
    from eval.policy import failures
    assert failures(_report()) == []


@pytest.mark.parametrize("path,value", [
    ("decision.false_accept_rate", 0.06),
    ("quality.ends_down.pi_coverage", 0.68),     # the v1 failure
    ("quality.csp.pi_coverage", 0.95),           # over-wide bands fail too
    ("quality.csp.mae", 40.0),
    ("optimiser.optimiser_blend_in_band_rate", 0.85),
])
def test_thresholds_catch_each_failure(path, value):
    from eval.policy import failures
    assert [c.metric for c in failures(_report(**{path: value}))] == [path]


def test_every_policy_threshold_is_checked():
    from eval.policy import check_thresholds
    assert {c.metric for c in check_thresholds(_report())} == set(ACCEPTANCE_THRESHOLDS)


# --- regression gate -----------------------------------------------------------
def test_regression_compare_flags_only_real_regressions():
    from eval.regression_suite import compare
    base = _report()
    latest = _report(**{"quality.csp.mae": 24.0,                 # +4 > tol 3 -> regressed
                        "quality.u_pct.mae": 0.12,               # within tol
                        "decision.agreement": 0.99})             # better
    rows = {r["metric"]: r for r in compare(base, latest)}
    assert rows["quality.csp.mae"]["regressed"]
    assert not rows["quality.u_pct.mae"]["regressed"]
    assert not rows["decision.agreement"]["regressed"]


def test_regression_compare_tolerates_newly_tracked_metric():
    from eval.regression_suite import compare
    rows = compare({}, _report(), checks={"quality.csp.mae": ("lower", 1.0)})
    assert rows[0]["baseline"] is None and not rows[0]["regressed"]


# --- registry + promotion --------------------------------------------------------
@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Registry, metrics, baseline and current pointer all under tmp_path."""
    from models import promote, registry
    monkeypatch.setattr(registry, "MODEL_REGISTRY", tmp_path / "registry.json")
    monkeypatch.setattr(promote, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(promote, "BASELINE", tmp_path / "baseline.json")
    monkeypatch.setattr(promote, "CURRENT_MODEL", tmp_path / "current.joblib")

    def add(version, report):
        art = tmp_path / f"{version}.joblib"
        art.write_bytes(version.encode())
        registry.register(version=version, artifact_path=str(art), training_data_hash="h",
                          metrics={}, n_train=1, n_test=1)
        (tmp_path / "latest.json").write_text(json.dumps(report))
    return SimpleNamespace(path=tmp_path, add=add, registry=registry, promote=promote)


def test_approve_retires_previous_and_needs_a_name(sandbox):
    reg = sandbox.registry
    sandbox.add("v1", _report(model_version="v1"))
    sandbox.add("v2", _report(model_version="v2"))
    with pytest.raises(ValueError):
        reg.approve("v1", "  ")
    reg.approve("v1", "Lead A")
    reg.approve("v2", "Lead B")
    assert reg.get("v1")["status"] == "retired"
    assert reg.get("v2")["status"] == "approved" and reg.get("v2")["approved_by"] == "Lead B"


def test_promote_refuses_threshold_failure(sandbox):
    sandbox.add("v1", _report(model_version="v1", **{"decision.false_accept_rate": 0.2}))
    with pytest.raises(SystemExit, match="fails acceptance thresholds"):
        sandbox.promote.promote("v1", "Lead A", accept_regression="CAB cannot override this")
    assert sandbox.registry.get("v1")["status"] == "candidate"
    assert not (sandbox.path / "current.joblib").exists()


def test_promote_moves_pointer_freezes_baseline_and_gates_regressions(sandbox):
    sandbox.add("v1", _report(model_version="v1"))
    sandbox.promote.promote(None, "Lead A")
    assert (sandbox.path / "current.joblib").read_bytes() == b"v1"
    assert json.loads((sandbox.path / "baseline.json").read_text())["model_version"] == "v1"

    worse = _report(model_version="v2", **{"optimiser.mean_cost_saving_pct_at_matched_quality": 1.0})
    sandbox.add("v2", worse)
    with pytest.raises(SystemExit, match="regressions"):
        sandbox.promote.promote("v2", "Lead A")
    assert (sandbox.path / "current.joblib").read_bytes() == b"v1"

    sandbox.promote.promote("v2", "Lead A", accept_regression="CAB-7: origin cap, by design")
    assert (sandbox.path / "current.joblib").read_bytes() == b"v2"
    assert "CAB-7" in sandbox.registry.get("v2")["cab_note"]
    assert sandbox.registry.get("v1")["status"] == "retired"


def test_promote_refuses_metrics_for_another_version(sandbox):
    sandbox.add("v1", _report(model_version="v1"))
    sandbox.add("v2", _report(model_version="v2"))
    with pytest.raises(SystemExit, match="not v1"):
        sandbox.promote.promote("v1", "Lead A")


# --- price freshness + origin caps -------------------------------------------------
def _inv(ages, as_of="2024-12-10"):
    d = pd.Timestamp(as_of)
    return pd.DataFrame(dict(bale_id=[f"B{i}" for i in range(len(ages))],
                             price_as_of=[str((d - pd.Timedelta(days=a)).date()) for a in ages]))


def test_price_freshness_guard():
    from optimiser.guards import StalePriceError, check_price_freshness
    check_price_freshness(_inv([0, 3, PRICE_MAX_AGE_DAYS]), "2024-12-10")
    with pytest.raises(StalePriceError, match="older than"):
        check_price_freshness(_inv([0, PRICE_MAX_AGE_DAYS + 1]), "2024-12-10")
    with pytest.raises(StalePriceError, match="after the planning date"):
        check_price_freshness(_inv([-2]), "2024-12-10")
    with pytest.raises(StalePriceError, match="no price_as_of"):
        check_price_freshness(pd.DataFrame(dict(bale_id=["B0"])), "2024-12-10")


def test_origin_cap_violation_reported():
    from optimiser.guards import origin_cap_violations, origin_excess, origin_masks
    caps = {"West_African": 0.3}
    assert origin_cap_violations({"origin_frac_West_African": 0.2}, caps) == []
    assert origin_cap_violations({"origin_frac_West_African": 0.45}, caps)[0].startswith("VIOLATED")
    inv = pd.DataFrame(dict(origin=["West_African"] * 2 + ["US_Pima"] * 2))
    w = np.array([0.3, 0.2, 0.25, 0.25])
    assert origin_excess(w, origin_masks(inv, caps), caps) == pytest.approx(0.2)


# --- confidence policy ---------------------------------------------------------------
class _FakeModel:
    features = ["x"]
    train_ref_ = {"stub": True}

    def __init__(self, ratio):
        self.ratio = ratio

    def support_ratio(self, X):
        return np.array([self.ratio])


def _result(csp_mean=2300, p10=2260, p90=2340, in_band=True, binding=()):
    pred = {t: dict(mean=1.0, p10=0.9, p90=1.1) for t in QUALITY_TARGETS}
    pred["csp"] = dict(mean=csp_mean, p10=p10, p90=p90)
    return SimpleNamespace(predicted=pred, in_band=in_band, profile={"x": 0.0},
                           binding_constraints=list(binding))


SPEC = dict(min_csp=2200)


def test_confidence_high_only_when_everything_holds():
    from optimiser.confidence import assess
    c = assess(_result(), SPEC, _FakeModel(0.8))
    assert c.level == "HIGH" and c.auto_suggestable


def test_confidence_out_of_support_is_never_high():
    from optimiser.confidence import assess
    c = assess(_result(), SPEC, _FakeModel(1.4))
    assert c.level == "MEDIUM" and not c.auto_suggestable
    assert any("OUT OF TRAINING SUPPORT" in r for r in c.reasons)


@pytest.mark.parametrize("kw", [dict(p10=2150), dict(p10=2210, p90=2500)])
def test_confidence_medium_on_weak_p10_or_wide_band(kw):
    from optimiser.confidence import assess
    assert assess(_result(**kw), SPEC, _FakeModel(0.5)).level == "MEDIUM"


def test_confidence_low_on_any_violation():
    from optimiser.confidence import assess
    r = _result(binding=["VIOLATED origin cap West_African: 0.400 > 0.3"])
    assert assess(r, SPEC, _FakeModel(0.5)).level == "LOW"
    assert assess(_result(in_band=False), SPEC, _FakeModel(0.5)).level == "LOW"


# --- drift -------------------------------------------------------------------------
def test_psi_near_zero_for_same_distribution_and_high_for_shift():
    from eval.monitor import psi
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 5000)
    edges = np.quantile(ref, np.linspace(0, 1, 11))
    props = np.histogram(ref, bins=edges)[0] / len(ref)
    assert psi(edges, props, rng.normal(0, 1, 5000)) < 0.02
    assert psi(edges, props, rng.normal(0.8, 1, 5000)) > 0.2


# --- audit log -----------------------------------------------------------------------
def test_decisions_log_and_correction_count(tmp_path, monkeypatch):
    from app import decisions_db
    monkeypatch.setattr(decisions_db, "DECISIONS_DB", tmp_path / "d.sqlite")
    kw = dict(scenario={}, method="lp", recommendation={"B1": 1.0}, predicted={}, price=150.0,
              baseline_price=160.0, rationale="r", llm_model="templated-fallback",
              edited_weights=None, feedback="")
    decisions_db.log_decision(model_version="v2", user_action="adjust", **kw)
    decisions_db.log_decision(model_version="v2", user_action="approve", **kw)
    decisions_db.log_decision(model_version="v1", user_action="adjust", **kw)
    assert decisions_db.count_actions("adjust") == 2
    assert decisions_db.count_actions("adjust", "v2") == 1
    did = decisions_db.recent(1)[0]["id"]
    decisions_db.record_outcome(did, {"csp": 2300}, "ok")
    assert json.loads(decisions_db.recent(1)[0]["outcome_qc_json"]) == {"csp": 2300}


# --- harness statistics ---------------------------------------------------------------
def test_interval_helpers():
    from eval.harness import bootstrap_mean_ci, wilson_ci
    lo, hi = wilson_ci(45, 50)
    assert lo < 0.9 < hi and 0 <= lo and hi <= 1
    assert wilson_ci(0, 0) == [None, None]
    lo, hi = bootstrap_mean_ci([4.0, 5.0, 6.0, 5.5, 4.5])
    assert lo < 5.0 < hi
    assert bootstrap_mean_ci([1.0]) == [None, None]


def test_default_origin_cap_configured():
    assert 0 < ORIGIN_MAX_FRACTION["West_African"] < 1
