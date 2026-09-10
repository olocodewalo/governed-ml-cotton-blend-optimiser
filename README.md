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
  │ synthetic bale  │ ──▶ │ blend profile ──▶    │ ──▶ │ LP  (PuLP, linear     │ ──▶ │ retrieve KB notes  │
  │ tests (2000)    │ X,y │ LightGBM multi-out   │ f() │      surrogate,        │     │ + run numbers      │
  │ historical      │     │ CSP / U% / IPI /     │     │      MILP, CBC)        │     │ ─▶ Claude API      │
  │ laydowns (500)  │     │ ends-down            │     │ GA  (DEAP, full model)│     │ ─▶ 4-6 sentence    │
  │ + ACTUAL QC     │     │ + P10/P90 (conformal │     │ min ₹/kg  s.t.        │     │    rationale       │
  │ feature store   │     │   -calibrated)       │     │  quality ∈ band,      │     │ (templated if no   │
  │ quality_physics │     │ SHAP ─▶ docs/        │     │  |Δ vs rolling avg|,   │     │  API key)          │
  │ = ground truth  │     │ model registry(JSON) │     │  bale cap / count     │     │ Ragas check (10)   │
  └─────────────────┘     └──────────────────────┘     └───────────────────────┘     └─────────┬──────────┘
        │                          ▲                             │                            │
        │                          │                             ▼                            ▼
        │                 ┌────────┴───────────┐        ┌───────────────────────────────────────────────┐
        │                 │  EVAL / FEEDBACK   │        │  HITL REVIEW UI   app/ (Streamlit)            │
        │                 │  eval/            │        │  blend table · predicted quality P10-P90 ·     │
        │                 │  golden set (50)   │◀───────│  cost vs baseline · rationale · confidence     │
        │                 │  regression suite  │ logged │  [ Approve ] [ Adjust ] [ Reject ] + feedback  │
        │                 │  feedback_retrain  │ decisions ────────────────────────────────────────────┤
        │                 └────────────────────┘        │  every decision ─▶ artifacts/decisions.sqlite  │
        │                                               └───────────────────────────────────────────────┘
        │
        ▼
  ┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  GOVERNANCE WRAPPER   docs/   -- model registry + sign-off · golden set · regression gate ·            │
  │  confidence policy (auto-suggest only above threshold) · RACI · Change Advisory · Go/No-Go ·           │
  │  immutable-ish audit log · 90-day plan · RAID · cost model · value hypothesis                          │
  └───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**This is not a generative-AI use case.** The core is an ML regression feeding a
constrained optimiser. The LLM only writes the plain-language rationale, off the
decision path, and degrades to a template if the API key is absent.

---

## Quick start

```bash
make setup      # pip install -r requirements.txt   (Python 3.11+)
make data       # synthetic bales + historical laydowns -> data/*.parquet
make train      # train quality model, SHAP chart -> docs/, register in artifacts/
make optimise   # LP + GA on a demo scenario, printed side by side
make eval       # golden-set harness + regression gate
make app        # Streamlit HITL review UI
make feedback   # fold 20 simulated master corrections in, show metric delta
```

Windows without GNU `make`: use `make.bat <target>` or run the module directly,
e.g. `python -m data.generate`.

Optional: set `ANTHROPIC_API_KEY` for real LLM rationales (otherwise a
deterministic templated rationale is used -- everything still runs).

---

## Repository layout

| Path | What |
|---|---|
| `data/generate.py` | synthetic bale + laydown generator |
| `data/quality_physics.py` | **single source of truth** -- non-linear ground-truth yarn-quality physics |
| `data/features.py` | laydown (bales + weights) -> blend-aggregate feature vector (train/serve parity) |
| `models/quality_model.py` | LightGBM multi-output + P10/P90 quantile heads, split-conformal calibrated |
| `models/train.py` | train, evaluate, SHAP chart, register |
| `models/registry.py` | JSON model registry with sign-off fields |
| `optimiser/lp.py` | MILP, linear surrogate, adaptive safety margins (PuLP + CBC) |
| `optimiser/ga.py` | genetic algorithm against the full non-linear model (DEAP) |
| `optimiser/common.py` | scenarios, baselines, blend evaluation, binding-constraint detection |
| `explainer/kb/` | 18 short fibre-science notes (hand-written) |
| `explainer/retriever.py` | sentence-transformers search, TF-IDF fallback |
| `explainer/generate.py` | Claude rationale, templated fallback |
| `app/streamlit_app.py` | HITL review UI |
| `app/decisions_db.py` | SQLite audit log |
| `eval/harness.py` | golden-set: quality error, in-band decision quality, optimiser value |
| `eval/regression_suite.py` | fails if any metric regresses vs `eval/baseline.json` |
| `eval/feedback_retrain.py` | corrections -> retrain -> measured delta |
| `eval/ragas_eval.py` | RAG faithfulness / relevance (proxy without API key) |
| `docs/` | governance one-pagers (linked below) |

---

## Governance docs

- [90-day delivery plan](docs/90_day_delivery_plan.md) -- discovery -> data readiness -> shadow pilot -> Go/No-Go
- [RAID register](docs/raid_register.md) -- 9 risks, assumptions, issues, dependencies
- [RACI](docs/raci.md) -- who owns model / data / approval / rollout
- [Model governance policy](docs/model_governance_policy.md) -- registry, golden set, thresholds, retrain triggers, confidence policy
- [Cost model](docs/cost_model.md) -- programme cost (incl. LLM/compute) vs 1-4% cotton saving
- [Value hypothesis & measurement plan](docs/value_hypothesis_and_measurement.md) -- baseline, targets, how measured, who verifies
- [LP vs metaheuristic](docs/lp_vs_metaheuristic.md) -- optimiser trade-offs

---

## Case-study write-up

### The decision being supported

A weekly bale laydown for a target yarn count (20s / 30s / 40s / 60s Ne). The
master must keep predicted yarn quality -- CSP (count-strength product), U%
(evenness), imperfections, ends-down -- inside the count's spec band, keep the
blend's fibre profile close to the rolling 30-laydown average (so yarn count
doesn't wander), and otherwise pay as little as possible per kg.

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

ML quality model -> cost optimiser (quality as a constraint) -> LLM explainer ->
human Approve/Adjust/Reject -> every decision logged -> golden-set eval +
regression gate -> master corrections become training signal.

### Results on the synthetic golden set (50 held-out historical laydowns)

| Metric | Result | Target |
|---|---|---|
| CSP MAE / label-noise floor | 22.9 / 28 | near the floor -> model has learned the physics |
| U% MAE | 0.14 | -- |
| Imperfections MAE | 17.3 | -- |
| Ends-down MAE | 0.46 | -- |
| P10-P90 coverage (CSP / U% / IPI / ends) | 0.82 / 0.80 / 0.72 / 0.68 | ~0.80 |
| Decision agreement with ground truth | 0.94 | -- |
| **False-accept rate** (model in-band, truth out) | **0.02** | <= 0.05 |
| Optimiser pick lands in-band | **0.93** | >= 0.90 |
| Cost saving vs historical, **at strictly matched quality** | **~6%** | 1-4% is the defensible planning range vs a competent human |
| Cost saving vs historical, spec-band only | ~19% | (historical laydowns here are not cost-optimised) |

Numbers regenerate with `make data && make train && make eval`; they are frozen
in `eval/baseline.json` and guarded by `eval/regression_suite.py`.

### Feedback loop

`make feedback` handicaps a "before" model (under-represents difficult high-SFC
blends), folds in 20 simulated mixing-master corrections in that region,
retrains, and reports the delta on the golden set and on a held-out high-SFC
slice. On this synthetic data the model is already near the irreducible noise
floor, so the deltas are small and **mixed** (imperfections and ends-down
improve; CSP is within noise) -- an honest outcome. The value is the
**instrumented loop**: corrections are captured, retraining is one command, and
the harness would catch a real regression.

### What is deliberately simplified

Synthetic data; a hand-written physics surrogate instead of a model trained on
real linked HVI/AFIS + yarn QC; single plant; four counts; no machine
integration; no price forecasting. The [90-day plan](docs/90_day_delivery_plan.md)
and [RAID register](docs/raid_register.md) treat **data readiness as the real
blocker**, which in a real mill it is.

### Honest limitations of the prototype

- The optimiser can exploit blind spots in the ML model; mitigated by keeping
  blends near training support (bale-count floor, per-bale cap, long-term-blend
  limits), by the GA re-scoring with the full model, and by mandatory HITL.
- The LP's linear surrogate genuinely under-models the variance penalties; the
  adaptive-margin loop and the full-model re-score in the UI expose the gap
  rather than hide it.
- Interval calibration is marginal on the smaller targets (imperfections,
  ends-down) with only ~380 training laydowns.
