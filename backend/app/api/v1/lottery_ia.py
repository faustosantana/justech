"""Lottery IA Dashboard + Motor v1.0 freeze + Discovery Engine (read-only)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.config import settings
from app.core.admin_permissions import role_has_permission
from app.core.exceptions import forbidden
from app.core.tenant import get_current_role
from app.lottery.ai.analyst.discovery_engine import DiscoveryRequest, get_discovery_engine
from app.lottery.numeric_relations.analysis_engine.ia_dashboard import build_ia_dashboard
from app.lottery.numeric_relations.analysis_engine.motor_v1_freeze import (
    motor_v1_freeze_manifest,
    persist_freeze_artifact,
)

router = APIRouter(prefix="/lottery/ia", tags=["lottery-ia"])


def require_lottery_permission(*permissions: str):
    async def _dep(user: CurrentUser, _: TenantCtx) -> None:
        if not settings.lottery_module_enabled:
            raise forbidden("Módulo Resultados de Loterías deshabilitado")
        role = get_current_role()
        if user.is_superadmin:
            return
        if not any(role_has_permission(role, p) for p in permissions):
            raise forbidden(f"Permiso requerido: {' o '.join(permissions)}")

    return Depends(_dep)


class DiscoveryRunBody(BaseModel):
    kind: str = "auto_discovery"
    context: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)


@router.get("/dashboard")
async def lottery_ia_dashboard(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> dict:
    return await build_ia_dashboard(db)


@router.get("/motor-freeze")
async def lottery_ia_motor_freeze(
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> dict:
    """Read-only Motor v1.0 freeze. No PATCH/POST — UI cannot edit."""
    manifest = motor_v1_freeze_manifest()
    try:
        persist_freeze_artifact()
    except Exception:
        pass
    return manifest


@router.post("/discovery/run")
async def lottery_ia_discovery_run(
    body: DiscoveryRunBody,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    """Run observational Discovery Engine (read-only; never mutates motor/ranking)."""
    engine = get_discovery_engine()
    result = engine.discover(
        DiscoveryRequest(kind=body.kind, context=body.context, params=body.params)
    )
    return {
        "status": result.status,
        "enabled": result.enabled,
        "kind": result.kind,
        "version": getattr(engine, "VERSION", "2.2.0"),
        **(result.payload or {}),
    }


@router.get("/discovery/history")
async def lottery_ia_discovery_history(
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
    limit: int = 50,
    status: str | None = "published",
) -> dict:
    engine = get_discovery_engine()
    items = engine.list_history(limit=min(max(limit, 1), 200), status=status)
    return {"status": "ok", "count": len(items), "findings": items}
