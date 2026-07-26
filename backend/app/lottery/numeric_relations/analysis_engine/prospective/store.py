"""Prospective store — durable DEV/UAT persistence with lock/integrity/evaluate."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.prospective.db import (
    SqliteProspectiveDB,
    encode_json_fields,
)
from app.lottery.numeric_relations.analysis_engine.prospective.evaluation import (
    evaluate_locked_prediction,
)
from app.lottery.numeric_relations.analysis_engine.prospective.freeze import (
    FROZEN_ENGINE_VERSION,
    FROZEN_TABLE_VERSION,
    FROZEN_TIEBREAK_RULE,
    OPERATIONAL_RANKING_PROFILE,
    OPERATIONAL_TIEBREAK_POLICY,
    assert_operational_freeze,
    freeze_manifest,
    git_commit_short,
)
from app.lottery.numeric_relations.analysis_engine.prospective.hashing import (
    build_lock_payload,
    hash_payload,
    verify_hash,
)
from app.lottery.numeric_relations.analysis_engine.prospective.metrics import compute_pilot_metrics
from app.lottery.numeric_relations.analysis_engine.prospective.shadow import run_shadow_profiles
from app.lottery.numeric_relations.analysis_engine.schemas import new_id

IMMUTABLE_STATUSES = {"LOCKED", "AWAITING_RESULTS", "EVALUATED"}
LOCKABLE_STATUSES = {"DRAFT", "READY_TO_LOCK"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProspectivePrediction:
    """Compatibility view used by Phase 3 tests and API."""

    prediction_id: str
    status: str
    created_at: str
    input_data: dict[str, Any]
    candidates: list[dict[str, Any]]
    ranking: list[dict[str, Any]]
    tiebreak: dict[str, Any] | None
    engine_version: str
    prediction_hash: str
    locked_at: str | None = None
    evaluated_at: str | None = None
    future_result: dict[str, Any] | None = None
    evaluation: dict[str, Any] | None = None
    # Phase 4 fields
    table1_version: str = FROZEN_TABLE_VERSION
    table2_version: str = FROZEN_TABLE_VERSION
    ranking_profile: str = OPERATIONAL_RANKING_PROFILE
    tiebreak_profile: str = FROZEN_TIEBREAK_RULE
    multi_strong_candidates: list[int] | None = None
    primary_signal: dict[str, Any] | None = None
    canonical_payload: dict[str, Any] | None = None
    locked_by: str | None = None
    engine_commit: str | None = None
    integrity_ok: bool = True
    analysis_date: str | None = None
    target_date: str | None = None
    shadow_profiles: dict[str, Any] | None = None
    evaluation_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "status": self.status,
            "created_at": self.created_at,
            "input_data": self.input_data,
            "candidates": self.candidates,
            "ranking": self.ranking,
            "tiebreak": self.tiebreak,
            "engine_version": self.engine_version,
            "prediction_hash": self.prediction_hash,
            "locked_at": self.locked_at,
            "evaluated_at": self.evaluated_at,
            "future_result": self.future_result,
            "evaluation": self.evaluation,
            "table1_version": self.table1_version,
            "table2_version": self.table2_version,
            "ranking_profile": self.ranking_profile,
            "tiebreak_profile": self.tiebreak_profile,
            "multi_strong_candidates": self.multi_strong_candidates or [],
            "primary_signal": self.primary_signal,
            "canonical_payload": self.canonical_payload,
            "locked_by": self.locked_by,
            "engine_commit": self.engine_commit,
            "integrity_ok": self.integrity_ok,
            "analysis_date": self.analysis_date,
            "target_date": self.target_date,
            "shadow_profiles": self.shadow_profiles,
            "evaluation_status": self.evaluation_status,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ProspectivePrediction":
        return cls(
            prediction_id=row["prediction_id"],
            status=row["status"],
            created_at=row.get("created_at") or "",
            input_data=row.get("input_data") or {},
            candidates=row.get("candidates") or [],
            ranking=row.get("ranking") or [],
            tiebreak=row.get("tiebreak"),
            engine_version=row.get("engine_version") or FROZEN_ENGINE_VERSION,
            prediction_hash=row.get("prediction_hash") or "",
            locked_at=row.get("locked_at"),
            evaluated_at=row.get("evaluated_at"),
            future_result=row.get("future_result"),
            evaluation=row.get("evaluation"),
            table1_version=row.get("table1_version") or FROZEN_TABLE_VERSION,
            table2_version=row.get("table2_version") or FROZEN_TABLE_VERSION,
            ranking_profile=row.get("ranking_profile") or OPERATIONAL_RANKING_PROFILE,
            tiebreak_profile=row.get("tiebreak_profile") or FROZEN_TIEBREAK_RULE,
            multi_strong_candidates=row.get("multi_strong_candidates") or [],
            primary_signal=row.get("primary_signal"),
            canonical_payload=row.get("canonical_payload"),
            locked_by=row.get("locked_by"),
            engine_commit=row.get("engine_commit"),
            integrity_ok=bool(row.get("integrity_ok", True)),
            analysis_date=row.get("analysis_date"),
            target_date=row.get("target_date"),
            shadow_profiles=row.get("shadow_profiles"),
            evaluation_status=row.get("evaluation_status"),
        )


class ProspectiveStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db = SqliteProspectiveDB(db_path)
        # Phase 3 compat alias
        self.predictions: dict[str, ProspectivePrediction] = {}
        self._reload_cache()

    def _reload_cache(self) -> None:
        self.predictions = {
            r["prediction_id"]: ProspectivePrediction.from_row(r)
            for r in self.db.list_predictions()
        }

    def _persist(self, pred: ProspectivePrediction, extra: dict[str, Any] | None = None) -> None:
        row = {
            "prediction_id": pred.prediction_id,
            "pilot_id": (extra or {}).get("pilot_id"),
            "status": pred.status,
            "created_at": pred.created_at,
            "created_by": (extra or {}).get("created_by"),
            "analysis_date": pred.analysis_date,
            "target_date": pred.target_date,
            "lottery": (extra or {}).get("lottery") or (pred.input_data.get("raw") or {}).get("lotteries"),
            "position": (extra or {}).get("position"),
            "input_numbers": pred.input_data.get("numbers"),
            "input_data": pred.input_data,
            "engine_version": pred.engine_version,
            "table1_version": pred.table1_version,
            "table2_version": pred.table2_version,
            "ranking_profile": pred.ranking_profile,
            "tiebreak_profile": pred.tiebreak_profile,
            "derivation_depth": (extra or {}).get("derivation_depth", 0),
            "candidates": pred.candidates,
            "ranking": pred.ranking,
            "primary_signal": pred.primary_signal,
            "secondary_signals": (extra or {}).get("secondary_signals") or [],
            "multi_strong_candidates": pred.multi_strong_candidates or [],
            "score_components": (extra or {}).get("score_components"),
            "confidence": (extra or {}).get("confidence"),
            "evidence": (extra or {}).get("evidence"),
            "tiebreak": pred.tiebreak,
            "shadow_profiles": pred.shadow_profiles,
            "locked_at": pred.locked_at,
            "locked_by": pred.locked_by,
            "prediction_hash": pred.prediction_hash,
            "canonical_payload": pred.canonical_payload,
            "engine_commit": pred.engine_commit,
            "result_received_at": (extra or {}).get("result_received_at"),
            "future_result": pred.future_result,
            "evaluation_status": pred.evaluation_status,
            "evaluation": pred.evaluation,
            "evaluated_at": pred.evaluated_at,
            "integrity_ok": 1 if pred.integrity_ok else 0,
            "input_complete": 1 if (extra or {}).get("input_complete", True) else 0,
            "input_incomplete_reason": (extra or {}).get("input_incomplete_reason"),
        }
        # stringify lottery if list
        if isinstance(row["lottery"], list):
            row["lottery"] = json.dumps(row["lottery"], ensure_ascii=False)
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
        self.db.upsert_prediction(encode_json_fields(row, json_keys))
        self.predictions[pred.prediction_id] = pred

    def create(self, body: dict[str, Any]) -> ProspectivePrediction:
        numbers = body.get("numbers") or []
        if not numbers:
            if body.get("mark_incomplete") or body.get("allow_incomplete"):
                pid = new_id("pros")
                pred = ProspectivePrediction(
                    prediction_id=pid,
                    status="DRAFT",
                    created_at=_now(),
                    input_data={"numbers": [], "raw": body, "incomplete": True},
                    candidates=[],
                    ranking=[],
                    tiebreak=None,
                    engine_version=FROZEN_ENGINE_VERSION,
                    prediction_hash="",
                    analysis_date=body.get("date"),
                    target_date=body.get("target_date") or body.get("date"),
                )
                self._persist(
                    pred,
                    {
                        "input_complete": False,
                        "input_incomplete_reason": body.get("incomplete_reason")
                        or "INPUT_INCOMPLETE",
                        "created_by": body.get("created_by"),
                    },
                )
                self.db.add_audit(
                    pid, "INPUT_INCOMPLETE", {"reason": "missing numbers"}, body.get("created_by"), _now()
                )
                return pred
            raise ValueError("INPUT_INCOMPLETE: at least one observed number is required")

        result = run_complete_analysis(
            {
                "numbers": numbers,
                "date": body.get("date"),
                "mode": body.get("mode") or "socio",
                "derivation_depth": int(body.get("derivation_depth") or 0),
                "positions": body.get("positions") or ["first"],
                "create_signals": False,
                "enable_tiebreak": body.get("enable_tiebreak", True),
            },
            persist=False,
            enable_tiebreak=bool(body.get("enable_tiebreak", True)),
        )
        multi = list((result.tiebreak or {}).get("multi_fuerte_numbers") or [])
        ranking = [
            {
                "number": c["number"],
                "rank": c.get("rank"),
                "classification": c["classification"],
                "score": c.get("total_score"),
            }
            for c in result.ranked_candidates[:10]
        ]
        freeze = freeze_manifest()
        shadow = None
        if body.get("include_shadow", False):
            shadow = run_shadow_profiles(
                numbers=list(result.observed_numbers),
                date=result.analysis_date,
                positions=list(result.positions or ["first"]),
            )
        pred = ProspectivePrediction(
            prediction_id=new_id("pros"),
            status="DRAFT",
            created_at=_now(),
            input_data={
                "numbers": result.observed_numbers,
                "date": result.analysis_date,
                "mode": result.mode,
                "raw": {
                    k: body.get(k)
                    for k in ("numbers", "date", "mode", "lotteries", "positions", "target_date")
                },
            },
            candidates=result.ranked_candidates[:10],
            ranking=ranking,
            tiebreak=result.tiebreak,
            engine_version=result.engine_version,
            prediction_hash="",  # set at lock
            table1_version=FROZEN_TABLE_VERSION,
            table2_version=FROZEN_TABLE_VERSION,
            ranking_profile=result.mode or OPERATIONAL_RANKING_PROFILE,
            tiebreak_profile=FROZEN_TIEBREAK_RULE,
            multi_strong_candidates=multi,
            primary_signal=result.primary_signal,
            engine_commit=freeze.get("engine_commit"),
            analysis_date=result.analysis_date,
            target_date=body.get("target_date") or result.analysis_date,
            shadow_profiles=shadow,
        )
        # draft hash of unlocked content (will be recomputed on lock with locked_at)
        draft_payload = build_lock_payload(
            inputs=pred.input_data,
            target_date=pred.target_date,
            lotteries=(body.get("lotteries") or []),
            positions=body.get("positions") or ["first"],
            candidates=[{"number": c["number"], "classification": c["classification"]} for c in pred.candidates],
            ranking=pred.ranking,
            scores=[{"number": r["number"], "score": r.get("score")} for r in pred.ranking],
            classifications=[{"number": r["number"], "classification": r["classification"]} for r in pred.ranking],
            tiebreak_rule=OPERATIONAL_TIEBREAK_POLICY,
            engine_version=pred.engine_version,
            table1_version=pred.table1_version,
            table2_version=pred.table2_version,
            locked_at="",
            engine_commit=pred.engine_commit,
        )
        pred.canonical_payload = draft_payload
        pred.prediction_hash = hash_payload(draft_payload)
        assert_operational_freeze(
            {
                "engine_version": pred.engine_version,
                "table1_version": pred.table1_version,
                "ranking_profile": pred.ranking_profile,
            }
        )
        self._persist(
            pred,
            {
                "created_by": body.get("created_by") or "system",
                "derivation_depth": int(body.get("derivation_depth") or 0),
                "confidence": (result.primary_signal or {}).get("analytical_confidence"),
                "evidence": result.evidence_summary,
                "secondary_signals": [
                    c
                    for c in result.ranked_candidates[:5]
                    if c["classification"] == "FUERTE_SECUNDARIO"
                ],
                "lottery": body.get("lotteries"),
                "position": (body.get("positions") or ["first"])[0]
                if body.get("positions") or True
                else "first",
            },
        )
        self.db.add_audit(pred.prediction_id, "CREATED", {"status": "DRAFT"}, body.get("created_by"), _now())
        return pred

    def update_draft(self, prediction_id: str, patch: dict[str, Any]) -> ProspectivePrediction:
        pred = self.get(prediction_id)
        if pred is None:
            raise ValueError("prediction not found")
        if pred.status not in {"DRAFT", "READY_TO_LOCK"}:
            raise ValueError("LOCKED prediction cannot be modified")
        # Allow draft metadata edits; structural recalc requires new prediction id.
        raw = dict(pred.input_data.get("raw") or {})
        raw.update({k: v for k, v in patch.items() if k not in {"candidates", "ranking", "tiebreak"}})
        pred.input_data = {**pred.input_data, "raw": raw, **{k: patch[k] for k in patch if k in {"notes"}}}
        if "notes" in patch:
            pred.input_data["notes"] = patch["notes"]
        self._persist(pred)
        self.db.add_audit(prediction_id, "DRAFT_UPDATED", patch, None, _now())
        return pred

    def prepare_lock(self, prediction_id: str) -> ProspectivePrediction:
        pred = self._require(prediction_id)
        if pred.status not in {"DRAFT", "READY_TO_LOCK"}:
            raise ValueError(f"cannot prepare-lock in status {pred.status}")
        if not pred.candidates:
            raise ValueError("INPUT_INCOMPLETE")
        pred.status = "READY_TO_LOCK"
        self._persist(pred)
        self.db.add_audit(prediction_id, "READY_TO_LOCK", {}, None, _now())
        return pred

    def lock(self, prediction_id: str, *, locked_by: str | None = None) -> ProspectivePrediction:
        pred = self._require(prediction_id)
        if pred.status in {"LOCKED", "AWAITING_RESULTS"}:
            return pred
        if pred.status not in LOCKABLE_STATUSES:
            raise ValueError(f"cannot lock prediction in status {pred.status}")
        if not pred.candidates:
            raise ValueError("cannot lock incomplete prediction")
        locked_at = _now()
        payload = build_lock_payload(
            inputs=pred.input_data,
            target_date=pred.target_date,
            lotteries=(pred.input_data.get("raw") or {}).get("lotteries") or [],
            positions=(pred.input_data.get("raw") or {}).get("positions") or ["first"],
            candidates=[
                {"number": c["number"], "classification": c["classification"]} for c in pred.candidates
            ],
            ranking=pred.ranking,
            scores=[{"number": r["number"], "score": r.get("score")} for r in pred.ranking],
            classifications=[
                {"number": r["number"], "classification": r["classification"]} for r in pred.ranking
            ],
            tiebreak_rule=OPERATIONAL_TIEBREAK_POLICY,
            engine_version=pred.engine_version,
            table1_version=pred.table1_version,
            table2_version=pred.table2_version,
            locked_at=locked_at,
            engine_commit=pred.engine_commit or git_commit_short(),
        )
        pred.canonical_payload = payload
        pred.prediction_hash = hash_payload(payload)
        pred.status = "LOCKED"
        pred.locked_at = locked_at
        pred.locked_by = locked_by or "system"
        pred.engine_commit = payload["engine_commit"]
        self._persist(pred)
        self.db.add_audit(
            prediction_id,
            "LOCKED",
            {"hash": pred.prediction_hash, "locked_at": locked_at},
            pred.locked_by,
            locked_at,
        )
        return pred

    def check_integrity(self, prediction_id: str) -> dict[str, Any]:
        pred = self._require(prediction_id)
        payload = pred.canonical_payload
        if not payload or not pred.prediction_hash:
            return {"ok": False, "reason": "missing_payload_or_hash", "integrity_ok": False}
        ok = verify_hash(payload, pred.prediction_hash)
        if not ok:
            pred.integrity_ok = False
            self._persist(pred)
            self.db.add_audit(
                prediction_id,
                "INTEGRITY_ERROR",
                {"expected": pred.prediction_hash, "actual": hash_payload(payload)},
                None,
                _now(),
            )
        return {
            "ok": ok,
            "prediction_hash": pred.prediction_hash,
            "recomputed": hash_payload(payload),
            "integrity_ok": ok,
            "status": pred.status,
        }

    def evaluate(self, prediction_id: str, future_result: dict[str, Any]) -> ProspectivePrediction:
        pred = self._require(prediction_id)
        if pred.status == "EVALUATED":
            raise ValueError("EVALUATED prediction cannot be modified")
        if pred.status not in {"LOCKED", "AWAITING_RESULTS"}:
            raise ValueError("prediction must be LOCKED before evaluation")
        # Reject draws that occurred before the lock moment (calendar day).
        # Compare result date to locked_at date only — analysis_date may be historical.
        lock_day = (pred.locked_at or "")[:10]
        result_day = str(future_result.get("date") or "")[:10]
        if lock_day and result_day and result_day < lock_day:
            raise ValueError("result_before_lock_is_rejected")

        integrity = self.check_integrity(prediction_id)
        if not integrity["ok"]:
            pred.evaluation = {
                "hit_class": "INTEGRITY_ERROR",
                "integrity_ok": False,
            }
            pred.evaluation_status = "INTEGRITY_ERROR"
            pred.integrity_ok = False
            pred.status = "EVALUATED"
            pred.evaluated_at = _now()
            self._persist(pred)
            self.db.add_audit(prediction_id, "EVALUATION_BLOCKED_INTEGRITY", integrity, None, _now())
            return pred

        ev = evaluate_locked_prediction(pred.to_dict(), future_result, integrity_ok=True)
        pred.future_result = dict(future_result)
        pred.evaluation = ev
        pred.evaluation_status = ev["hit_class"]
        pred.status = "EVALUATED"
        pred.evaluated_at = ev["evaluated_at"]
        self._persist(pred, {"result_received_at": _now()})
        self.db.add_audit(
            prediction_id,
            "EVALUATED",
            {"hit_class": ev["hit_class"], "relative_day": ev.get("relative_day")},
            None,
            _now(),
        )
        return pred

    def cancel(self, prediction_id: str, reason: str | None = None) -> ProspectivePrediction:
        pred = self._require(prediction_id)
        if pred.status in {"EVALUATED"}:
            raise ValueError("cannot cancel evaluated prediction")
        if pred.status in IMMUTABLE_STATUSES and pred.status != "AWAITING_RESULTS":
            # allow cancel only from draft/ready; locked stays immutable except cancel->CANCELLED is explicit new state
            pass
        if pred.status in {"LOCKED", "AWAITING_RESULTS"}:
            # explicit cancel of locked is allowed as CANCELLED (not silent edit)
            pred.status = "CANCELLED"
        elif pred.status in {"DRAFT", "READY_TO_LOCK"}:
            pred.status = "CANCELLED"
        else:
            raise ValueError(f"cannot cancel status {pred.status}")
        self._persist(pred)
        self.db.add_audit(prediction_id, "CANCELLED", {"reason": reason}, None, _now())
        return pred

    def assert_mutable(self, prediction_id: str) -> None:
        pred = self._require(prediction_id)
        if pred.status in IMMUTABLE_STATUSES:
            raise ValueError("LOCKED prediction cannot be modified")

    def get(self, prediction_id: str) -> ProspectivePrediction | None:
        row = self.db.get_prediction(prediction_id)
        if not row:
            return None
        pred = ProspectivePrediction.from_row(row)
        self.predictions[prediction_id] = pred
        return pred

    def _require(self, prediction_id: str) -> ProspectivePrediction:
        pred = self.get(prediction_id)
        if pred is None:
            raise ValueError("prediction not found")
        return pred

    def list(self) -> list[ProspectivePrediction]:
        self._reload_cache()
        return list(self.predictions.values())

    def audit_log(self, prediction_id: str) -> list[dict[str, Any]]:
        return self.db.list_audit(prediction_id)

    def metrics(self) -> dict[str, Any]:
        preds = [p.to_dict() for p in self.list()]
        base = compute_pilot_metrics(preds)
        # Phase 3 compatibility keys
        base.update(
            {
                "total": len(preds),
                "draft": sum(1 for p in preds if p["status"] == "DRAFT"),
                "locked": sum(1 for p in preds if p["status"] in {"LOCKED", "AWAITING_RESULTS"}),
                "evaluated": sum(1 for p in preds if p["status"] == "EVALUATED"),
                "locked_or_evaluated": sum(
                    1
                    for p in preds
                    if p["status"] in {"LOCKED", "AWAITING_RESULTS", "EVALUATED"}
                ),
            }
        )
        return base

    # --- pilot configurations ---
    def create_pilot(self, body: dict[str, Any]) -> dict[str, Any]:
        pid = new_id("pilot")
        now = _now()
        row = {
            "id": pid,
            "pilot_name": body.get("pilot_name") or "DEV/UAT Prospective Pilot",
            "start_date": body.get("start_date"),
            "end_date": body.get("end_date"),
            "status": body.get("status") or "DRAFT",
            "lotteries": body.get("lotteries") or [],
            "positions": body.get("positions") or ["first"],
            "input_mode": body.get("input_mode") or "generator_first",
            "analysis_time": body.get("analysis_time"),
            "lock_deadline": body.get("lock_deadline"),
            "evaluation_window": body.get("evaluation_window") or "D+1_D+7",
            "ranking_profile": body.get("ranking_profile") or OPERATIONAL_RANKING_PROFILE,
            "tiebreak_profile": body.get("tiebreak_profile") or FROZEN_TIEBREAK_RULE,
            "derivation_depth": int(body.get("derivation_depth") or 0),
            "auto_run": 1 if body.get("auto_run", True) else 0,
            "auto_lock": 1 if body.get("auto_lock", True) else 0,
            "auto_evaluate": 1 if body.get("auto_evaluate", True) else 0,
            "minimum_samples": int(body.get("minimum_samples") or 100),
            "responsible_user": body.get("responsible_user"),
            "environment": "DEV/UAT",
            "payload": {
                "tiebreak_policy": OPERATIONAL_TIEBREAK_POLICY,
                "freeze": freeze_manifest(),
            },
            "created_at": now,
            "updated_at": now,
        }
        self.db.upsert_pilot(
            encode_json_fields(row, ("lotteries", "positions", "payload"))
        )
        return self.db.get_pilot(pid) or row

    def list_pilots(self) -> list[dict[str, Any]]:
        return self.db.list_pilots()

    def get_pilot(self, pilot_id: str) -> dict[str, Any] | None:
        return self.db.get_pilot(pilot_id)

    def patch_pilot(self, pilot_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        cur = self.db.get_pilot(pilot_id)
        if not cur:
            raise ValueError("pilot not found")
        if cur.get("status") == "COMPLETED":
            raise ValueError("completed pilot cannot be modified")
        cur.update(patch)
        cur["updated_at"] = _now()
        self.db.upsert_pilot(
            encode_json_fields(
                {
                    **cur,
                    "auto_run": 1 if cur.get("auto_run", True) else 0,
                    "auto_lock": 1 if cur.get("auto_lock", True) else 0,
                    "auto_evaluate": 1 if cur.get("auto_evaluate", True) else 0,
                },
                ("lotteries", "positions", "payload"),
            )
        )
        return self.db.get_pilot(pilot_id) or cur

    def set_pilot_status(self, pilot_id: str, status: str) -> dict[str, Any]:
        return self.patch_pilot(pilot_id, {"status": status})

    def save_snapshot(self, pilot_id: str | None, snapshot_date: str, metrics: dict[str, Any]) -> None:
        self.db.add_snapshot(pilot_id, snapshot_date, metrics, _now())

    def list_snapshots(self) -> list[dict[str, Any]]:
        return self.db.list_snapshots()


_STORE: ProspectiveStore | None = None


def get_prospective_store() -> ProspectiveStore:
    global _STORE
    if _STORE is None:
        # tests: use temp db unless LOTTERY_PROSPECTIVE_DB set
        path = None
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("LOTTERY_PROSPECTIVE_DB"):
            fd, name = tempfile.mkstemp(prefix="prospective_test_", suffix=".sqlite")
            os.close(fd)
            path = Path(name)
        _STORE = ProspectiveStore(path)
    return _STORE


def reset_prospective_store() -> ProspectiveStore:
    global _STORE
    if _STORE is not None:
        try:
            _STORE.db.reset()
            _STORE.db.close()
        except Exception:
            pass
    path = None
    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("LOTTERY_PROSPECTIVE_DB"):
        fd, name = tempfile.mkstemp(prefix="prospective_test_", suffix=".sqlite")
        os.close(fd)
        path = Path(name)
    _STORE = ProspectiveStore(path)
    return _STORE
