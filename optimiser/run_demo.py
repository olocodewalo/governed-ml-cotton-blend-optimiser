"""Run LP and GA optimisers on a demo scenario and print the comparison.

Run: ``python -m optimiser.run_demo``  (or ``make optimise``)
"""
from __future__ import annotations

import argparse
import json

from config import QUALITY_TARGETS
from optimiser.common import load_current_model, make_scenario, naive_baseline
from optimiser.ga import solve_ga
from optimiser.lp import solve_lp


def _summary(res, spec):
    return dict(
        method=res.method,
        price_inr_per_kg=res.price_inr_per_kg,
        in_band=res.in_band,
        feasible=res.feasible,
        n_bales=int(sum(1 for w in res.weights if w > 1e-4)),
        predicted={t: {k: round(v, 1) for k, v in res.predicted[t].items()} for t in QUALITY_TARGETS},
        binding=res.binding_constraints,
        note=res.note,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", default="40s_Ne")
    ap.add_argument("--inventory", type=int, default=120)
    ap.add_argument("--bias", default=None, choices=[None, "cheap", "premium"])
    ap.add_argument("--skip-ga", action="store_true")
    args = ap.parse_args()

    model = load_current_model()
    scenario = make_scenario(args.count, inventory_size=args.inventory, bias=args.bias)
    spec = scenario.spec

    base = naive_baseline(scenario, model)
    lp = solve_lp(scenario, model)
    out = {"target_count": args.count, "spec": spec,
           "naive_baseline": _summary(base, spec), "lp": _summary(lp, spec)}

    if not args.skip_ga:
        ga = solve_ga(scenario, model)
        out["ga"] = _summary(ga, spec)
        out["ga_vs_naive_saving_pct"] = round(
            100 * (base.price_inr_per_kg - ga.price_inr_per_kg) / base.price_inr_per_kg, 2)

    out["lp_vs_naive_saving_pct"] = round(
        100 * (base.price_inr_per_kg - lp.price_inr_per_kg) / base.price_inr_per_kg, 2)

    if not base.in_band:
        out["note"] = ("naive baseline is OUT OF BAND -- it is cheaper only because it "
                       "ignores the spec; the optimiser's blends are the cheapest that "
                       "actually meet quality. See eval/ for the matched-quality saving.")

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
