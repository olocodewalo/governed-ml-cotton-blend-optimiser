"""Regression gate: fail (exit 1) if any tracked metric has regressed vs baseline.

Run after any change to data / model / physics / optimiser:
    python -m eval.run_golden        # refresh latest_metrics.json
    python -m eval.regression_suite  # compare to baseline.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.policy import get_path

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


def compare(base: dict, latest: dict, checks: dict | None = None) -> list[dict]:
    """One row per tracked metric: baseline, latest, regressed flag.

    A metric missing from the baseline (newly tracked) is reported, not failed.
    """
    checks = CHECKS if checks is None else checks
    rows = []
    for path, (direction, tol) in checks.items():
        l = get_path(latest, path)
        try:
            b = get_path(base, path)
        except KeyError:
            rows.append(dict(metric=path, baseline=None, latest=l, regressed=False))
            continue
        regressed = l > b + tol if direction == "lower" else l < b - tol
        rows.append(dict(metric=path, baseline=b, latest=l, regressed=regressed))
    return rows


def print_rows(rows: list[dict]) -> None:
    print(f"{'metric':<48} {'baseline':>12} {'latest':>12}  verdict")
    print("-" * 90)
    for r in rows:
        b = "new" if r["baseline"] is None else f"{r['baseline']:.3f}"
        verdict = "REGRESSED" if r["regressed"] else "ok"
        print(f"{r['metric']:<48} {b:>12} {r['latest']:>12.3f}  {verdict}")
    print("-" * 90)


def main() -> None:
    if not BASELINE.exists():
        print("no baseline.json -- run `python -m eval.run_golden --freeze-baseline` first")
        sys.exit(2)
    if not LATEST.exists():
        print("no latest_metrics.json -- run `python -m eval.run_golden` first")
        sys.exit(2)

    base = json.loads(BASELINE.read_text())
    latest = json.loads(LATEST.read_text())
    rows = compare(base, latest)
    print(f"baseline model {base.get('model_version')} vs latest model {latest.get('model_version')}")
    print_rows(rows)

    failed = [r["metric"] for r in rows if r["regressed"]]
    if failed:
        print(f"FAIL: {len(failed)} metric(s) regressed: {', '.join(failed)}")
        sys.exit(1)
    print("PASS: no regressions")


if __name__ == "__main__":
    main()
