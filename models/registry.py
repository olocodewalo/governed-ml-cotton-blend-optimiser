"""Minimal JSON model registry.

Not MLflow -- deliberately a single human-readable file so a reviewer can see
every model that has ever been proposed, its metrics, and who signed it off.
``models/train.py`` also logs to MLflow when available; this file is the
governance record of record.

Lifecycle: ``train`` registers a **candidate**; only ``models.promote`` (after
the acceptance thresholds + regression gate pass) marks it **approved**, retires
the previously approved model and moves the ``quality_model_current`` pointer.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import MODEL_REGISTRY, ROOT


def _load() -> list[dict]:
    if MODEL_REGISTRY.exists():
        return json.loads(MODEL_REGISTRY.read_text())
    return []


def _save(entries: list[dict]) -> None:
    MODEL_REGISTRY.write_text(json.dumps(entries, indent=2))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(path: str | Path) -> str:
    """Store artifact paths relative to the repo so the registry is portable."""
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def artifact_abspath(entry: dict) -> Path:
    p = Path(entry["artifact_path"])
    return p if p.is_absolute() else ROOT / p


def next_version() -> str:
    entries = _load()
    return f"v{len(entries) + 1}"


def register(*, version: str, artifact_path: str, training_data_hash: str,
             metrics: dict, n_train: int, n_test: int, notes: str = "") -> dict:
    entries = _load()
    entry = dict(
        version=version,
        timestamp=_now(),
        artifact_path=_rel(artifact_path),
        training_data_hash=training_data_hash,
        n_train=n_train,
        n_test=n_test,
        metrics=metrics,
        golden_metrics=None,       # filled by eval.run_golden
        approved_by=None,          # set by governance sign-off, not by training
        approved_at=None,
        status="candidate",        # candidate | approved | retired
        notes=notes,
    )
    entries.append(entry)
    _save(entries)
    return entry


def record_golden(version: str, report: dict) -> None:
    entries = _load()
    for e in entries:
        if e["version"] == version:
            e["golden_metrics"] = report
            _save(entries)
            return
    raise KeyError(version)


def approve(version: str, approver: str, cab_note: str | None = None) -> dict:
    """Mark ``version`` approved and retire any previously approved model."""
    if not approver or not approver.strip():
        raise ValueError("approval needs a named approver")
    entries = _load()
    target = None
    for e in entries:
        if e["version"] == version:
            target = e
    if target is None:
        raise KeyError(version)
    for e in entries:
        if e is not target and e["status"] == "approved":
            e["status"] = "retired"
            e["retired_at"] = _now()
    target["approved_by"] = approver.strip()
    target["approved_at"] = _now()
    target["status"] = "approved"
    if cab_note:
        target["cab_note"] = cab_note
    _save(entries)
    return target


def latest(status: str | None = None) -> dict | None:
    entries = _load()
    if status:
        entries = [e for e in entries if e["status"] == status]
    return entries[-1] if entries else None


def get(version: str) -> dict:
    for e in _load():
        if e["version"] == version:
            return e
    raise KeyError(version)


def all_entries() -> list[dict]:
    return _load()
