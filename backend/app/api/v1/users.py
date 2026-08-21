"""API — usuarios del tenant (asignación de tareas)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.admin import PlatformAccessResponse
from app.schemas.users import TenantUserListResponse
from app.services.admin_service import AdminService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/me/platform-access", response_model=PlatformAccessResponse)
async def my_platform_access(db: DbSession, user: CurrentUser, _: TenantCtx) -> PlatformAccessResponse:
    ctx = require_tenant_context()
    data = await AdminService(db, ctx.tenant_id, actor_id=user.id).get_platform_access(user)
    return PlatformAccessResponse(**data)


@router.get("", response_model=TenantUserListResponse)
async def list_tenant_users(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TenantUserListResponse:
    ctx = require_tenant_context()
    return await UserService(db, ctx.tenant_id).list_tenant_users(
        search=search,
        limit=limit,
        offset=offset,
    )
