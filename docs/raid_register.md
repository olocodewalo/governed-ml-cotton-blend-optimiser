# RAID Register -- Cotton Blend Optimisation

R = Risk, A = Assumption, I = Issue, D = Dependency. Scored L(1-5) x I(1-5).

## Risks

| # | Risk | L | I | Score | Mitigation | Owner | Prototype status |
|---|---|---|---|---|---|---|---|
| R1 | **Historical lab data not digitised / not linked to yarn QC** -- the model cannot be trained on reality. | 4 | 5 | 20 | Phase 1 is entirely data readiness; fall back to a smaller clean subset; budget data-eng time explicitly. | Data Eng | Open -- synthetic data in prototype |
| R2 | **SFC / maturity missing** (HVI only, no AFIS) for most bales, yet they are the strongest non-linear drivers. | 4 | 4 | 16 | Estimate SFC from length uniformity + micronaire with a documented error term; widen the quality model's uncertainty; flag estimated rows. | ML Eng | Open -- needs real HVI/AFIS audit |
| R3 | **Model over-trusted** -- master follows an out-of-band recommendation because "the tool said so". | 3 | 5 | 15 | Confidence policy (auto-suggest only above threshold); P10 must clear CSP floor; every rec labelled HIGH/MED/LOW; HITL mandatory below threshold. | Product + Mixing Master | **Implemented** -- `optimiser/confidence.py` (out-of-support never HIGH) |
| R4 | **Cotton price feed stale or wrong** -> optimiser minimises against wrong numbers. | 3 | 4 | 12 | Price data contract with freshness check; UI shows price timestamp; refuse to run on prices older than N days. | Data Eng | **Implemented** -- `optimiser/guards.py`, 7-day limit, app shows price age |
| R5 | **Distribution shift** -- new crop year / new origin the model never saw. | 3 | 4 | 12 | Monitor feature drift vs training; expand uncertainty out-of-support; retrain trigger in the governance policy. | ML Eng | **Implemented** -- `eval/monitor.py` (PSI, rolling MAE, new origin, corrections) |
| R6 | **Physics/ground-truth surrogate wrong** -- the synthetic prototype's `quality_physics.py` does not match the mill. | 2 | 5 | 10 | Prototype only; replaced by a model trained on real linked data in Phase 2; golden-set backtest is the check. | ML Eng | Accepted for prototype |
| R7 | **Optimiser exploits model blind spots** -- picks a weird cheap blend the model wrongly scores as good. | 3 | 4 | 12 | Constrain blends to stay near the training support (bale-count floor, per-bale cap, long-term-blend limits); GA re-scores with the full model; HITL. | ML Eng | **Implemented** -- out-of-support check (kNN distance to training blends) caps confidence at MEDIUM; a tighter per-bale cap was tested and rejected (cost + in-band loss) |
| R8 | **Master disengages** -- reviewing recommendations feels like extra work with no payoff. | 3 | 3 | 9 | Keep the UI to one screen; show the money saved; make "Adjust" fast; shadow period proves value before asking for trust. | Product | Partly -- one-screen UI; shadow pilot pending |
| R9 | **Contamination event** traced to an origin the optimiser increased. | 2 | 4 | 8 | Hard cap on high-risk origin fractions regardless of price; contamination notes in the KB and rationale. | Mixing Master | **Implemented** -- `config.ORIGIN_MAX_FRACTION`, hard LP constraint + GA penalty |

## Assumptions

- A1: The mill has >= 12 months of laydowns that can be linked to spun-yarn QC.
- A2: Spec bands per count can be agreed and are stable over the pilot.
- A3: The mixing master(s) will spend ~2 hrs/week on review during the pilot.
- A4: Bale-level price (or lot price) is available at laydown-planning time.
- A5: One plant, ring-spun cotton, 20s-60s Ne for the pilot.

## Issues (open)

- I1: AFIS coverage unknown until the data audit (Phase 1) -- blocks R2 sizing.
- I2: No agreed definition of "count-consistency excursion" yet -- needed for the KPI.

## Dependencies

- D1: Lab LIMS export access (HVI/AFIS).
- D2: Yarn QC system export (CSP, U%, IPI, ends-down) with lot linkage.
- D3: Procurement price feed / lot cost sheet.
- D4: Anthropic API access for the explainer (degrades to templated text if absent).
- D5: A machine/VM for weekly batch runs + the Streamlit review app.
