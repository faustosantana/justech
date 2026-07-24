"""API — Lottery IA Predicciones (registry + run NR)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.api.v1.lottery_ai_admin import require_ai_admin
from app.lottery.numeric_relations.api_schemas import AnalyzeBody
from app.services.lottery_prediction_service import PredictionMotorService

router = APIRouter(
    prefix="/lottery/admin/predictions",
    tags=["Lottery Predictions"],
)

_PERMS = ("lottery_admin_ai", "lottery.admin", "lottery_admin_tools")


class MotorPatchBody(BaseModel):
    status: str | None = None
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    weight: float | None = Field(default=None, ge=0, le=100)


@router.get("/motors")
async def list_prediction_motors(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    svc = PredictionMotorService(db)
    items = await svc.list_motors()
    return {"items": items, "source": "lottery.predictions.registry"}


@router.get("/motors/{key}")
async def get_prediction_motor(
    key: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    svc = PredictionMotorService(db)
    motor = await svc.get_motor(key)
    if motor is None:
        raise HTTPException(status_code=404, detail="motor not found")
    return svc._to_dict(motor)


@router.patch("/motors/{key}")
async def patch_prediction_motor(
    key: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    body: MotorPatchBody = Body(...),
) -> dict[str, Any]:
    svc = PredictionMotorService(db)
    try:
        return await svc.patch_motor(key, body.model_dump(exclude_unset=True), user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/numeric-relations/run")
async def run_numeric_relations_prediction(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    body: AnalyzeBody = Body(...),
) -> dict[str, Any]:
    svc = PredictionMotorService(db)
    try:
        return await svc.run_numeric_relations(body, user_id=user.id, trigger="admin")
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
