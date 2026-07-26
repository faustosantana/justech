"""Lottery IA Dashboard + Motor v1.0 freeze (read-only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.config import settings
from app.core.admin_permissions import role_has_permission
from app.core.exceptions import forbidden
from app.core.tenant import get_current_role
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
