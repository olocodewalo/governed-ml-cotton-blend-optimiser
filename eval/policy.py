"""Acceptance-threshold check (model governance policy, section 3).

A candidate model may be promoted only if every threshold in
``config.ACCEPTANCE_THRESHOLDS`` holds on its golden-set report.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import ACCEPTANCE_THRESHOLDS


def get_path(d: dict, path: str):
    for p in path.split("."):
        d = d[p]
    return d


@dataclass
class Check:
    metric: str
    value: float
    rule: str
    ok: bool


def check_thresholds(report: dict, thresholds: dict | None = None) -> list[Check]:
    thresholds = ACCEPTANCE_THRESHOLDS if thresholds is None else thresholds
    out = []
    for path, (kind, limit) in thresholds.items():
        v = float(get_path(report, path))
        if kind == "max":
            ok, rule = v <= limit, f"<= {limit}"
        elif kind == "min":
            ok, rule = v >= limit, f">= {limit}"
        elif kind == "range":
            lo, hi = limit
            ok, rule = lo <= v <= hi, f"in [{lo}, {hi}]"
        else:
            raise ValueError(f"unknown threshold kind {kind!r} for {path}")
        out.append(Check(path, v, rule, ok))
    return out


def failures(report: dict, thresholds: dict | None = None) -> list[Check]:
    return [c for c in check_thresholds(report, thresholds) if not c.ok]


def print_checks(checks: list[Check]) -> None:
    print(f"{'policy threshold':<44} {'value':>10}  {'rule':<16} verdict")
    print("-" * 84)
    for c in checks:
        print(f"{c.metric:<44} {c.value:>10.3f}  {c.rule:<16} {'ok' if c.ok else 'FAIL'}")
