"""Run the golden-set harness on a registered model and check the policy thresholds.

    python -m eval.run_golden                 # latest registered model (usually the new candidate)
    python -m eval.run_golden --version v2    # a specific model

Writes ``eval/latest_metrics.json`` and records the report on the registry
entry. The regression baseline is NOT frozen here: ``models.promote`` freezes it
when a model is approved (governance policy, section 4).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.harness import run_all
from eval.policy import check_thresholds, print_checks
from models import registry
from optimiser.common import load_model

LATEST = Path(__file__).parent / "latest_metrics.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", help="registered model version (default: latest registered)")
    args = ap.parse_args()

    model = load_model(args.version)
    report = run_all(model)
    report["model_version"] = model.version
    checks = check_thresholds(report)
    report["policy"] = dict(passes=all(c.ok for c in checks),
                            failures=[c.metric for c in checks if not c.ok])

    LATEST.write_text(json.dumps(report, indent=2))
    registry.record_golden(model.version, report)
    print(json.dumps(report, indent=2))
    print()
    print_checks(checks)
    status = registry.get(model.version)["status"]
    verdict = "PASSES" if report["policy"]["passes"] else "FAILS"
    print(f"\nmodel {model.version} ({status}) {verdict} the acceptance thresholds")


if __name__ == "__main__":
    main()
