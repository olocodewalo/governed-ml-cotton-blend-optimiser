"""HITL review UI for the Cotton Blend Optimiser.

    streamlit run app/streamlit_app.py     (or: make app)

Flow: pick a scenario -> run the optimiser -> review the recommended blend,
predicted quality with P10-P90, cost vs a naive baseline, and the LLM rationale
-> Approve / Adjust / Reject with feedback. Every action is written to the
SQLite audit log.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import streamlit as st

from config import ORIGIN_MAX_FRACTION, PRICE_MAX_AGE_DAYS, QUALITY_TARGETS, YARN_COUNT_SPECS, anthropic_key
from app.decisions_db import log_decision, recent
from explainer.generate import explain_blend
from models import registry
from models.dataset import load_bales
from optimiser.common import (NoApprovedModelError, evaluate_blend, load_current_model,
                              make_scenario, naive_baseline)
from optimiser.confidence import assess
from optimiser.ga import solve_ga
from optimiser.guards import StalePriceError, price_age_days
from optimiser.lp import solve_lp

st.set_page_config(page_title="Cotton Blend Optimiser -- HITL Review", layout="wide")


@st.cache_resource
def _model():
    return load_current_model()


@st.cache_data
def _price_sheet_date():
    return pd.to_datetime(load_bales()["price_as_of"]).max().date()


def _quality_table(result, spec):
    rows = []
    limits = dict(csp=("min", spec["min_csp"]), u_pct=("max", spec["max_u_pct"]),
                  imperfections=("max", spec["max_imperfections"]),
                  ends_down=("max", spec["max_ends_down"]))
    for t in QUALITY_TARGETS:
        p = result.predicted[t]
        sense, lim = limits[t]
        ok = (p["mean"] >= lim) if sense == "min" else (p["mean"] <= lim)
        rows.append(dict(metric=t, P10=round(p["p10"], 1), mean=round(p["mean"], 1),
                         P90=round(p["p90"], 1), spec=f"{sense} {lim}",
                         status="OK" if ok else "OUT"))
    return pd.DataFrame(rows)


st.title("Cotton Blend Optimisation -- Human-in-the-Loop Review")

try:
    model = _model()
except NoApprovedModelError as e:
    st.error(str(e))
    st.stop()

entry = registry.get(model.version)
st.caption(f"quality model **{model.version}** ({entry['status']}"
           f"{', approved by ' + entry['approved_by'] if entry.get('approved_by') else ''}) "
           f"| LLM: {'Anthropic API' if anthropic_key() else 'templated fallback (no ANTHROPIC_API_KEY)'}")

with st.sidebar:
    st.header("Scenario")
    count = st.selectbox("Target yarn count", list(YARN_COUNT_SPECS), index=2)
    inv_size = st.slider("Bale inventory available", 60, 300, 120, 10)
    bias = st.selectbox("Inventory skew", ["none", "cheap", "premium"], index=0)
    seed = st.number_input("Scenario seed", value=20260910, step=1)
    plan_date = st.date_input("Planning date", value=_price_sheet_date(),
                              help=f"The optimiser refuses to run on prices older than "
                                   f"{PRICE_MAX_AGE_DAYS} days at this date.")
    method = st.radio("Optimiser", ["LP (PuLP + linear surrogate)", "GA (DEAP + full ML model)"])
    run = st.button("Run optimiser", type="primary")
    st.divider()
    spec = YARN_COUNT_SPECS[count]
    st.write("**Spec band**")
    st.json(spec)
    st.write("**Origin caps (contamination)**")
    st.json(ORIGIN_MAX_FRACTION)

if run:
    scenario = make_scenario(count, inventory_size=int(inv_size), seed=int(seed),
                             bias=None if bias == "none" else bias, as_of=pd.Timestamp(plan_date))
    try:
        with st.spinner("optimising..."):
            baseline = naive_baseline(scenario, model)
            if method.startswith("LP"):
                result = solve_lp(scenario, model)
            else:
                result = solve_ga(scenario, model)
            explanation = explain_blend(scenario, result, baseline)
    except StalePriceError as e:
        st.session_state.pop("result", None)
        st.error(f"Refusing to optimise: {e}")
        st.stop()
    st.session_state.update(scenario=scenario, result=result, baseline=baseline,
                            explanation=explanation, model_version=model.version)
    st.session_state.pop("rescored", None)

if "result" in st.session_state:
    scenario = st.session_state["scenario"]
    result = st.session_state["result"]
    baseline = st.session_state["baseline"]
    explanation = st.session_state["explanation"]
    spec = scenario.spec

    conf = assess(result, spec, model)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Blend cost", f"₹{result.price_inr_per_kg:.1f}/kg",
              f"{result.price_inr_per_kg - baseline.price_inr_per_kg:+.1f} vs naive")
    saving = 100 * (baseline.price_inr_per_kg - result.price_inr_per_kg) / baseline.price_inr_per_kg
    c2.metric("vs naive baseline", f"{saving:+.1f}%",
              help="The naive rule-of-thumb blend. Comparable only when it is itself in band.")
    c3.metric("In spec band?", "YES" if result.in_band else "NO")
    c4.metric("Confidence", conf.level)
    (st.success if conf.level == "HIGH" else st.warning if conf.level == "MEDIUM" else st.error)(conf.summary)
    if not baseline.in_band:
        st.info(f"The naive baseline blend (₹{baseline.price_inr_per_kg:.1f}/kg) is **out of the spec "
                f"band**, so it is cheaper only because it misses quality — the percentage above is not "
                f"a like-for-like saving. The defensible number is the golden-set saving at matched "
                f"quality (eval/baseline.json), not this one.")
    ages = price_age_days(scenario.inventory, scenario.planning_date)
    st.caption(f"planning date {scenario.planning_date.date()} · bale prices {int(ages.min())}-"
               f"{int(ages.max())} days old (limit {PRICE_MAX_AGE_DAYS})")
    if not result.feasible:
        st.error(result.note)

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Recommended blend")
        wt = result.weight_table(scenario.inventory)
        st.dataframe(wt, use_container_width=True, height=340)
        st.caption(f"{len(wt)} bales · method: {result.method} · {result.note}")

        st.subheader("Predicted quality (P10 / mean / P90)")
        st.dataframe(_quality_table(result, spec), use_container_width=True)
        st.caption("Binding / violated: " + (", ".join(result.binding_constraints) or "none"))

    with right:
        st.subheader("Rationale")
        st.write(explanation.rationale)
        st.caption(f"retriever: {explanation.retriever_backend} · model: {explanation.llm_model} · "
                   f"sources: {', '.join(s['id'] for s in explanation.sources)}")

        st.subheader("Fibre profile vs rolling average")
        rp = scenario.rolling_profile
        prof = result.profile
        st.dataframe(pd.DataFrame([
            dict(property="micronaire", blend=round(prof["w_mean_micronaire"], 2),
                 rolling=round(rp["w_mean_micronaire"], 2), limit=f"±{scenario.mic_tol}"),
            dict(property="strength g/tex", blend=round(prof["w_mean_strength_gtex"], 2),
                 rolling=round(rp["w_mean_strength_gtex"], 2), limit=f"±{scenario.strength_tol}"),
            dict(property="staple mm", blend=round(prof["w_mean_staple_length_mm"], 2),
                 rolling=round(rp["w_mean_staple_length_mm"], 2), limit="-"),
            dict(property="SFC %", blend=round(prof["w_mean_short_fibre_content_pct"], 2),
                 rolling=round(rp["w_mean_short_fibre_content_pct"], 2), limit="-"),
            dict(property="effective bales", blend=round(prof["n_bales_effective"], 1),
                 rolling=round(rp["n_bales_effective"], 1), limit="-"),
        ]), use_container_width=True)

    st.divider()
    st.subheader("Decision")
    action = st.radio("Action", ["approve", "adjust", "reject"], horizontal=True)

    edited = None
    if action == "adjust":
        st.caption("Edit weights (%). They are renormalised on submit; the ML model re-scores.")
        wt = result.weight_table(scenario.inventory).copy()
        edited_df = st.data_editor(wt[["bale_id", "weight_pct", "origin",
                                       "short_fibre_content_pct", "price_inr_per_kg"]],
                                   use_container_width=True, height=300, key="editor")
        if st.button("Re-score edited blend"):
            inv = scenario.inventory
            w = np.zeros(len(inv))
            for _, r in edited_df.iterrows():
                pos = inv.index[inv["bale_id"] == r["bale_id"]]
                if len(pos):
                    w[pos[0]] = max(float(r["weight_pct"]), 0.0)
            if w.sum() > 0:
                rescored = evaluate_blend(scenario, w, model, "master_adjusted")
                st.session_state["rescored"] = rescored
        if "rescored" in st.session_state:
            rs = st.session_state["rescored"]
            rs_conf = assess(rs, spec, model)
            st.write(f"Re-scored cost: ₹{rs.price_inr_per_kg:.1f}/kg · in band: {rs.in_band} · "
                     f"confidence: {rs_conf.level}")
            st.dataframe(_quality_table(rs, spec), use_container_width=True)
            edited = {b: w for b, w in zip(rs.bale_ids, rs.weights) if w > 1e-4}

    feedback = st.text_area("Feedback / reason (becomes training signal for 'adjust' & 'reject')")

    if st.button("Submit decision", type="primary"):
        rec = {b: w for b, w in zip(result.bale_ids, result.weights) if w > 1e-4}
        did = log_decision(
            scenario=dict(target_count=scenario.target_count, spec=spec,
                          inventory_size=len(scenario.inventory),
                          planning_date=str(scenario.planning_date.date()),
                          origin_caps=scenario.origin_caps,
                          confidence=conf.level, confidence_reasons=conf.reasons,
                          support_ratio=conf.support_ratio),
            model_version=st.session_state["model_version"],
            method=result.method,
            recommendation=rec,
            predicted={t: result.predicted[t] for t in QUALITY_TARGETS},
            price=result.price_inr_per_kg,
            baseline_price=baseline.price_inr_per_kg,
            rationale=explanation.rationale,
            llm_model=explanation.llm_model,
            user_action=action,
            edited_weights=edited,
            feedback=feedback,
        )
        st.success(f"Logged decision #{did} to the audit trail.")

st.divider()
with st.expander("Recent decisions (audit log)"):
    rows = recent(20)
    if rows:
        st.dataframe(pd.DataFrame(rows)[["id", "ts", "method", "user_action",
                                         "price_inr_per_kg", "baseline_price",
                                         "model_version", "feedback"]],
                     use_container_width=True)
    else:
        st.write("No decisions logged yet.")
