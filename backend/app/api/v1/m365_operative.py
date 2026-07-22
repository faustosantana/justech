"""API Microsoft 365 Operativo — email intelligence + automatización."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.api.permission_deps import M365_VIEW, M365_MUTATE
from app.core.tenant import require_tenant_context
from app.schemas.m365_operative import (
    M365CalendarSuggestionsResponse,
    M365ExecuteActionRequest,
    M365ExecuteActionResponse,
    M365InboundEmailWebhook,
    M365OperativeDashboard,
    M365ProcessedEmailListResponse,
    M365ProcessedEmailResponse,
    M365SyncResponse,
)
from app.services.m365_operative_service import M365OperativeService

router = APIRouter(prefix="/operative", tags=["Microsoft 365 Operativo"])


def _service(db: DbSession, user: CurrentUser) -> M365OperativeService:
    ctx = require_tenant_context()
    return M365OperativeService(db, ctx.tenant_id, user_id=user.id)


@router.get("/dashboard", response_model=M365OperativeDashboard, dependencies=M365_VIEW)
async def operative_dashboard(db: DbSession, user: CurrentUser, _: TenantCtx) -> M365OperativeDashboard:
    return await _service(db, user).get_dashboard()


@router.get("/emails", response_model=M365ProcessedEmailListResponse, dependencies=M365_VIEW)
async def operative_emails(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    classification: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> M365ProcessedEmailListResponse:
    return await _service(db, user).list_emails(classification=classification, limit=limit)


@router.get("/emails/{email_id}", response_model=M365ProcessedEmailResponse, dependencies=M365_VIEW)
async def operative_email_detail(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    email_id: uuid.UUID,
) -> M365ProcessedEmailResponse:
    row = await _service(db, user).get_email(email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    return row


@router.post("/sync", response_model=M365SyncResponse, dependencies=M365_MUTATE)
async def operative_sync(db: DbSession, user: CurrentUser, _: TenantCtx) -> M365SyncResponse:
    try:
        return await _service(db, user).sync_inbox()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/emails/{email_id}/actions", response_model=M365ExecuteActionResponse, dependencies=M365_MUTATE)
async def operative_execute_action(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    email_id: uuid.UUID,
    payload: M365ExecuteActionRequest,
) -> M365ExecuteActionResponse:
    result = await _service(db, user).execute_action(
        email_id, payload.action_key, user=user, params=payload.params
    )
    if result.status == "error":
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.get("/calendar/suggestions", response_model=M365CalendarSuggestionsResponse, dependencies=M365_VIEW)
async def operative_calendar_suggestions(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> M365CalendarSuggestionsResponse:
    return await _service(db, user).calendar_suggestions()


@router.post("/webhooks/n8n/inbound-email", response_model=M365ProcessedEmailResponse)
async def n8n_inbound_email(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    payload: M365InboundEmailWebhook,
) -> M365ProcessedEmailResponse:
    """Webhook n8n: Outlook → JAIOS."""
    return await _service(db, user).ingest_webhook(payload)


@router.post("/webhooks/n8n/trigger/{workflow_id}")
async def n8n_trigger_outbound(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    workflow_id: str,
    payload: dict | None = None,
) -> dict:
    """Dispara flujo n8n saliente (JAIOS → Teams/Odoo/SharePoint)."""
    from integrations.n8n import N8nClient

    ctx = require_tenant_context()
    client = N8nClient(tenant_id=str(ctx.tenant_id))
    return await client.trigger_workflow(workflow_id, payload=payload or {})