from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.llm.router import LLMRouter
from app.schemas.llm import LLMCompletionRequest, LLMCompletionResponse

router = APIRouter(prefix="/llm", tags=["LLM Router"])


@router.post("/completions", response_model=LLMCompletionResponse)
async def create_completion(
    data: LLMCompletionRequest,
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
) -> LLMCompletionResponse:
    ctx = require_tenant_context()
    router_service = LLMRouter(db)
    return await router_service.complete(data, tenant_id=ctx.tenant_id)
