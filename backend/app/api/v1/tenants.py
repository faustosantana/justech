from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    data: TenantCreate,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> TenantResponse:
    service = TenantService(db)
    tenant = await service.create_tenant(data, owner=user)
    return TenantResponse.model_validate(tenant)


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(db: DbSession, _: CurrentUser, __: TenantCtx) -> TenantResponse:
    ctx = require_tenant_context()
    service = TenantService(db)
    tenant = await service.get_by_id(ctx.tenant_id)
    return TenantResponse.model_validate(tenant)
