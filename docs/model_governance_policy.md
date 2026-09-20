# Model Governance Policy -- Cotton Blend Optimisation

Scope: the ML quality model, the linear surrogate, the optimiser rules, and the
LLM explainer prompt/KB. All are versioned artefacts under change control.

## 1. Model registry

Every trained quality model is recorded in `artifacts/model_registry.json` with:
version, timestamp, training-data hash, train/test row counts, full metrics,
`status` (candidate | approved | retired), and `approved_by` / `approved_at`.

- Training produces a **candidate** (`models/train.py` writes only the versioned
  artifact). It cannot be used for a real laydown: the app and optimiser load
  only the approved pointer and refuse to start without one.
- Promotion to **approved** is `make promote APPROVER="<name>"`
  (`models/promote.py`), which requires: golden-set metrics within thresholds
  (below), regression suite green, and a named approver.
- Promotion marks the previous approved model **retired** (its artifact is kept
  for rollback), copies the new artifact to `quality_model_current.joblib`, and
  re-freezes `eval/baseline.json`.

## 2. Golden set

- 50 held-out historical laydowns with known actual yarn QC, never used in
  training (`eval/harness.py::golden_laydowns` -- the most recent 50 by date).
- Refreshed only when >= 12 new months of data exist, as an explicit,
  reviewed change (it moves the goalposts).

## 3. Acceptance thresholds (candidate -> approved)

| Metric | Threshold |
|---|---|
| CSP MAE | <= 35 (approx. 1.3x the label noise floor) |
| U% MAE | <= 0.22 |
| Imperfections MAE | <= 28 |
| Ends-down MAE | <= 0.7 |
| P10-P90 coverage (each target) | 0.70 - 0.90 |
| Decision agreement with ground truth (golden) | >= 0.90 |
| **False-accept rate** (model says in-band, truth out) | **<= 0.05** |
| Optimiser pick lands in-band (golden) | >= 0.90 |

False-accept rate is the hard gate: shipping yarn that misses spec costs more
than any cotton saving. Thresholds live in `config.ACCEPTANCE_THRESHOLDS`, are
checked by `eval/policy.py` on every `make eval`, and **cannot be overridden** at
promotion.

With 50 golden laydowns a coverage estimate carries roughly +/-0.11 of sampling
error, so the harness reports a Wilson 95% interval next to each rate; a value
just outside the band is a signal to investigate, not proof of miscalibration.

## 4. Regression suite

`eval/regression_suite.py` compares `latest_metrics.json` to
`baseline.json` and **fails CI** if any tracked metric regresses beyond its
tolerance. Run on every change to data, physics/labels, model code, surrogate,
or optimiser -- `.github/workflows/ci.yml` runs data -> train -> golden set ->
regression gate -> tests on every push and pull request. `baseline.json` is
re-frozen only by `models/promote.py`. A regression can be accepted at
promotion only with a recorded CAB reason (`--accept-regression "<reason>"`),
which is written to the registry entry as `cab_note`.

## 5. Retrain triggers

Retrain (produce a new candidate) when any of:

- New linked data: >= 8 new weekly laydowns with yarn QC available.
- **Drift**: population stability index on any key feature > 0.2 vs training,
  or rolling 4-week prediction MAE > 1.5x golden MAE.
- >= 20 new master "Adjust" corrections logged (`eval/feedback_retrain.py`).
- A new origin or crop year enters inventory.
- Any change to `data/quality_physics.py` (prototype) or the real label
  definition.

`make monitor` (`eval/monitor.py`) checks the first four automatically against
the approved model: PSI of key blend features over the last 100 laydowns vs the
training snapshot stored inside the model artifact, rolling MAE over the last 8
laydowns vs the model's golden MAE, 'adjust' decisions logged against the model
version, and inventory origins absent from training. `--fail-on-trigger` exits
non-zero for a scheduled job. (A 100-laydown window keeps PSI's sampling floor,
~(bins-1)/n, well below the 0.2 alert.)

## 6. Confidence policy (auto-suggest gate)

A recommendation is **auto-suggestable** (HIGH) only if: predicted mean in band
with no violated hard constraint AND P10 clears the CSP floor AND the CSP P10-P90
width < 250 AND the blend is inside training support. Otherwise it is MEDIUM
("for review", master decision mandatory) or LOW (a limit is violated).

**Training support** is measured as the mean distance from the blend's
standardised feature vector to its 5 nearest training laydowns, divided by the
99th percentile of the same distance within the training set. A ratio > 1 means
the model is extrapolating; such a blend is never HIGH. Implemented in
`optimiser/confidence.py`, shared by the app and `optimiser/run_demo.py`, and the
level plus reasons are written to the audit log with each decision.

**Pre-run guards** (`optimiser/guards.py`), enforced by both optimisers:
the planning date's bale prices must be <= 7 days old (RAID R4), and
contamination-prone origins are hard-capped as a blend share (West African
<= 30%, RAID R9).

## 7. LLM explainer control

- The KB (`explainer/kb/*.md`) and system prompt are versioned; changes go
  through the CAB.
- The explainer is **advisory only** -- it never changes numbers and is not on
  the decision path. If the API is unavailable, a templated rationale is shown.
- RAG faithfulness/relevance checked on 10 sample runs (`eval/ragas_eval.py`)
  before a KB or prompt change ships.

## 8. Change Advisory Board

Model/surrogate/optimiser/KB changes are reviewed by ML Eng + Product + Yarn QC
Lead. The record: what changed, why, metric deltas vs baseline, rollback plan.

## 9. Audit

Every recommendation and master decision is written to
`artifacts/decisions.sqlite` (append-only in practice; only the `outcome_*`
fields are filled in later when yarn QC returns). Retained per the plant's data
policy; reviewed monthly by MLOps + Yarn QC.
