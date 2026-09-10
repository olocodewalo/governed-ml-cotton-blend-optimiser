"""Regression gate: fail (exit 1) if any tracked metric has regressed vs baseline.

Run after any change to data / model / physics / optimiser:
    python -m eval.run_golden        # refresh latest_metrics.json
    python -m eval.regression_suite  # compare to baseline.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
BASELINE = HERE / "baseline.json"
LATEST = HERE / "latest_metrics.json"

# metric path -> (direction, absolute tolerance)
#   "lower"  = smaller is better (errors)
#   "higher" = larger is better (coverage, savings, agreement)
CHECKS = {
    "quality.csp.mae": ("lower", 3.0),
    "quality.u_pct.mae": ("lower", 0.03),
    "quality.imperfections.mae": ("lower", 3.0),
    "quality.ends_down.mae": ("lower", 0.08),
    "decision.agreement": ("higher", 0.05),
    "decision.false_accept_rate": ("lower", 0.05),
    "optimiser.optimiser_blend_in_band_rate": ("higher", 0.1),
    "optimiser.mean_cost_saving_pct_vs_historical": ("higher", 2.0),
    "optimiser.mean_cost_saving_pct_at_matched_quality": ("higher", 2.0),
}


def _get(d: dict, path: str):
    for p in path.split("."):
        d = d[p]
    return d


def main() -> None:
    if not BASELINE.exists():
        print("no baseline.json -- run `python -m eval.run_golden --freeze-baseline` first")
        sys.exit(2)
    if not LATEST.exists():
        print("no latest_metrics.json -- run `python -m eval.run_golden` first")
        sys.exit(2)

    base = json.loads(BASELINE.read_text())
    latest = json.loads(LATEST.read_text())

    failures = []
    print(f"{'metric':<48} {'baseline':>12} {'latest':>12}  verdict")
    print("-" * 90)
    for path, (direction, tol) in CHECKS.items():
        b, l = _get(base, path), _get(latest, path)
        if direction == "lower":
            regressed = l > b + tol
        else:
            regressed = l < b - tol
        verdict = "REGRESSED" if regressed else "ok"
        if regressed:
            failures.append(path)
        print(f"{path:<48} {b:>12.3f} {l:>12.3f}  {verdict}")

    print("-" * 90)
    if failures:
        print(f"FAIL: {len(failures)} metric(s) regressed: {', '.join(failures)}")
        sys.exit(1)
    print("PASS: no regressions")


if __name__ == "__main__":
    main()
