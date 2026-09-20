"""Cost optimiser -- genetic algorithm (DEAP), scoring against the FULL ML model.

Individual = vector of non-negative weights over the inventory bales. It is
normalised to sum to 1 before evaluation, then the (non-linear, variance-aware)
quality model scores it. Constraint violations become penalties on a single
scalar fitness = price + penalties, which the GA minimises.

Slower and only near-optimal, but it optimises against the model that will
actually be shown to the mixing master -- no surrogate gap. See
docs/lp_vs_metaheuristic.md.

The whole population is scored in one batched ``model.predict`` call per
generation, which is what makes this tractable.
"""
from __future__ import annotations

import random

import numpy as np
import pandas as pd

from config import RANDOM_SEED
from data.features import blend_profile, feature_columns
from optimiser.common import Scenario, evaluate_blend, validate_scenario
from optimiser.guards import origin_excess, origin_masks

try:
    from deap import base, creator, tools
    _HAVE_DEAP = True
except Exception:  # pragma: no cover
    _HAVE_DEAP = False

if _HAVE_DEAP and not hasattr(creator, "FitnessMin"):
    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)


def _batch_penalised_cost(scenario: Scenario, weight_vectors: list[np.ndarray], model) -> np.ndarray:
    inv = scenario.inventory
    price = inv["price_inr_per_kg"].to_numpy(dtype=float)
    spec = scenario.spec
    rp = scenario.rolling_profile

    masks = origin_masks(inv, scenario.origin_caps)

    profiles, prices, n_used, excess = [], [], [], []
    for wv in weight_vectors:
        w = np.asarray(wv, dtype=float)
        w = w / w.sum() if w.sum() > 0 else np.full(len(w), 1.0 / len(w))
        profiles.append(blend_profile(inv, w))
        prices.append(float(np.sum(price * w)))
        n_used.append(int((w > 1e-4).sum()))
        excess.append(origin_excess(w, masks, scenario.origin_caps))

    X = pd.DataFrame(profiles, columns=feature_columns())
    pr = model.predict(X)
    prices = np.array(prices)

    pen = np.zeros(len(weight_vectors))
    pen += np.maximum(0.0, spec["min_csp"] - pr["csp"].to_numpy()) * 2.0
    pen += np.maximum(0.0, pr["u_pct"].to_numpy() - spec["max_u_pct"]) * 400.0
    pen += np.maximum(0.0, pr["imperfections"].to_numpy() - spec["max_imperfections"]) * 3.0
    pen += np.maximum(0.0, pr["ends_down"].to_numpy() - spec["max_ends_down"]) * 120.0

    mic = np.array([p["w_mean_micronaire"] for p in profiles])
    stg = np.array([p["w_mean_strength_gtex"] for p in profiles])
    pen += np.maximum(0.0, np.abs(mic - rp["w_mean_micronaire"]) - scenario.mic_tol) * 8000.0
    pen += np.maximum(0.0, np.abs(stg - rp["w_mean_strength_gtex"]) - scenario.strength_tol) * 3000.0
    pen += np.maximum(0, np.array(n_used) - scenario.max_bales) * 200.0
    pen += np.array(excess) * 3000.0
    return prices + pen


def solve_ga(scenario: Scenario, model, *, pop_size: int = 100, n_gen: int = 40,
             seed: int = RANDOM_SEED):
    if not _HAVE_DEAP:
        raise RuntimeError("deap not installed; `pip install deap`")
    validate_scenario(scenario)
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    n = len(scenario.inventory)
    target_bales = scenario.max_bales

    def make_ind():
        v = np.zeros(n)
        pick = np_rng.choice(n, size=target_bales, replace=False)
        v[pick] = np_rng.random(target_bales)
        return creator.Individual(v.tolist())

    def mutate(arr: np.ndarray) -> np.ndarray:
        arr = arr.copy()
        for _ in range(3):
            i = rng.randrange(n)
            if rng.random() < 0.5:
                arr[i] = 0.0
            else:
                arr[i] = max(0.0, arr[i] + np_rng.normal(0, 0.15))
        if (arr > 1e-4).sum() == 0:
            arr[rng.randrange(n)] = 1.0
        return arr

    def mate(a: np.ndarray, b: np.ndarray):
        mask = np_rng.random(n) < 0.5
        return np.where(mask, a, b), np.where(mask, b, a)

    pop = [np.array(ind) for ind in (make_ind() for _ in range(pop_size))]
    fit = _batch_penalised_cost(scenario, pop, model)
    best_i = int(np.argmin(fit))
    best, best_fit = pop[best_i].copy(), float(fit[best_i])

    for _ in range(n_gen):
        # tournament selection
        parents = []
        for _ in range(pop_size):
            cand = rng.sample(range(pop_size), 3)
            parents.append(pop[min(cand, key=lambda j: fit[j])].copy())
        # crossover + mutation
        children = []
        for i in range(0, pop_size, 2):
            a, b = parents[i], parents[min(i + 1, pop_size - 1)]
            if rng.random() < 0.6:
                a, b = mate(a, b)
            if rng.random() < 0.4:
                a = mutate(a)
            if rng.random() < 0.4:
                b = mutate(b)
            children.extend([a, b])
        children = children[:pop_size]
        cfit = _batch_penalised_cost(scenario, children, model)
        # elitist merge
        allp = pop + children
        allf = np.concatenate([fit, cfit])
        keep = np.argsort(allf)[:pop_size]
        pop = [allp[j] for j in keep]
        fit = allf[keep]
        if fit[0] < best_fit:
            best, best_fit = pop[0].copy(), float(fit[0])

    res = evaluate_blend(scenario, best, model, method="ga_deap")
    res.note = f"GA best of {pop_size}x{n_gen} vs full ML model; penalised cost={best_fit:.1f}"
    res.feasible = res.in_band
    return res
