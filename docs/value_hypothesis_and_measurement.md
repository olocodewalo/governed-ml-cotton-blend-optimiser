# Value Hypothesis & Measurement Plan

## Hypothesis

> If a mixing master plans each weekly bale laydown with an ML-quality-model +
> cost-optimiser recommendation (reviewed, not automated), the mill will spend
> **1-4% less on raw cotton at the same spun-yarn quality and count
> consistency**, and the reasoning behind each blend will be recorded rather
> than held in one person's head.

Secondary: fewer count-consistency excursions; faster re-planning when cotton
prices move; a training-data flywheel from master corrections.

## Baseline (what we compare against)

| Baseline | Definition | Use |
|---|---|---|
| **B0 Historical actual** | The blend the master actually ran for a given past laydown, and its yarn QC. | Backtest / golden set. |
| **B1 Shadow master** | During the pilot, the blend the master chooses that week, unaware of the tool's pick. | Primary field baseline. |
| B2 Naive rule-of-thumb | Cheapest bales passing a coarse quality filter, equal weight. | Sanity lower bound in the demo UI only. |

The credible number is **optimiser vs B1**, measured at **matched or better
predicted quality** (the optimiser is constrained to meet the master's own
blend quality on every axis, then minimise cost).

## Metrics

| Metric | Definition | Target | Source |
|---|---|---|---|
| Cotton cost delta | (B1 blend ₹/kg - tool blend ₹/kg) / B1, at matched quality | 1-4% saving | `eval/harness.py::optimiser_value`, then weekly pilot log |
| Quality realised | Actual CSP, U%, IPI, ends-down of the produced lot vs its spec band | In-band rate not worse than baseline | Yarn QC system |
| Prediction accuracy | MAE per target on golden set / rolling 4-week | CSP <= 35, U% <= 0.22, IPI <= 28, ends <= 0.7 | `eval/run_golden` |
| False-accept rate | Tool says in-band, actual out | <= 5% | Golden set + pilot outcomes |
| Count consistency | Std dev of produced count across consecutive lots; count-excursion count | No worse than baseline; ideally lower | Yarn QC |
| Long-term-blend adherence | Fraction of laydowns within micronaire +-0.2 and strength +-1.5 of rolling avg | 100% (hard constraint) | Optimiser logs |
| Knowledge capture | Fraction of laydowns with a logged recommendation + rationale + outcome | 100% during pilot | `decisions.sqlite` |
| Feedback loop | Do >= 20 logged master corrections measurably move golden-set metrics? | Net non-regression; improvement on the targeted slice | `eval/feedback_retrain.py` |

## Measurement design

1. **Backtest (pre-pilot):** run the optimiser on 50 historical laydowns with
   their real inventory snapshot; compare cost at matched quality; check
   predicted vs actual QC. Gate: meets accuracy + in-band targets.
2. **Shadow pilot (6-10 weeks):** every planning cycle, log tool recommendation
   + master's independent choice + both predicted qualities. After production,
   attach the actual yarn QC to both (the master's is real; the tool's is
   counterfactual-predicted, flagged as such).
3. **Analysis:** paired comparison across weeks. Report mean cost delta with a
   confidence interval, quality realised, and consistency. Product/PM verifies;
   Yarn QC Lead signs off on the quality read.
4. **Go/No-Go (day 90):** proceed to supervised live use only if cost delta CI
   lower bound > 0 and quality/consistency not worse.

## Threats to validity

- Counterfactual quality for the tool's pick is *predicted*, not measured, until
  it is actually run -- widen with the model's own uncertainty.
- Week-to-week price and inventory variation -> use paired weekly comparison,
  not pooled averages.
- Master may unconsciously drift toward the tool's style once exposed -> keep
  the shadow choice genuinely blind where possible; note the risk.
- Small n over a 10-week pilot -> report intervals, not point claims; continue
  measuring after Go.
