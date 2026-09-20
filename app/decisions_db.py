"""Immutable-ish audit log of every HITL decision (SQLite).

One row per master action. Nothing is updated except the ``outcome`` fields,
which are filled in later when the spun-yarn QC for that laydown comes back.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from config import DECISIONS_DB

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                TEXT NOT NULL,
    scenario_json     TEXT NOT NULL,
    model_version     TEXT NOT NULL,
    method            TEXT NOT NULL,
    recommendation_json TEXT NOT NULL,
    predicted_json    TEXT NOT NULL,
    price_inr_per_kg  REAL NOT NULL,
    baseline_price    REAL,
    rationale         TEXT,
    llm_model         TEXT,
    user_action       TEXT NOT NULL,          -- approve | adjust | reject
    edited_weights_json TEXT,
    feedback          TEXT,
    outcome_qc_json   TEXT,                   -- filled later
    outcome_note      TEXT
);
"""


def _conn():
    c = sqlite3.connect(DECISIONS_DB)
    c.execute(_SCHEMA)
    return c


def log_decision(*, scenario: dict, model_version: str, method: str,
                 recommendation: dict, predicted: dict, price: float,
                 baseline_price: float | None, rationale: str, llm_model: str,
                 user_action: str, edited_weights: dict | None, feedback: str) -> int:
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO decisions
               (ts, scenario_json, model_version, method, recommendation_json,
                predicted_json, price_inr_per_kg, baseline_price, rationale,
                llm_model, user_action, edited_weights_json, feedback)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"),
             json.dumps(scenario), model_version, method, json.dumps(recommendation),
             json.dumps(predicted), price, baseline_price, rationale, llm_model,
             user_action, json.dumps(edited_weights) if edited_weights else None,
             feedback),
        )
        return cur.lastrowid


def recent(limit: int = 25):
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def record_outcome(decision_id: int, qc: dict, note: str = "") -> None:
    with _conn() as c:
        c.execute("UPDATE decisions SET outcome_qc_json=?, outcome_note=? WHERE id=?",
                  (json.dumps(qc), note, decision_id))


def count_actions(action: str, model_version: str | None = None) -> int:
    """How many decisions of one kind (e.g. 'adjust') -- a retrain trigger input."""
    sql, args = "SELECT COUNT(*) FROM decisions WHERE user_action=?", [action]
    if model_version:
        sql += " AND model_version=?"
        args.append(model_version)
    with _conn() as c:
        return int(c.execute(sql, args).fetchone()[0])
