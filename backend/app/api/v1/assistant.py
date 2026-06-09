from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from app.services.assistant_service import AssistantService
from fastapi import APIRouter

router = APIRouter(prefix="/assistant", tags=["JAIOS Assistant"])


@router.post("/query", response_model=AssistantQueryResponse)
async def assistant_query(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    payload: AssistantQueryRequest,
) -> AssistantQueryResponse:
    ctx = require_tenant_context()
    service = AssistantService(db, ctx.tenant_id, user.id)
    return await service.query(payload)
