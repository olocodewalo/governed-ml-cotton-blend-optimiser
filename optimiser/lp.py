"""Cost optimiser -- LP/MILP formulation (PuLP + CBC).

minimise   sum_i price_i * w_i
s.t.       sum_i w_i = 1
           w_i <= w_cap * y_i          (y_i binary: bale i used)
           w_i >= w_floor * y_i
           sum_i y_i <= max_bales
           sum_i y_i >= min_bales
           surrogate_CSP(w)      >= min_csp    + margin
           surrogate_U(w)        <= max_u_pct  - margin
           surrogate_imperf(w)   <= max_imperf - margin
           surrogate_ends(w)     <= max_ends   - margin
           |sum_i mic_i  w_i - rolling_mic| <= mic_tol
           |sum_i str_i  w_i - rolling_str| <= strength_tol

The linear surrogate under-models the non-linear variance penalties, so the LP
is wrapped in a short adaptive loop: solve, re-score the blend with the full ML
model, and if it fell outside the real spec band, inflate the safety margins and
re-solve (a few times).
"""
from __future__ import annotations

import numpy as np
import pulp

from config import MIN_BALES_IN_LAYDOWN
from optimiser.common import Scenario, evaluate_blend
from optimiser.surrogate import LinearSurrogate

# Starting safety margins (absorb surrogate-vs-full-model gap). Sized from
# typical surrogate error; the adaptive loop scales them up if needed.
_MARGIN0 = dict(csp=40.0, u_pct=0.20, imperfections=18.0, ends_down=0.6)


def _build_and_solve(scenario, surrogate, mg, w_cap, w_floor, time_limit):
    inv = scenario.inventory
    n = len(inv)
    price = inv["price_inr_per_kg"].to_numpy(dtype=float)
    mic = inv["micronaire"].to_numpy(dtype=float)
    stg = inv["strength_gtex"].to_numpy(dtype=float)
    spec = scenario.spec
    rp = scenario.rolling_profile

    prob = pulp.LpProblem("cotton_blend", pulp.LpMinimize)
    w = [pulp.LpVariable(f"w_{i}", lowBound=0, upBound=w_cap) for i in range(n)]
    y = [pulp.LpVariable(f"y_{i}", cat="Binary") for i in range(n)]

    prob += pulp.lpSum(price[i] * w[i] for i in range(n))
    prob += pulp.lpSum(w) == 1
    for i in range(n):
        prob += w[i] <= w_cap * y[i]
        prob += w[i] >= w_floor * y[i]
    prob += pulp.lpSum(y) <= scenario.max_bales
    prob += pulp.lpSum(y) >= min(MIN_BALES_IN_LAYDOWN, scenario.max_bales)

    for target, sense, limit in [
        ("csp", "min", spec["min_csp"] + mg["csp"]),
        ("u_pct", "max", spec["max_u_pct"] - mg["u_pct"]),
        ("imperfections", "max", spec["max_imperfections"] - mg["imperfections"]),
        ("ends_down", "max", spec["max_ends_down"] - mg["ends_down"]),
    ]:
        per_bale, const = surrogate.linear_expr_coeffs(target, inv)
        expr = const + pulp.lpSum(per_bale[i] * w[i] for i in range(n))
        prob += (expr >= limit) if sense == "min" else (expr <= limit)

    prob += pulp.lpSum(mic[i] * w[i] for i in range(n)) <= rp["w_mean_micronaire"] + scenario.mic_tol
    prob += pulp.lpSum(mic[i] * w[i] for i in range(n)) >= rp["w_mean_micronaire"] - scenario.mic_tol
    prob += pulp.lpSum(stg[i] * w[i] for i in range(n)) <= rp["w_mean_strength_gtex"] + scenario.strength_tol
    prob += pulp.lpSum(stg[i] * w[i] for i in range(n)) >= rp["w_mean_strength_gtex"] - scenario.strength_tol

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit))
    return pulp.LpStatus[status], np.array([pulp.value(v) or 0.0 for v in w])


def solve_lp(scenario: Scenario, model, surrogate: LinearSurrogate | None = None,
             w_cap: float = 0.12, w_floor: float = 0.004, time_limit: int = 30,
             use_margin: bool = True, max_rounds: int = 4):
    surrogate = surrogate or LinearSurrogate.fit()
    mg = dict(_MARGIN0) if use_margin else {k: 0.0 for k in _MARGIN0}

    last = None
    for rnd in range(max_rounds):
        status_str, weights = _build_and_solve(scenario, surrogate, mg, w_cap, w_floor, time_limit)
        if status_str != "Optimal":
            if last is not None:
                return last
            return _infeasible(scenario, model, status_str)
        res = evaluate_blend(scenario, weights, model, method="lp_pulp")
        res.note = f"LP optimal vs linear surrogate (round {rnd + 1}); margins={ {k: round(v, 2) for k, v in mg.items()} }"
        last = res
        if res.in_band or not use_margin:
            return res
        for k in mg:  # tighten and retry
            mg[k] *= 1.8
    last.note += " -- still marginally out of band after adaptive rounds; GA recommended"
    return last


def _infeasible(scenario, model, status_str):
    res = evaluate_blend(scenario, np.ones(len(scenario.inventory)), model, "lp_pulp")
    res.feasible = False
    res.in_band = False
    res.note = f"LP {status_str}: no blend satisfies the spec band with this inventory"
    return res
