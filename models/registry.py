"""Minimal JSON model registry.

Not MLflow -- deliberately a single human-readable file so a reviewer can see
every model that has ever been proposed, its metrics, and who signed it off.
``models/train.py`` also logs to MLflow when available; this file is the
governance record of record.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import MODEL_REGISTRY


def _load() -> list[dict]:
    if MODEL_REGISTRY.exists():
        return json.loads(MODEL_REGISTRY.read_text())
    return []


def _save(entries: list[dict]) -> None:
    MODEL_REGISTRY.write_text(json.dumps(entries, indent=2))


def next_version() -> str:
    entries = _load()
    return f"v{len(entries) + 1}"


def register(*, version: str, artifact_path: str, training_data_hash: str,
             metrics: dict, n_train: int, n_test: int, notes: str = "") -> dict:
    entries = _load()
    entry = dict(
        version=version,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        artifact_path=str(Path(artifact_path).as_posix()),
        training_data_hash=training_data_hash,
        n_train=n_train,
        n_test=n_test,
        metrics=metrics,
        approved_by=None,          # set by governance sign-off, not by training
        approved_at=None,
        status="candidate",        # candidate | approved | retired
        notes=notes,
    )
    entries.append(entry)
    _save(entries)
    return entry


def approve(version: str, approver: str) -> dict:
    entries = _load()
    for e in entries:
        if e["version"] == version:
            e["approved_by"] = approver
            e["approved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            e["status"] = "approved"
            _save(entries)
            return e
    raise KeyError(version)


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
