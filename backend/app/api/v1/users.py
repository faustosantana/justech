"""API — usuarios del tenant (asignación de tareas)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.schemas.users import TenantUserListResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("", response_model=TenantUserListResponse)
async def list_tenant_users(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TenantUserListResponse:
    from app.core.tenant import require_tenant_context

    ctx = require_tenant_context()
    return await UserService(db, ctx.tenant_id).list_tenant_users(
        search=search,
        limit=limit,
        offset=offset,
    )
