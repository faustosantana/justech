"""API — Mis Licitaciones / checklist preparación / pendientes / hoy."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.api.permission_deps import DGCP_MUTATE, DGCP_VIEW
from app.core.tenant import require_tenant_context
from app.schemas.dgcp_preparation import (
    ApplyTemplateRequest,
    ApplyTemplateResponse,
    AlertScanResponse,
    HoyResponse,
    MyLicitacionesResponse,
    PrepChecklistResponse,
    PrepTaskCreate,
    PrepTaskOut,
    PrepTaskUpdate,
    SetResponsibleRequest,
    TemplateCreate,
    TemplateOut,
)
from app.services.dgcp_my_work_service import DGCPMyWorkService

router = APIRouter(prefix="/dgcp/my-work", tags=["DGCP My Work"])


def _svc(db: DbSession, user: CurrentUser) -> DGCPMyWorkService:
    ctx = require_tenant_context()
    return DGCPMyWorkService(db, ctx.tenant_id, user.id)


@router.get("/licitations", response_model=MyLicitacionesResponse, dependencies=DGCP_VIEW)
async def list_my_licitations(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    scope: str = Query("mine", pattern="^(mine|team|unassigned|all)$"),
    company: str | None = None,
    q: str | None = None,
    limit: int = Query(100, ge=1, le=300),
) -> MyLicitacionesResponse:
    return await _svc(db, user).list_my_licitations(scope=scope, company=company, q=q, limit=limit)


@router.get("/hoy", response_model=HoyResponse, dependencies=DGCP_VIEW)
async def list_hoy(db: DbSession, user: CurrentUser, _: TenantCtx) -> HoyResponse:
    return await _svc(db, user).list_hoy()


@router.get("/pendientes", dependencies=DGCP_VIEW)
async def list_my_pendientes(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    filter_mode: str = Query("open", pattern="^(open|today|overdue|week|completed)$"),
    company: str | None = None,
) -> dict:
    return await _svc(db, user).list_my_pendientes(filter_mode=filter_mode, company=company)


@router.get(
    "/opportunities/{opportunity_id}/checklist",
    response_model=PrepChecklistResponse,
    dependencies=DGCP_VIEW,
)
async def get_prep_checklist(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> PrepChecklistResponse:
    try:
        return await _svc(db, user).get_checklist(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/items",
    response_model=PrepTaskOut,
    dependencies=DGCP_MUTATE,
)
async def add_prep_item(
    opportunity_id: uuid.UUID,
    data: PrepTaskCreate,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> PrepTaskOut:
    try:
        out = await _svc(db, user).create_task(opportunity_id, data)
        await db.commit()
        return out
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/tasks/{task_id}", response_model=PrepTaskOut, dependencies=DGCP_MUTATE)
async def update_prep_task(
    task_id: uuid.UUID,
    data: PrepTaskUpdate,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> PrepTaskOut:
    try:
        out = await _svc(db, user).update_task(task_id, data)
        await db.commit()
        return out
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/toggle", response_model=PrepTaskOut, dependencies=DGCP_MUTATE)
async def toggle_prep_task(
    task_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> PrepTaskOut:
    try:
        out = await _svc(db, user).toggle_complete(task_id)
        await db.commit()
        return out
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/apply-template",
    response_model=ApplyTemplateResponse,
    dependencies=DGCP_MUTATE,
)
async def apply_checklist_template(
    opportunity_id: uuid.UUID,
    data: ApplyTemplateRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> ApplyTemplateResponse:
    try:
        out = await _svc(db, user).apply_template(
            opportunity_id,
            template_id=data.template_id,
            assign_to_responsible=data.assign_to_responsible,
        )
        await db.commit()
        return out
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/responsible",
    response_model=PrepChecklistResponse,
    dependencies=DGCP_MUTATE,
)
async def set_responsible(
    opportunity_id: uuid.UUID,
    data: SetResponsibleRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> PrepChecklistResponse:
    try:
        out = await _svc(db, user).set_responsible(
            opportunity_id,
            responsible_user_id=data.responsible_user_id,
            reassign_open_tasks=data.reassign_open_tasks,
        )
        await db.commit()
        return out
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/templates", response_model=list[TemplateOut], dependencies=DGCP_VIEW)
async def list_templates(db: DbSession, user: CurrentUser, _: TenantCtx) -> list[TemplateOut]:
    return await _svc(db, user).list_templates()


@router.post("/templates", response_model=TemplateOut, dependencies=DGCP_MUTATE)
async def create_template(
    data: TemplateCreate,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> TemplateOut:
    out = await _svc(db, user).create_template(data)
    await db.commit()
    return out


@router.post("/alerts/scan", response_model=AlertScanResponse, dependencies=DGCP_MUTATE)
async def scan_alerts(db: DbSession, user: CurrentUser, _: TenantCtx) -> AlertScanResponse:
    result = await _svc(db, user).scan_and_emit_alerts()
    await db.commit()
    return AlertScanResponse(**result)
