"""Promote a candidate model to approved (model governance policy, sections 1-4).

    python -m models.promote --approver "A. Mixing-Lead"
    python -m models.promote --approver "..." --version v3 \
        --accept-regression "CAB-12: origin cap costs ~1% saving by design"

Gates, in order:
  1. ``eval/latest_metrics.json`` must be the golden-set report for this version.
  2. Every acceptance threshold must hold. Not overridable -- false-accept rate
     is the hard gate.
  3. The regression suite vs ``eval/baseline.json`` must pass, unless a Change
     Advisory Board reason is recorded with ``--accept-regression``.
Then: mark approved (retiring the previous approved model), move the
``quality_model_current`` pointer, and freeze the new baseline.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys

from eval.policy import check_thresholds, print_checks
from eval.regression_suite import BASELINE, compare, print_rows
from eval.run_golden import LATEST
from models import registry
from optimiser.common import CURRENT_MODEL


def promote(version: str | None, approver: str, accept_regression: str | None = None) -> dict:
    if not LATEST.exists():
        raise SystemExit("no eval/latest_metrics.json -- run `make eval` first")
    report = json.loads(LATEST.read_text())
    version = version or report.get("model_version")
    if report.get("model_version") != version:
        raise SystemExit(f"latest_metrics.json is for {report.get('model_version')}, not {version}; "
                         f"run `python -m eval.run_golden --version {version}`")
    entry = registry.get(version)
    if entry["status"] != "candidate":
        raise SystemExit(f"{version} is {entry['status']}; only a candidate can be promoted")

    checks = check_thresholds(report)
    print_checks(checks)
    failed = [c.metric for c in checks if not c.ok]
    if failed:
        raise SystemExit(f"\nREFUSED: {version} fails acceptance thresholds: {', '.join(failed)}")

    cab_note = None
    if BASELINE.exists():
        base = json.loads(BASELINE.read_text())
        print(f"\nregression vs baseline model {base.get('model_version')}:")
        rows = compare(base, report)
        print_rows(rows)
        regressed = [r["metric"] for r in rows if r["regressed"]]
        if regressed:
            if not (accept_regression and accept_regression.strip()):
                raise SystemExit(f"REFUSED: regressions in {', '.join(regressed)}; fix them or record "
                                 f"a CAB decision with --accept-regression \"<reason>\"")
            cab_note = f"accepted regressions {regressed}: {accept_regression.strip()}"
            print(f"regressions accepted by CAB: {accept_regression.strip()}")

    approved = registry.approve(version, approver, cab_note=cab_note)
    shutil.copyfile(registry.artifact_abspath(approved), CURRENT_MODEL)
    BASELINE.write_text(json.dumps(report, indent=2))
    print(f"\nAPPROVED {version} by {approved['approved_by']} at {approved['approved_at']}")
    print(f"  current model pointer -> {CURRENT_MODEL.name}")
    print(f"  regression baseline frozen -> {BASELINE}")
    return approved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approver", required=True, help="named approver (recorded in the registry)")
    ap.add_argument("--version", help="candidate to promote (default: the one in latest_metrics.json)")
    ap.add_argument("--accept-regression", metavar="REASON",
                    help="CAB reason for accepting regression-suite failures")
    args = ap.parse_args()
    try:
        promote(args.version, args.approver, args.accept_regression)
    except SystemExit as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
