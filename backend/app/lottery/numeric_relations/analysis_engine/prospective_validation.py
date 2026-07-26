"""Prospective validation — lock predictions before draw outcomes (DEV in-memory)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.schemas import new_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProspectivePrediction:
    prediction_id: str
    status: str  # DRAFT | LOCKED | EVALUATED
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hash_payload(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ProspectiveStore:
    def __init__(self) -> None:
        self.predictions: dict[str, ProspectivePrediction] = {}

    def create(self, body: dict[str, Any]) -> ProspectivePrediction:
        result = run_complete_analysis(
            {
                "numbers": body.get("numbers") or [],
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
        payload = {
            "numbers": result.observed_numbers,
            "date": result.analysis_date,
            "ranked": [
                {"number": c["number"], "classification": c["classification"], "score": c["total_score"]}
                for c in result.ranked_candidates[:10]
            ],
            "primary": result.primary_signal,
            "tiebreak": result.tiebreak,
            "engine_version": result.engine_version,
        }
        pred = ProspectivePrediction(
            prediction_id=new_id("pros"),
            status="DRAFT",
            created_at=_now(),
            input_data={
                "numbers": result.observed_numbers,
                "date": result.analysis_date,
                "mode": result.mode,
                "raw": {k: body.get(k) for k in ("numbers", "date", "mode", "lotteries", "positions")},
            },
            candidates=result.ranked_candidates[:10],
            ranking=[
                {"number": c["number"], "rank": c.get("rank"), "classification": c["classification"]}
                for c in result.ranked_candidates[:10]
            ],
            tiebreak=result.tiebreak,
            engine_version=result.engine_version,
            prediction_hash=_hash_payload(payload),
        )
        self.predictions[pred.prediction_id] = pred
        return pred

    def lock(self, prediction_id: str) -> ProspectivePrediction:
        pred = self.predictions[prediction_id]
        if pred.status == "LOCKED":
            return pred
        if pred.status != "DRAFT":
            raise ValueError(f"cannot lock prediction in status {pred.status}")
        pred.status = "LOCKED"
        pred.locked_at = _now()
        return pred

    def evaluate(self, prediction_id: str, future_result: dict[str, Any]) -> ProspectivePrediction:
        pred = self.predictions[prediction_id]
        if pred.status == "EVALUATED":
            raise ValueError("EVALUATED prediction cannot be modified")
        if pred.status != "LOCKED":
            raise ValueError("prediction must be LOCKED before evaluation")
        drawn = [int(x) for x in (future_result.get("numbers") or [])]
        multi = (pred.tiebreak or {}).get("multi_fuerte_numbers") or []
        primary_num = pred.ranking[0]["number"] if pred.ranking else None
        hit_exact = primary_num in drawn if primary_num is not None and not multi else False
        hit_multi = any(n in drawn for n in multi) if multi else False
        pred.future_result = dict(future_result)
        pred.evaluation = {
            "hit_primary_exact": hit_exact,
            "hit_multi_fuerte": hit_multi,
            "drawn_numbers": drawn,
            "evaluated_at": _now(),
        }
        pred.status = "EVALUATED"
        pred.evaluated_at = _now()
        return pred

    def assert_mutable(self, prediction_id: str) -> None:
        pred = self.predictions[prediction_id]
        if pred.status in {"LOCKED", "EVALUATED"}:
            raise ValueError("LOCKED prediction cannot be modified")

    def get(self, prediction_id: str) -> ProspectivePrediction | None:
        return self.predictions.get(prediction_id)

    def list(self) -> list[ProspectivePrediction]:
        return list(self.predictions.values())

    def metrics(self) -> dict[str, Any]:
        preds = list(self.predictions.values())
        locked = [p for p in preds if p.status in {"LOCKED", "EVALUATED"}]
        evaluated = [p for p in preds if p.status == "EVALUATED"]
        return {
            "total": len(preds),
            "draft": sum(1 for p in preds if p.status == "DRAFT"),
            "locked": sum(1 for p in preds if p.status == "LOCKED"),
            "evaluated": len(evaluated),
            "locked_or_evaluated": len(locked),
            "hit_primary_rate": (
                sum(1 for p in evaluated if (p.evaluation or {}).get("hit_primary_exact"))
                / len(evaluated)
            )
            if evaluated
            else None,
            "production_modified": False,
        }


_STORE: ProspectiveStore | None = None


def get_prospective_store() -> ProspectiveStore:
    global _STORE
    if _STORE is None:
        _STORE = ProspectiveStore()
    return _STORE


def reset_prospective_store() -> ProspectiveStore:
    global _STORE
    _STORE = ProspectiveStore()
    return _STORE
