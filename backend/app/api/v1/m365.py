import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.m365 import (
    M365HealthResponse,
    M365ListResponse,
    M365SearchResponse,
    M365StatusResponse,
)
from app.schemas.m365_account import (
    M365AccountListResponse,
    M365AccountPrepareRequest,
    M365AccountResponse,
)
from app.services.m365_account_service import M365AccountService
from app.services.m365_service import M365Service

router = APIRouter(prefix="/m365", tags=["Microsoft 365 Intelligence"])


def _service(db: DbSession, user: CurrentUser) -> M365Service:
    ctx = require_tenant_context()
    return M365Service(db, ctx.tenant_id, user_id=user.id)


@router.get("/health", response_model=M365HealthResponse)
async def m365_health(db: DbSession, user: CurrentUser, _: TenantCtx) -> M365HealthResponse:
    return await _service(db, user).health()


@router.get("/status", response_model=M365StatusResponse)
async def m365_status(db: DbSession, user: CurrentUser, _: TenantCtx) -> M365StatusResponse:
    return await _service(db, user).status()


@router.get("/outlook/messages", response_model=M365ListResponse)
async def m365_outlook_messages(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> M365ListResponse:
    return await _service(db, user).outlook_messages(search=search, limit=limit)


@router.get("/sharepoint/sites", response_model=M365ListResponse)
async def m365_sharepoint_sites(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> M365ListResponse:
    return await _service(db, user).sharepoint_sites(search=search, limit=limit)


@router.get("/onedrive/files", response_model=M365ListResponse)
async def m365_onedrive_files(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> M365ListResponse:
    return await _service(db, user).onedrive_files(search=search, limit=limit)


@router.get("/calendar/events", response_model=M365ListResponse)
async def m365_calendar_events(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> M365ListResponse:
    return await _service(db, user).calendar_events(limit=limit)


@router.get("/teams", response_model=M365ListResponse)
async def m365_teams(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> M365ListResponse:
    return await _service(db, user).teams(limit=limit)


@router.get("/documents", response_model=M365ListResponse)
async def m365_documents(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> M365ListResponse:
    return await _service(db, user).documents(search=search, limit=limit)


@router.get("/search", response_model=M365SearchResponse)
async def m365_search(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> M365SearchResponse:
    return await _service(db, user).search(q, limit=limit)


def _accounts(db: DbSession, user: CurrentUser) -> M365AccountService:
    ctx = require_tenant_context()
    return M365AccountService(db, ctx.tenant_id, actor_id=user.id)


@router.get("/accounts", response_model=M365AccountListResponse)
async def list_m365_accounts(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> M365AccountListResponse:
    return await _accounts(db, user).list_accounts()


@router.get("/accounts/me", response_model=M365AccountResponse | None)
async def my_m365_account(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> M365AccountResponse | None:
    return await _accounts(db, user).get_my_account(user.id)


@router.post("/accounts/prepare", response_model=M365AccountResponse, status_code=201)
async def prepare_m365_account(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    payload: M365AccountPrepareRequest,
) -> M365AccountResponse:
    try:
        return await _accounts(db, user).prepare_account(payload, actor_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_m365_account(
    db: DbSession, user: CurrentUser, _: TenantCtx, account_id: uuid.UUID
) -> None:
    if not await _accounts(db, user).delete_account(account_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
