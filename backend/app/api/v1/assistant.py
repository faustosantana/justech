from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse, CopilotBriefingResponse
from app.services.assistant_service import AssistantService
from app.services.copilot_briefing_service import CopilotBriefingService
from fastapi import APIRouter, Query

router = APIRouter(prefix="/assistant", tags=["JAIOS Assistant"])


@router.get("/briefing", response_model=CopilotBriefingResponse)
async def assistant_briefing(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    mode: str = Query(default="managerial", pattern="^(managerial|operational|bidding)$"),
) -> CopilotBriefingResponse:
    ctx = require_tenant_context()
    service = CopilotBriefingService(db, ctx.tenant_id, user.id)
    return await service.get_briefing(user, mode=mode)


@router.post("/conversations/reset")
async def reset_conversation(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    conversation_id: str = Query(min_length=36),
) -> dict[str, str]:
    from app.services.persistent_conversation_store import PersistentConversationStore

    ctx = require_tenant_context()
    store = PersistentConversationStore(db, ctx.tenant_id, user.id)
    await store.reset_conversation(conversation_id)
    await db.commit()
    return {"status": "ok", "conversation_id": conversation_id}


@router.put("/briefing-mode")
async def set_briefing_mode(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    conversation_id: str = Query(min_length=36),
    mode: str = Query(pattern="^(managerial|operational|bidding)$"),
) -> dict[str, str]:
    from app.services.persistent_conversation_store import PersistentConversationStore

    ctx = require_tenant_context()
    store = PersistentConversationStore(db, ctx.tenant_id, user.id)
    await store.set_briefing_mode(conversation_id, mode)
    await db.commit()
    return {"status": "ok", "mode": mode}


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
