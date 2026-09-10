"""Run the golden-set harness; optionally (re)freeze the regression baseline.

    python -m eval.run_golden                  # report only
    python -m eval.run_golden --freeze-baseline # write eval/baseline.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.harness import run_all
from optimiser.common import load_current_model

BASELINE = Path(__file__).parent / "baseline.json"
LATEST = Path(__file__).parent / "latest_metrics.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze-baseline", action="store_true")
    args = ap.parse_args()

    model = load_current_model()
    report = run_all(model)
    report["model_version"] = model.version

    LATEST.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

    if args.freeze_baseline:
        BASELINE.write_text(json.dumps(report, indent=2))
        print(f"\nfroze baseline -> {BASELINE}")


if __name__ == "__main__":
    main()
