# Cotton Blend Optimisation for Spinning Mills

A learning / portfolio prototype at **enterprise-grade design, prototype scale**.

Raw cotton is 55-65% of yarn cost. Each week a mixing master decides the **bale
laydown** -- which bales, in what proportions -- trading ₹/kg against spun-yarn
quality and count consistency. Today that lives in one expert's head and a
spreadsheet, is not re-optimised as prices move, and leaves no record of why a
blend was chosen.

This repo builds the decision-support system around that choice:

```
                          COTTON BLEND OPTIMISATION  --  data -> ML -> optimise -> explain -> human -> learn

  ┌─────────────────┐     ┌──────────────────────┐     ┌───────────────────────┐     ┌────────────────────┐
  │  DATA LAYER     │     │  ML QUALITY MODEL    │     │  COST OPTIMISER       │     │  LLM EXPLAINER     │
  │ data/          │     │ models/             │     │ optimiser/           │     │ explainer/        │
  │                 │     │                      │     │                       │     │                    │
  │ synthetic bale  │ ──▶ │ blend profile ──▶    │ ──▶ │ guards: price age,    │ ──▶ │ retrieve KB notes  │
  │ tests (2000)    │ X,y │ LightGBM multi-out   │ f() │   origin caps         │     │ + run numbers      │
  │ + price date    │     │ CSP / U% / IPI /     │     │ LP  (PuLP, linear     │     │ ─▶ Claude API      │
  │ historical      │     │ ends-down            │     │      surrogate, CBC)  │     │ ─▶ 4-6 sentence    │
  │ laydowns (500)  │     │ + P10/P90 (5-fold    │     │ GA  (DEAP, full model)│     │    rationale       │
  │ + ACTUAL QC     │     │   CQR calibrated)    │     │ min ₹/kg  s.t.        │     │ (templated if no   │
  │ quality_physics │     │ + training-support & │     │  quality ∈ band, LTB, │     │  API key)          │
  │ = ground truth  │     │   drift snapshot     │     │  bale/origin caps     │     │ Ragas check (10)   │
  └─────────────────┘     └──────────────────────┘     └───────────┬───────────┘     └─────────┬──────────┘
        │                          ▲                              │ confidence policy          │
        │                          │                              ▼ HIGH / MEDIUM / LOW        ▼
        │                 ┌────────┴───────────┐        ┌───────────────────────────────────────────────┐
        │                 │  EVAL / FEEDBACK   │        │  HITL REVIEW UI   app/ (Streamlit)            │
        │                 │  eval/            │        │  blend table · predicted quality P10-P90 ·     │
        │                 │  golden set (50)   │◀───────│  cost vs baseline · rationale · confidence     │
        │                 │  policy thresholds │ logged │  [ Approve ] [ Adjust ] [ Reject ] + feedback  │
        │                 │  regression gate   │decisions───────────────────────────────────────────────┤
        │                 │  drift monitor     │        │  every decision ─▶ artifacts/decisions.sqlite  │
        │                 │  feedback_retrain  │        └───────────────────────────────────────────────┘
        │                 └────────────────────┘
        ▼
  ┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  GOVERNANCE WRAPPER   candidate ─▶ eval ─▶ promote (thresholds + regression gate + named approver)     │
  │  ─▶ approved pointer · CI on every push · drift/retrain triggers · RACI · CAB · Go/No-Go · audit log    │
  └───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**This is not a generative-AI use case.** The core is an ML regression feeding a
constrained optimiser. The LLM only writes the plain-language rationale, off the
decision path, and degrades to a template if the API key is absent.

---

## Quick start

```bash
make setup                        # pip install -r requirements.txt   (Python 3.11+)
make data                         # synthetic bales + historical laydowns -> data/*.parquet
make train                        # train quality model -> registered as a CANDIDATE
make eval                         # golden set + policy thresholds + regression gate
make promote APPROVER="<name>"    # gate, approve, move the current-model pointer, freeze baseline
make optimise                     # LP + GA on a demo scenario (approved model only)
make app                          # Streamlit HITL review UI (approved model only)
make monitor                      # PSI drift + rolling MAE + retrain triggers
make feedback                     # fold 20 simulated master corrections in, show metric delta
make test                         # pytest
```

Windows without GNU `make`: `make.bat <target>` (`make.bat promote "Name"`) or
run the module directly, e.g. `python -m data.generate`.

`requirements.txt` holds the core; `requirements-lock.txt` pins the exact
versions CI runs; `requirements-optional.txt` adds the sentence-transformers
retriever and MLflow (both optional, import-guarded).

Optional: set `ANTHROPIC_API_KEY` for real LLM rationales (otherwise a
deterministic templated rationale is used -- everything still runs).

---

## Repository layout

| Path | What |
|---|---|
| `data/generate.py` | synthetic bale + laydown generator (bales carry a `price_as_of` date) |
| `data/quality_physics.py` | **single source of truth** -- non-linear ground-truth yarn-quality physics |
| `data/features.py` | laydown (bales + weights) -> blend-aggregate feature vector (train/serve parity) |
| `models/quality_model.py` | LightGBM multi-output + P10/P90 heads, 5-fold CQR calibration, training-support + drift snapshot |
| `models/train.py` | train, evaluate, SHAP chart, register as candidate |
| `models/registry.py` | JSON model registry: candidate / approved / retired, approver, CAB note |
| `models/promote.py` | candidate -> approved gate |
| `optimiser/lp.py` | MILP, linear surrogate, adaptive safety margins, origin caps (PuLP + CBC) |
| `optimiser/ga.py` | genetic algorithm against the full non-linear model (DEAP) |
| `optimiser/guards.py` | price-freshness guard, contamination-prone origin caps |
| `optimiser/confidence.py` | confidence policy: HIGH / MEDIUM / LOW incl. out-of-support |
| `optimiser/common.py` | scenarios, baselines, blend evaluation, binding-constraint detection, model loading |
| `explainer/kb/` | 18 short fibre-science notes (hand-written) |
| `explainer/retriever.py` | sentence-transformers search, TF-IDF fallback |
| `explainer/generate.py` | Claude rationale, templated fallback |
| `app/streamlit_app.py` | HITL review UI |
| `app/decisions_db.py` | SQLite audit log |
| `eval/harness.py` | golden set: quality error, in-band decision quality, optimiser value, 95% intervals |
| `eval/policy.py` | acceptance thresholds from the governance policy |
| `eval/regression_suite.py` | fails if any metric regresses vs `eval/baseline.json` |
| `eval/monitor.py` | PSI drift, rolling MAE, correction count, new-origin retrain triggers |
| `eval/feedback_retrain.py` | corrections -> retrain -> measured delta |
| `eval/ragas_eval.py` | RAG faithfulness / relevance (proxy without API key) |
| `.github/workflows/ci.yml` | data -> train -> golden set -> regression gate -> tests |
| `docs/` | governance one-pagers (linked below) |

---

## Governance docs

- [90-day delivery plan](docs/90_day_delivery_plan.md) -- discovery -> data readiness -> shadow pilot -> Go/No-Go
- [RAID register](docs/raid_register.md) -- 9 risks with prototype implementation status
- [RACI](docs/raci.md) -- who owns model / data / approval / rollout
- [Model governance policy](docs/model_governance_policy.md) -- registry, golden set, thresholds, retrain triggers, confidence policy
- [Cost model](docs/cost_model.md) -- programme cost (incl. LLM/compute) vs 1-4% cotton saving
- [Value hypothesis & measurement plan](docs/value_hypothesis_and_measurement.md) -- baseline, targets, how measured, who verifies
- [LP vs metaheuristic](docs/lp_vs_metaheuristic.md) -- optimiser trade-offs and the training-support finding
- [Full technical write-up](docs/linkedin/article.md) -- every design choice and why, end to end

### Where each policy control lives

| Policy control | Enforced by |
|---|---|
| Training produces a candidate only; app/optimiser load approved model only | `models/train.py`, `optimiser/common.py::load_current_model` |
| Acceptance thresholds (not overridable) | `config.ACCEPTANCE_THRESHOLDS`, `eval/policy.py`, `models/promote.py` |
| Regression gate; override only with recorded CAB reason | `eval/regression_suite.py`, `models/promote.py --accept-regression` |
| CI on every push / PR | `.github/workflows/ci.yml` |
| Confidence policy; out-of-support blends never HIGH | `optimiser/confidence.py` |
| Refuse stale prices (RAID R4) | `optimiser/guards.py` (7 days) |
| Contamination-prone origin cap (RAID R9) | `config.ORIGIN_MAX_FRACTION`, LP constraint, GA penalty |
| Retrain triggers: PSI > 0.2, rolling MAE > 1.5x, >= 20 corrections, new origin | `eval/monitor.py` |
| Every decision logged with confidence + reasons | `app/decisions_db.py` |

---

## Case-study write-up

### The decision being supported

A weekly bale laydown for a target yarn count (20s / 30s / 40s / 60s Ne). The
master must keep predicted yarn quality -- CSP (count-strength product), U%
(evenness), imperfections, ends-down -- inside the count's spec band, keep the
blend's fibre profile close to the rolling 30-laydown average (so yarn count
doesn't wander), keep contamination-prone origins under their cap, and
otherwise pay as little as possible per kg.

### Why ML earns its place

Yarn quality is a **non-linear** function of the blend's aggregate fibre
profile. `data/quality_physics.py` encodes this as the ground truth: short-fibre
content penalises strength and evenness with a power > 1; micronaire *variance*
across the blend (mixing coarse and fine bales) hurts evenness and neps
super-linearly, independent of the mean; neps come from both immature fibre and
short fibre and the two interact. A linear cost rule cannot see any of this. The
ML model learns to approximate the physics from historical laydowns without ever
seeing the formula.

### Architecture in one line

ML quality model -> guarded cost optimiser (quality as a constraint) -> confidence
policy -> LLM explainer -> human Approve/Adjust/Reject -> every decision logged ->
golden-set eval + regression gate + drift monitor -> master corrections become
training signal.

### Results on the synthetic golden set (50 held-out historical laydowns, model v2)

| Metric | Result | Target |
|---|---|---|
| CSP MAE / label-noise floor | 22.9 / 28 | near the floor -> model has learned the physics |
| U% MAE | 0.14 | <= 0.22 |
| Imperfections MAE | 17.3 | <= 28 |
| Ends-down MAE | 0.46 | <= 0.7 |
| P10-P90 coverage (CSP / U% / IPI / ends) | 0.86 / 0.86 / 0.76 / 0.80 | 0.70-0.90 (n=50, so +/-~0.11 sampling error) |
| Decision agreement with ground truth | 0.94 | >= 0.90 |
| **False-accept rate** (model in-band, truth out) | **0.02** | <= 0.05 |
| Optimiser pick lands in-band (all 50 scenarios) | **0.90** (95% CI 0.79-0.96) | >= 0.90 |
| Cost saving vs historical, **at strictly matched quality** (n=35) | **3.0%** (95% CI 0.8-5.5%) | 1-4% is the defensible planning range |
| Cost saving vs historical, spec-band only | 16.0% (95% CI 13.3-18.5%) | (historical laydowns here are not cost-optimised) |
| Optimiser blends inside training support | 0 / 50 | -- every recommendation needs master review |

Numbers regenerate with `make data && make train && make eval`; the approved
model's report is frozen in `eval/baseline.json` and guarded by
`eval/regression_suite.py`.

**What changed from the first version, and why the headline got smaller.** The
first write-up reported a ~6% matched-quality saving and 0.93 in-band. Both came
from a 15-scenario sample (11 matched). Evaluated on all 50 golden laydowns with
the same optimiser, they are 3.2% and 0.92; adding the West African 30% cap
costs a further ~0.2 points, giving 3.0% and 0.90. The old model's
imperfections and ends-down intervals also under-covered (0.67 / 0.68), failing
the policy's own 0.70 floor; cross-conformal calibration fixed that without
changing point accuracy.

### Feedback loop

`make feedback` handicaps a "before" model (under-represents difficult high-SFC
blends), folds in 20 simulated mixing-master corrections in that region,
retrains, and reports the delta on the golden set and on a held-out high-SFC
slice. On this synthetic data the model is already near the irreducible noise
floor, so the deltas are small and **mixed** -- an honest outcome. The value is
the **instrumented loop**: corrections are captured, retraining is one command,
and the harness would catch a real regression. `make monitor` counts the
'adjust' decisions logged against the approved model and flags a retrain at 20.

### What is deliberately simplified

Synthetic data; a hand-written physics surrogate instead of a model trained on
real linked HVI/AFIS + yarn QC; single plant; four counts; no machine
integration; no price forecasting. The [90-day plan](docs/90_day_delivery_plan.md)
and [RAID register](docs/raid_register.md) treat **data readiness as the real
blocker**, which in a real mill it is.

### Honest limitations of the prototype

- **The optimiser leaves the model's training support.** The cheapest in-band
  blend is unlike any historical laydown (0 of 50 golden-scenario LP blends are
  in support). A tighter per-bale cap was tried and rejected: it cost the saving
  and in-band rate without fixing support. The mitigation is the confidence
  policy (never HIGH out of support, so HITL is mandatory) and the shadow pilot.
- The LP's linear surrogate genuinely under-models the variance penalties; the
  adaptive-margin loop and the full-model re-score in the UI expose the gap
  rather than hide it.
- The optimiser in-band rate sits exactly on its 0.90 threshold; its 95%
  interval reaches down to 0.79.
- The recent-laydown PSI for staple length is 0.19, just under the 0.2 alert,
  against an in-sample noise floor of ~0.05-0.10: worth watching, not yet drift.
