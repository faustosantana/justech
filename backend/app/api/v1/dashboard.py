from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.dashboard import ExecutiveDashboardResponse
from app.services.executive_dashboard_service import ExecutiveDashboardService
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/executive", response_model=ExecutiveDashboardResponse)
async def get_executive_dashboard(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> ExecutiveDashboardResponse:
    ctx = require_tenant_context()
    tenant = await TenantService(db).get_by_id(ctx.tenant_id)
    tenant_name = tenant.name if tenant else "JAIOS"
    return await ExecutiveDashboardService(db, ctx.tenant_id, user.id).get_dashboard(
        user,
        tenant_name,
    )
