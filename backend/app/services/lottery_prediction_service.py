"""Service for prediction motor registry + NR-backed prediction run."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lottery.numeric_relations.api_schemas import AnalyzeBody, limit_from_body
from app.lottery.numeric_relations.db_history import analyze_from_db
from app.lottery.predictions import (
    ALLOWED_STATUS,
    MOTOR_CATALOG,
    PREDICTION_DISCLAIMER,
    catalog_by_key,
)
from app.models.lottery import LotteryPredictionMotor, LotteryPredictionMotorRun


class PredictionMotorService:
    def __init__(self, db: AsyncSession, *, tenant_id: UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id

    async def ensure_seeded(self) -> None:
        existing = {
            r.key: r
            for r in (
                await self.db.execute(select(LotteryPredictionMotor))
            ).scalars().all()
        }
        changed = False
        for item in MOTOR_CATALOG:
            row = existing.get(item["key"])
            if row is None:
                self.db.add(
                    LotteryPredictionMotor(
                        tenant_id=self.tenant_id,
                        key=item["key"],
                        name=item["name"],
                        description=item["description"],
                        status=item["status"],
                        implemented=bool(item["implemented"]),
                        implementation_ref=item.get("implementation_ref"),
                        version=item.get("version"),
                        priority=int(item.get("priority") or 100),
                        weight=item.get("weight"),
                        docs=item.get("docs"),
                        health="ok" if item["implemented"] else "n/a",
                    )
                )
                changed = True
            else:
                # Keep operator toggles; refresh static metadata for unimplemented.
                row.name = item["name"]
                row.description = item["description"]
                row.implemented = bool(item["implemented"])
                row.implementation_ref = item.get("implementation_ref")
                row.docs = item.get("docs")
                if not item["implemented"]:
                    row.status = "NO_IMPLEMENTADO"
                    row.weight = None
                changed = True
        if changed:
            await self.db.flush()

    async def list_motors(self) -> list[dict[str, Any]]:
        await self.ensure_seeded()
        rows = (
            await self.db.execute(
                select(LotteryPredictionMotor).order_by(LotteryPredictionMotor.priority.asc())
            )
        ).scalars().all()
        return [self._to_dict(r) for r in rows]

    async def get_motor(self, key: str) -> LotteryPredictionMotor | None:
        await self.ensure_seeded()
        return (
            await self.db.execute(
                select(LotteryPredictionMotor).where(LotteryPredictionMotor.key == key)
            )
        ).scalar_one_or_none()

    async def is_executable(self, key: str) -> bool:
        motor = await self.get_motor(key)
        if motor is None:
            cat = catalog_by_key().get(key)
            return bool(cat and cat.get("implemented") and cat.get("status") == "ACTIVO")
        return bool(motor.implemented and motor.status == "ACTIVO")

    async def patch_motor(self, key: str, data: dict[str, Any], *, user_id: UUID | None) -> dict[str, Any]:
        motor = await self.get_motor(key)
        if motor is None:
            raise ValueError(f"motor not found: {key}")
        if not motor.implemented:
            raise ValueError(
                f"motor '{key}' is NO_IMPLEMENTADO — cannot activate, weight, or execute"
            )
        if "status" in data and data["status"] is not None:
            status = str(data["status"]).upper().replace(" ", "_")
            if status not in ALLOWED_STATUS - {"NO_IMPLEMENTADO"}:
                raise ValueError(f"invalid status for implemented motor: {status}")
            if status == "NO_IMPLEMENTADO":
                raise ValueError("cannot set implemented motor to NO_IMPLEMENTADO")
            motor.status = status
        if "priority" in data and data["priority"] is not None:
            motor.priority = int(data["priority"])
        if "weight" in data and data["weight"] is not None:
            if motor.status != "ACTIVO":
                raise ValueError("weight only applies when motor is ACTIVO")
            motor.weight = float(data["weight"])
        if "enabled" in data:
            # Convenience: enabled true/false → ACTIVO/INACTIVO
            motor.status = "ACTIVO" if bool(data["enabled"]) else "INACTIVO"
        motor.updated_by = user_id
        await self.db.flush()
        return self._to_dict(motor)

    async def run_numeric_relations(
        self,
        body: AnalyzeBody,
        *,
        user_id: UUID | None,
        trigger: str = "admin",
    ) -> dict[str, Any]:
        if not await self.is_executable("numeric_relations"):
            raise PermissionError(
                "Motor Relaciones Numéricas no está ACTIVO — no se ejecuta"
            )
        motor = await self.get_motor("numeric_relations")
        started = datetime.now(timezone.utc)
        limit = limit_from_body(body)
        result = await analyze_from_db(
            self.db,
            observed_number=body.observed_number,
            lottery_ids=list(body.lottery_ids),
            limit=limit,
        )
        payload = result.to_dict()
        ranking = list(payload.get("ranking") or [])
        total_score = sum(int(c.get("score") or 0) for c in ranking) or 0
        candidates: list[dict[str, Any]] = []
        for idx, cand in enumerate(ranking, start=1):
            score = int(cand.get("score") or 0)
            rel = (score / total_score) if total_score > 0 else 0.0
            candidates.append(
                {
                    "position": idx,
                    "number": cand.get("number"),
                    "score": score,
                    "score_share": round(rel, 6),  # distribución interna, NO probabilidad
                    "neighbors": cand.get("matched_neighbors") or cand.get("neighbors"),
                    "table2_code": cand.get("table2_code"),
                    "table2_group": cand.get("table2_group"),
                    "matches": cand.get("matches"),
                    "trace": cand.get("trace"),
                }
            )
        all_matches: list[dict[str, Any]] = []
        zero_score: list[dict[str, Any]] = []
        for cand in ranking:
            all_matches.extend(cand.get("matches") or [])
            if int(cand.get("score") or 0) == 0:
                zero_score.append(cand)

        out: dict[str, Any] = {
            **payload,
            "prediction_kind": "numeric_relations_historical_signal",
            "candidates": candidates,
            "ranking": ranking,
            "matches": all_matches,
            "companions_score_zero": zero_score,
            "disclaimer": PREDICTION_DISCLAIMER,
            "llm_calculates": False,
            "guarantees_outcome": False,
            "explanation": (
                "Los candidatos son compañeros fortalecidos por coincidencias históricas "
                "de vecinos (Tabla 2) ancladas en draw_id. score_share es solo la "
                "distribución relativa del score interno; no es probabilidad ni garantía."
            ),
            "warning": PREDICTION_DISCLAIMER,
            "motor": self._to_dict(motor) if motor else catalog_by_key()["numeric_relations"],
        }

        finished = datetime.now(timezone.utc)
        if motor:
            motor.last_run_at = finished
            motor.last_run_result = {
                "ok": True,
                "observed_number": body.observed_number,
                "candidates": len(candidates),
                "occurrences_used": payload.get("occurrences_used"),
            }
            motor.health = "ok"
            self.db.add(
                LotteryPredictionMotorRun(
                    motor_id=motor.id,
                    started_at=started,
                    finished_at=finished,
                    trigger=trigger,
                    input={
                        "observed_number": body.observed_number,
                        "lottery_ids": [str(x) for x in body.lottery_ids],
                        "occurrence_limit": limit.to_dict(),
                    },
                    output={
                        "candidates": len(candidates),
                        "occurrences_used": payload.get("occurrences_used"),
                        "top": candidates[0]["number"] if candidates else None,
                    },
                    ok=True,
                    user_id=user_id,
                )
            )
            await self.db.flush()
        return out

    @staticmethod
    def _to_dict(row: LotteryPredictionMotor) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "key": row.key,
            "name": row.name,
            "description": row.description,
            "status": row.status,
            "implemented": row.implemented,
            "implementation_ref": row.implementation_ref,
            "version": row.version,
            "priority": row.priority,
            "weight": float(row.weight) if row.weight is not None else None,
            "docs": row.docs,
            "health": row.health,
            "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
            "last_run_result": row.last_run_result,
            "can_activate": bool(row.implemented),
            "can_execute": bool(row.implemented and row.status == "ACTIVO"),
            "can_weight": bool(row.implemented and row.status == "ACTIVO"),
        }
