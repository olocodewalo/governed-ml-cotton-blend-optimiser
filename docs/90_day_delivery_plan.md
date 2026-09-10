# 90-Day Delivery Plan -- Cotton Blend Optimisation

**Goal of the 90 days:** get from "one expert + a spreadsheet" to a shadow-mode
recommender whose blend picks are logged next to the master's, with a Go/No-Go
decision at day 90 on whether it may influence a real laydown.

| Phase | Days | Activities | Exit criteria |
|---|---|---|---|
| **0. Discovery** | 1-10 | Interview mixing master(s) & yarn QC. Map the current decision, its inputs, and where records live. Agree the target counts and their spec bands. Confirm cost model inputs. | Signed problem statement + spec bands; RACI drafted; data-source inventory. |
| **1. Data readiness** | 10-40 | Digitise HVI/AFIS bale records. Build the join: bale test -> laydown -> spun-yarn QC. Quantify missingness (esp. AFIS/SFC). Stand up the feature store (bale profiles + blend aggregates). Data contracts with the lab and QC. | >= 12 months of laydowns linked to yarn QC; documented gaps; contract tests green in CI. |
| **2. Model + optimiser** | 30-60 | Train the quality model on real linked data; calibrate uncertainty. Build LP + GA against real inventory snapshots. Backtest on held-out historical laydowns (golden set). | Quality MAE within agreed bound; optimiser lands in-band >= 90% on golden set; LP vs GA note. |
| **3. Shadow pilot** | 55-85 | Each week, run the optimiser on the real inventory and record its recommendation, predicted quality, confidence, and rationale **without acting on it**. Master reviews in the HITL UI (Approve/Adjust/Reject). Compare predicted vs actual yarn QC. | >= 6 weekly shadow runs; prediction error tracked; >= 20 master decisions logged with feedback. |
| **4. Go / No-Go** | 85-90 | Review: prediction accuracy, would-be cost saving at constant quality, count-consistency, master trust, failure modes. CAB sign-off. | Documented decision. If Go: confidence threshold set, first supervised live laydown scheduled. |

**Staffing:** 1 data engineer (60%), 1 ML engineer (60%), 0.5 domain lead
(mixing master's time), 0.2 product/PM, fractional MLOps.

**Key risks to the timeline:** AFIS/SFC data thinner than expected (mitigation:
HVI-based SFC estimation + wider uncertainty); yarn-QC linkage ambiguous
(mitigation: start with the lots that are cleanly traceable).

**Explicitly out of scope for 90 days:** automatic laydown execution, machine
integration, multi-plant rollout, price forecasting.
