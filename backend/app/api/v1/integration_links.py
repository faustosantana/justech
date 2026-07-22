"""API — vinculación de usuario a integraciones."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.integration_connector import UserLinkCreateRequest, UserLinkResponse
from app.services.dynamic_connector_service import DynamicConnectorService

router = APIRouter(prefix="/integrations", tags=["Integraciones — Usuario"])


@router.post("/{provider_id}/link-user", response_model=UserLinkResponse)
async def link_user(
    provider_id: uuid.UUID,
    payload: UserLinkCreateRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> UserLinkResponse:
    ctx = require_tenant_context()
    svc = DynamicConnectorService(db, ctx.tenant_id, actor_id=user.id)
    try:
        data = await svc.link_user(provider_id, user.id, payload.model_dump())
        return UserLinkResponse(**data)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{provider_id}/unlink-user")
async def unlink_user(
    provider_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    ctx = require_tenant_context()
    svc = DynamicConnectorService(db, ctx.tenant_id, actor_id=user.id)
    await svc.unlink_user(provider_id, user.id)
    return {"ok": True}
