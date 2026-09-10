# Cost Model -- Cotton Blend Optimisation

Illustrative, for a single mid-size spinning mill. Replace bracketed numbers
with the plant's actuals. Currency: INR.

## Reference mill

| Parameter | Value |
|---|---|
| Yarn output | 10,000 tonnes/year |
| Average cotton cost | ₹190 /kg |
| Annual cotton spend | 10,000 t x 1000 x 190 = **₹190 crore** |
| Raw cotton as share of yarn cost | ~60% |

## Programme cost (Year 1)

| Item | Basis | Year-1 cost |
|---|---|---|
| Data engineering | 1 FTE x 6 months (build) + 0.3 FTE run | ₹22,00,000 |
| ML engineering | 1 FTE x 6 months + 0.3 FTE run | ₹24,00,000 |
| Domain lead (mixing master time) | 0.2 FTE | ₹6,00,000 |
| Product / PM | 0.2 FTE | ₹8,00,000 |
| MLOps / infra setup | 0.2 FTE | ₹6,00,000 |
| Compute (training + weekly batch + app) | 1 small always-on VM + burst | ₹1,50,000 |
| LLM API (explainer) | see below | ₹40,000 |
| Contingency | ~15% | ₹10,00,000 |
| **Total Year 1** | | **≈ ₹1.08 crore** |
| **Run-rate (Year 2+)** | ~1.2 FTE + infra + API | **≈ ₹45,00,000 /year** |

### LLM API detail

- ~1 explainer call per laydown; ~1 planning laydown/day/count, 4 counts ->
  ~1,000 calls/year, plus eval and re-runs -> ~3,000 calls/year.
- ~3-4k input tokens (KB snippets + run facts) + ~0.5k output per call.
- At Claude Sonnet pricing that is on the order of **₹10-15 per call** ->
  **~₹40,000/year**. Negligible next to the cotton spend; the explainer is not
  the cost driver. Falls back to templated text at ₹0 if disabled.

## Benefit

Saving = (cotton spend) x (share reachable by blend optimisation) x (% saved).

| Scenario | % cotton saved at constant quality | Annual saving |
|---|---|---|
| Conservative | 1.0% | ₹1.90 crore |
| Base | 2.0% | ₹3.80 crore |
| Optimistic | 3.5% | ₹6.65 crore |

The prototype's golden-set backtest shows ~6% at strictly matched quality
against a non-optimised historical baseline; **1-4% is the defensible planning
range** against a competent human baseline, because (a) the master already
captures much of the easy saving, (b) real inventories are more constrained than
the synthetic one, (c) uncertainty margins cost a little quality headroom.

## Net

| | Year 1 | Year 2+ (per year) |
|---|---|---|
| Cost | ₹1.08 cr | ₹0.45 cr |
| Benefit @ 1% (conservative) | ₹1.90 cr | ₹1.90 cr |
| **Net @ 1%** | **+₹0.82 cr** | **+₹1.45 cr** |
| Net @ 2% (base) | +₹2.72 cr | +₹3.35 cr |

Break-even is well under 1% cotton saving. Payback < 9 months in the base case.
Downside is bounded by the programme cost; the HITL gate prevents a bad blend
from turning the downside into scrapped yarn.

## What could erode the benefit

- Quality misses from over-aggressive optimisation -> scrap/claims (mitigated by
  P10 constraint + HITL + false-accept gate).
- Master overrides most recommendations -> saving not realised (measured in the
  shadow pilot before committing).
- Price feed lag -> optimising against stale numbers (freshness check).
