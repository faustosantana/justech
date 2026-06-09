from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.work import WorkHubResponse
from app.services.work_service import WorkService

router = APIRouter(prefix="/work", tags=["Work Hub"])


@router.get("", response_model=WorkHubResponse)
async def get_work_hub(db: DbSession, user: CurrentUser, _: TenantCtx) -> WorkHubResponse:
    ctx = require_tenant_context()
    return await WorkService(db, ctx.tenant_id, user.id).get_hub()
