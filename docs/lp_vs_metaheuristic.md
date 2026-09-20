# LP vs Metaheuristic for the blend optimiser

The repo ships both. They solve the same problem against different quality models.

## The problem

Choose bale proportions `w` (sum 1) to **minimise blend ₹/kg** subject to:
predicted yarn quality inside the count's band, blend fibre profile within the
long-term-blend drift limits, a per-bale share cap, a bale-count window, and a
hard cap on contamination-prone origins (West African <= 30%). Both optimisers
first refuse to run if bale prices are stale at the planning date.

The hard part: **predicted quality is non-linear** in `w`. It depends on weighted
*variances* (e.g. micronaire spread), which are quadratic in `w`, and the
physics penalties for short-fibre content and micronaire spread are super-linear.

## `optimiser/lp.py` -- MILP with a linear surrogate (PuLP + CBC)

- Fits an OLS surrogate (`optimiser/surrogate.py`) on only the features that are
  **linear in `w`**: weighted means and origin fractions. Variance terms are
  dropped.
- Solves a mixed-integer linear program: continuous `w_i`, binary `y_i` for
  "bale used", cardinality via `sum y_i <= max_bales`.
- Because the surrogate under-models the variance penalties, the LP is wrapped
  in a short **adaptive-margin loop**: solve -> re-score with the full ML model
  -> if out of band, inflate the safety margins and re-solve (up to 4 rounds).

**Pros:** fast (~1-3 s), globally optimal *against the surrogate*, deterministic,
easy to explain, gives exact shadow prices on the binding constraints.
**Cons:** the surrogate gap is real; needs the margin loop; cannot represent
"require the P10 estimate to clear the floor" cleanly; struggles when the
variance penalty is what's actually binding.

## `optimiser/ga.py` -- genetic algorithm (DEAP)

- Individual = weight vector over the inventory. Whole population scored in one
  **batched call to the full non-linear ML model** per generation (this is what
  makes it tractable).
- Constraint violations -> penalties on a single scalar fitness = price +
  penalties. Tournament selection, uniform crossover, sparsify/jitter mutation,
  elitist merge.

**Pros:** optimises against the exact model the master will see -- no surrogate
gap; handles any constraint you can compute (P10 floors, caps, non-linear
penalties); good at "spread the blend over many bales".
**Cons:** slower (~10-30 s for 100x40), only near-optimal, stochastic (seeded
here), no shadow prices, needs penalty tuning.

## Both leave the training support

The cheapest in-band blend is, almost by definition, unlike the historical
laydowns the quality model learned from: it concentrates on cheap bales and
unusual origin/maturity mixes. On the 50 golden scenarios only a small minority
of LP blends fall inside training support (kNN distance ratio <= 1). This is the
RAID R7 risk made measurable. Two responses were evaluated:

| Option | In-band (truth) | Saving at matched quality | In support |
|---|---|---|---|
| Per-bale cap 12% (kept) | 0.90 | ~3.0% | ~0% |
| Per-bale cap 6% (rejected) | 0.82 | ~0% | 8% |

Forcing the blend to look historical cost the saving and did not buy support.
The shipped mitigation is the confidence policy: an out-of-support blend is
never HIGH, so the mixing master reviews it, and the shadow pilot's actual yarn
QC is what earns the model trust in that region.

## When to use which

| Situation | Use |
|---|---|
| Fast weekly what-if, many scenarios | LP |
| The recommendation that goes to the master | GA (or LP then GA-polish) |
| Need shadow prices / "which constraint costs me most" | LP |
| Variance / P10 constraints are binding | GA |
| CI / regression harness (determinism, speed) | LP |

## Practical recommendation

Run the **LP first** for a fast, explainable feasible point and its shadow
prices, then **seed the GA** from it and let the GA polish against the full
model. The HITL UI shows both the LP's surrogate prediction and the full-model
re-score so the master sees the gap.
