"""SQLite persistence backend for DEV/UAT prospective pilot (tests + local).

Postgres schema is provided by Alembic 062. This backend mirrors the same
logical records so unit tests and DEV work without Production Postgres.
Production writes are hard-blocked.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def default_db_path() -> Path:
    override = os.environ.get("LOTTERY_PROSPECTIVE_DB")
    if override:
        return Path(override)
    path = _repo_root() / "artifacts" / "prospective" / "pilot_dev_uat.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def assert_not_production() -> None:
    env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").lower()
    if env in {"production", "prod"}:
        raise RuntimeError("Prospective pilot persistence is forbidden in Production")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pilot_configurations (
  id TEXT PRIMARY KEY,
  pilot_name TEXT NOT NULL,
  start_date TEXT,
  end_date TEXT,
  status TEXT NOT NULL,
  lotteries TEXT,
  positions TEXT,
  input_mode TEXT,
  analysis_time TEXT,
  lock_deadline TEXT,
  evaluation_window TEXT,
  ranking_profile TEXT,
  tiebreak_profile TEXT,
  derivation_depth INTEGER,
  auto_run INTEGER,
  auto_lock INTEGER,
  auto_evaluate INTEGER,
  minimum_samples INTEGER,
  responsible_user TEXT,
  environment TEXT,
  payload TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS prospective_runs (
  prediction_id TEXT PRIMARY KEY,
  pilot_id TEXT,
  status TEXT NOT NULL,
  created_at TEXT,
  created_by TEXT,
  analysis_date TEXT,
  target_date TEXT,
  lottery TEXT,
  position TEXT,
  input_numbers TEXT,
  input_data TEXT,
  engine_version TEXT,
  table1_version TEXT,
  table2_version TEXT,
  ranking_profile TEXT,
  tiebreak_profile TEXT,
  derivation_depth INTEGER,
  candidates TEXT,
  ranking TEXT,
  primary_signal TEXT,
  secondary_signals TEXT,
  multi_strong_candidates TEXT,
  score_components TEXT,
  confidence REAL,
  evidence TEXT,
  tiebreak TEXT,
  shadow_profiles TEXT,
  locked_at TEXT,
  locked_by TEXT,
  prediction_hash TEXT,
  canonical_payload TEXT,
  engine_commit TEXT,
  result_received_at TEXT,
  future_result TEXT,
  evaluation_status TEXT,
  evaluation TEXT,
  evaluated_at TEXT,
  integrity_ok INTEGER,
  input_complete INTEGER,
  input_incomplete_reason TEXT
);

CREATE TABLE IF NOT EXISTS prospective_audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prediction_id TEXT NOT NULL,
  action TEXT NOT NULL,
  detail TEXT,
  actor TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pilot_daily_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pilot_id TEXT,
  snapshot_date TEXT NOT NULL,
  metrics TEXT,
  created_at TEXT NOT NULL
);
"""


class SqliteProspectiveDB:
    def __init__(self, path: Path | None = None) -> None:
        assert_not_production()
        self.path = path or default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def reset(self) -> None:
        for table in (
            "prospective_audit_logs",
            "pilot_daily_snapshots",
            "prospective_runs",
            "pilot_configurations",
        ):
            self._conn.execute(f"DELETE FROM {table}")
        self._conn.commit()

    # --- pilots ---
    def upsert_pilot(self, row: dict[str, Any]) -> None:
        cols = list(row.keys())
        placeholders = ",".join("?" for _ in cols)
        updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "id")
        sql = (
            f"INSERT INTO pilot_configurations ({','.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}"
        )
        self._conn.execute(sql, [row[c] for c in cols])
        self._conn.commit()

    def get_pilot(self, pilot_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT * FROM pilot_configurations WHERE id=?", (pilot_id,))
        r = cur.fetchone()
        return self._decode_pilot(r) if r else None

    def list_pilots(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM pilot_configurations ORDER BY created_at")
        return [self._decode_pilot(r) for r in cur.fetchall()]

    def _decode_pilot(self, r: sqlite3.Row) -> dict[str, Any]:
        d = dict(r)
        for k in ("lotteries", "positions", "payload"):
            if d.get(k):
                d[k] = json.loads(d[k])
        for k in ("auto_run", "auto_lock", "auto_evaluate"):
            if k in d and d[k] is not None:
                d[k] = bool(d[k])
        return d

    # --- predictions ---
    def upsert_prediction(self, row: dict[str, Any]) -> None:
        cols = list(row.keys())
        placeholders = ",".join("?" for _ in cols)
        updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "prediction_id")
        sql = (
            f"INSERT INTO prospective_runs ({','.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(prediction_id) DO UPDATE SET {updates}"
        )
        self._conn.execute(sql, [row[c] for c in cols])
        self._conn.commit()

    def get_prediction(self, prediction_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute(
            "SELECT * FROM prospective_runs WHERE prediction_id=?", (prediction_id,)
        )
        r = cur.fetchone()
        return self._decode_pred(r) if r else None

    def list_predictions(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM prospective_runs ORDER BY created_at")
        return [self._decode_pred(r) for r in cur.fetchall()]

    def _decode_pred(self, r: sqlite3.Row) -> dict[str, Any]:
        d = dict(r)
        json_keys = (
            "input_numbers",
            "input_data",
            "candidates",
            "ranking",
            "primary_signal",
            "secondary_signals",
            "multi_strong_candidates",
            "score_components",
            "evidence",
            "tiebreak",
            "shadow_profiles",
            "canonical_payload",
            "future_result",
            "evaluation",
        )
        for k in json_keys:
            if d.get(k):
                d[k] = json.loads(d[k])
        d["integrity_ok"] = bool(d.get("integrity_ok", 1))
        d["input_complete"] = bool(d.get("input_complete", 1))
        return d

    def add_audit(
        self,
        prediction_id: str,
        action: str,
        detail: dict[str, Any] | None = None,
        actor: str | None = None,
        created_at: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO prospective_audit_logs (prediction_id, action, detail, actor, created_at) "
            "VALUES (?,?,?,?,?)",
            (
                prediction_id,
                action,
                json.dumps(detail or {}, ensure_ascii=False),
                actor,
                created_at or "",
            ),
        )
        self._conn.commit()

    def list_audit(self, prediction_id: str) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT * FROM prospective_audit_logs WHERE prediction_id=? ORDER BY id",
            (prediction_id,),
        )
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            if d.get("detail"):
                d["detail"] = json.loads(d["detail"])
            rows.append(d)
        return rows

    def add_snapshot(self, pilot_id: str | None, snapshot_date: str, metrics: dict[str, Any], created_at: str) -> None:
        self._conn.execute(
            "INSERT INTO pilot_daily_snapshots (pilot_id, snapshot_date, metrics, created_at) VALUES (?,?,?,?)",
            (pilot_id, snapshot_date, json.dumps(metrics, ensure_ascii=False), created_at),
        )
        self._conn.commit()

    def list_snapshots(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM pilot_daily_snapshots ORDER BY id")
        out = []
        for r in cur.fetchall():
            d = dict(r)
            if d.get("metrics"):
                d["metrics"] = json.loads(d["metrics"])
            out.append(d)
        return out


def encode_json_fields(row: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    out = dict(row)
    for k in keys:
        if k in out and out[k] is not None and not isinstance(out[k], str):
            out[k] = json.dumps(out[k], ensure_ascii=False, default=str)
    return out
