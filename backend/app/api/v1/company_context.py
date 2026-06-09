"""API — contexto global multiempresa."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import AdminMutator, AdminViewer, CurrentUser, DbSession, TenantCtx
from app.core.exceptions import JAIOSException
from app.core.tenant import require_tenant_context
from app.schemas.company_context import (
    AllowedCompaniesResponse,
    GlobalCompanyContextResponse,
    GlobalCompanyContextUpdate,
    UserCompaniesAdminResponse,
    UserCompaniesAdminUpdate,
)
from app.services.global_company_context_service import GlobalCompanyContextService

router = APIRouter(prefix="/company-context", tags=["Contexto multiempresa"])


def _svc(db: DbSession, user: CurrentUser) -> GlobalCompanyContextService:
    ctx = require_tenant_context()
    return GlobalCompanyContextService(db, ctx.tenant_id, user.id)


@router.get("", response_model=GlobalCompanyContextResponse)
async def get_company_context(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> GlobalCompanyContextResponse:
    return await _svc(db, user).get_context()


@router.put("", response_model=GlobalCompanyContextResponse)
async def set_company_context(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    payload: GlobalCompanyContextUpdate,
) -> GlobalCompanyContextResponse:
    try:
        return await _svc(db, user).set_context(payload)
    except JAIOSException as e:
        raise HTTPException(status_code=400, detail=e.message) from e


@router.get("/allowed", response_model=AllowedCompaniesResponse)
async def get_allowed_companies(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> AllowedCompaniesResponse:
    return await _svc(db, user).get_allowed()
