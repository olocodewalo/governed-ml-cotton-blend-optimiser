# Model Governance Policy -- Cotton Blend Optimisation

Scope: the ML quality model, the linear surrogate, the optimiser rules, and the
LLM explainer prompt/KB. All are versioned artefacts under change control.

## 1. Model registry

Every trained quality model is recorded in `artifacts/model_registry.json` with:
version, timestamp, training-data hash, train/test row counts, full metrics,
`status` (candidate | approved | retired), and `approved_by` / `approved_at`.

- Training produces a **candidate**. It cannot be used for a real laydown.
- Promotion to **approved** requires: golden-set metrics within thresholds
  (below), regression suite green, and a named approver (`registry.approve()`).
- The app and optimiser load `quality_model_current.joblib`; promoting a model
  updates that pointer. The previous approved model is kept for rollback.

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
than any cotton saving.

## 4. Regression suite

`eval/regression_suite.py` compares `latest_metrics.json` to
`baseline.json` and **fails CI** if any tracked metric regresses beyond its
tolerance. Run on every change to data, physics/labels, model code, surrogate,
or optimiser. `baseline.json` is re-frozen only alongside an approved model
promotion.

## 5. Retrain triggers

Retrain (produce a new candidate) when any of:

- New linked data: >= 8 new weekly laydowns with yarn QC available.
- **Drift**: population stability index on any key feature > 0.2 vs training,
  or rolling 4-week prediction MAE > 1.5x golden MAE.
- >= 20 new master "Adjust" corrections logged (`eval/feedback_retrain.py`).
- A new origin or crop year enters inventory.
- Any change to `data/quality_physics.py` (prototype) or the real label
  definition.

## 6. Confidence policy (auto-suggest gate)

A recommendation is **auto-suggestable** only if: predicted mean in band AND
P10 clears the CSP floor AND the CSP P10-P90 width < 250. Otherwise it is shown
"for review" and a master decision is mandatory. Out-of-support blends (feature
vector far from training) are always MED/LOW.

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
