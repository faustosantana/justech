"""API del módulo Resultados de Loterías / Lotería IA."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx, get_current_user_optional
from app.config import settings
from app.core.admin_permissions import role_has_permission
from app.core.exceptions import forbidden
from app.core.tenant import get_current_role, require_tenant_context
from app.models.user import User
from pathlib import Path
from datetime import date as date_cls
from app.schemas.lottery import (
    CalendarWindowResponse,
    CompareRequest,
    ComparisonResponse,
    CrossLotteryResponse,
    DateQueryResponse,
    DrawsWindowResponse,
    FrequencyResponse,
    LotteryHealthResponse,
    LotteryListResponse,
    NextOccurrencesResponse,
    NumberSearchResponse,
    RangeQueryResponse,
    RepetitionResponse,
)
from app.schemas.lottery_chat import (
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatSendResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    SavedQueryListResponse,
    SavedQueryRename,
    SavedQueryResponse,
)
from app.schemas.lottery_admin import (
    LotteryAdminBulkRequest,
    LotteryAdminBulkResponse,
    LotteryAdminLotteryResponse,
    LotteryAdminLotteryUpdate,
    LotteryCatalogResponse,
    LotteryDashboardV2,
)
from app.services.lottery_admin_service import LotteryAdminService, to_admin_response
from app.services.lottery_aliases import describe_alias_resolution
from app.services.lottery_chat_service import LotteryChatService
from app.services.lottery_exceptions import LotteryQueryError
from app.services.lottery_export_service import LotteryExportService
from app.services.lottery_permissions import LOTTERY_CLIENT_ROLE
from app.services.lottery_product_service import LotteryProductService
from app.services.lottery_query_service import LotteryQueryService
from app.services.lottery_service import LotteryService
from app.schemas.lottery_product import (
    LotteryDashboardResponse,
    LotteryDetailResponse,
    LotteryExportRequest,
    LotteryExportResponse,
    LotteryFavoriteListResponse,
    LotteryFavoriteReorderRequest,
    LotteryFavoriteResponse,
    LotteryPreferences,
    LotteryPreferencesUpdate,
    LotteryRecentQueryListResponse,
)
from app.schemas.lottery_share import (
    LotteryShareCreateRequest,
    LotteryShareListResponse,
    LotteryShareResponse,
    LotterySharedViewResponse,
    LotterySyncDryRunRequest,
    LotterySyncDryRunResponse,
)
from app.services.lottery_share_service import LotteryShareService, view_shared_by_token
from app.services.lottery_sync_service import LotterySyncService

router = APIRouter(prefix="/lottery", tags=["Lottery"])


def require_lottery_permission(*permissions: str):
    async def _dep(user: CurrentUser, _: TenantCtx) -> None:
        if not settings.lottery_module_enabled:
            raise forbidden("Módulo Resultados de Loterías deshabilitado")
        role = get_current_role()
        if user.is_superadmin:
            return
        if not any(role_has_permission(role, p) for p in permissions):
            raise forbidden(f"Permiso requerido: {' o '.join(permissions)}")

    return Depends(_dep)


def _raise_query(exc: LotteryQueryError):
    raise exc.to_http() from exc


@router.get("/health", response_model=LotteryHealthResponse)
async def lottery_health(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> LotteryHealthResponse:
    role = get_current_role()
    if not user.is_superadmin and not role_has_permission(role, "lottery.access"):
        raise forbidden("Permiso requerido: lottery.access")
    return await LotteryService(db).health()


@router.get("/lotteries", response_model=LotteryListResponse)
async def list_lotteries(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    searchable_only: bool = False,
    visible_only: bool = False,
    ai_only: bool = False,
    comparable_only: bool = False,
    include_aggregates: bool = False,
    featured_only: bool = True,
    include_archived: bool = False,
) -> LotteryListResponse:
    # J-10H: por defecto solo destacadas; include_archived exige admin.
    if include_archived:
        role = get_current_role()
        if not user.is_superadmin and not (
            role_has_permission(role, "lottery.admin")
            or role_has_permission(role, "lottery_admin_lotteries")
        ):
            raise forbidden("Archivo histórico requiere lottery.admin")
    return await LotteryService(db).list_lotteries(
        limit=limit,
        offset=offset,
        searchable_only=searchable_only,
        visible_only=visible_only,
        ai_only=ai_only,
        comparable_only=comparable_only,
        include_aggregates=include_aggregates,
        featured_only=featured_only,
        include_archived=include_archived,
    )


@router.get("/aliases/resolve")
async def resolve_alias(
    q: Annotated[str, Query(min_length=1, max_length=128)],
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> dict:
    return describe_alias_resolution(q)


@router.get("/results/by-date", response_model=DateQueryResponse)
async def results_by_date(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search")],
    lottery: Annotated[str, Query(min_length=1)],
    date: date,
    game: str | None = None,
    include_numbers: bool = True,
) -> DateQueryResponse:
    try:
        return await LotteryQueryService(db).by_date(
            lottery, date, game=game, include_numbers=include_numbers
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/results/range", response_model=RangeQueryResponse)
async def results_range(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search")],
    lottery: Annotated[str, Query(min_length=1)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    game: str | None = None,
    number: str | None = None,
    position: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: int | None = None,
    sort: Literal["asc", "desc"] = "asc",
) -> RangeQueryResponse:
    try:
        return await LotteryQueryService(db).range(
            lottery,
            from_date,
            to_date,
            game=game,
            number=number,
            position=position,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/results/following-days", response_model=CalendarWindowResponse)
async def results_following_days(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search")],
    lottery: Annotated[str, Query(min_length=1)],
    date: date,
    days: Annotated[int, Query(ge=1)],
    include_base_date: bool = False,
    game: str | None = None,
) -> CalendarWindowResponse:
    try:
        return await LotteryQueryService(db).following_days(
            lottery, date, days, include_base_date=include_base_date, game=game
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/results/previous-days", response_model=CalendarWindowResponse)
async def results_previous_days(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search")],
    lottery: Annotated[str, Query(min_length=1)],
    date: date,
    days: Annotated[int, Query(ge=1)],
    include_base_date: bool = False,
    game: str | None = None,
) -> CalendarWindowResponse:
    try:
        return await LotteryQueryService(db).previous_days(
            lottery, date, days, include_base_date=include_base_date, game=game
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/results/following-draws", response_model=DrawsWindowResponse)
async def results_following_draws(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search")],
    lottery: Annotated[str, Query(min_length=1)],
    date: date,
    count: Annotated[int, Query(ge=1)],
    include_base_date: bool = False,
    game: str | None = None,
) -> DrawsWindowResponse:
    try:
        return await LotteryQueryService(db).following_draws(
            lottery, date, count, include_base_date=include_base_date, game=game
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/results/previous-draws", response_model=DrawsWindowResponse)
async def results_previous_draws(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search")],
    lottery: Annotated[str, Query(min_length=1)],
    date: date,
    count: Annotated[int, Query(ge=1)],
    include_base_date: bool = False,
    game: str | None = None,
) -> DrawsWindowResponse:
    try:
        return await LotteryQueryService(db).previous_draws(
            lottery, date, count, include_base_date=include_base_date, game=game
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/results/by-number", response_model=NumberSearchResponse)
async def results_by_number(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search")],
    lottery: Annotated[str, Query(min_length=1)],
    number: Annotated[str, Query(min_length=1, max_length=32)],
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    position: int | None = None,
    number_type: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: int | None = None,
) -> NumberSearchResponse:
    try:
        return await LotteryQueryService(db).by_number(
            lottery,
            number,
            from_date=from_date,
            to_date=to_date,
            position=position,
            number_type=number_type,
            page=page,
            page_size=page_size,
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/statistics/frequencies", response_model=FrequencyResponse)
async def statistics_frequencies(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.statistics")],
    lottery: Annotated[str, Query(min_length=1)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    position: int | None = None,
    number_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    order: Literal["asc", "desc"] = "desc",
) -> FrequencyResponse:
    try:
        return await LotteryQueryService(db).frequencies(
            lottery,
            from_date,
            to_date,
            position=position,
            number_type=number_type,
            limit=limit,
            order=order,
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/statistics/repetitions", response_model=RepetitionResponse)
async def statistics_repetitions(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.statistics")],
    lottery: Annotated[str, Query(min_length=1)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    min_count: Annotated[int, Query(ge=2)] = 2,
    position: int | None = None,
    number_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RepetitionResponse:
    try:
        return await LotteryQueryService(db).repetitions(
            lottery,
            from_date,
            to_date,
            min_count=min_count,
            position=position,
            number_type=number_type,
            limit=limit,
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/statistics/next-occurrences", response_model=NextOccurrencesResponse)
async def statistics_next_occurrences(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.statistics")],
    lottery: Annotated[str, Query(min_length=1)],
    number: Annotated[str, Query(min_length=1, max_length=32)],
    after_date: date,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    position: int | None = None,
) -> NextOccurrencesResponse:
    try:
        return await LotteryQueryService(db).next_occurrences(
            lottery, number, after_date, limit=limit, position=position
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/statistics/cross-lottery", response_model=CrossLotteryResponse)
async def statistics_cross_lottery(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.statistics", "lottery.compare")],
    lotteries: Annotated[str, Query(description="Comma-separated lottery ids/aliases")],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    mode: Literal["same_day", "within_range", "after_occurrence"] = "within_range",
    number: str | None = None,
) -> CrossLotteryResponse:
    names = [x.strip() for x in lotteries.split(",") if x.strip()]
    try:
        return await LotteryQueryService(db).cross_lottery(
            names, from_date, to_date, mode, number=number
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.post("/compare", response_model=ComparisonResponse)
async def compare_lotteries(
    body: CompareRequest,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.compare")],
) -> ComparisonResponse:
    try:
        return await LotteryQueryService(db).compare(
            body.lotteries,
            body.from_date,
            body.to_date,
            body.mode,
            position=body.position,
            number_type=body.number_type,
            include_draws=body.include_draws,
            limit=body.limit,
            intersection_scope=body.intersection_scope,
        )
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/client-isolation-check")
async def client_isolation_check(user: CurrentUser, _: TenantCtx) -> dict:
    role = get_current_role()
    return {
        "ok": True,
        "role": role,
        "is_lottery_client": role == LOTTERY_CLIENT_ROLE,
        "user_id": str(user.id),
    }


# --- Chat Lotería IA ---


def _make_chat(db, user) -> LotteryChatService:
    ctx = require_tenant_context()
    if not ctx.tenant_id:
        raise forbidden("Tenant requerido")
    return LotteryChatService(
        db,
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        role=get_current_role(),
        is_superadmin=bool(user.is_superadmin),
    )


def _session_resp(session) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        context=session.context or {},
        last_message_at=session.last_message_at,
        created_at=getattr(session, "created_at", None),
        updated_at=getattr(session, "updated_at", None),
    )


@router.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    body: ChatSessionCreate,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.chat")],
) -> ChatSessionResponse:
    svc = _make_chat(db, user)
    session = await svc.create_session(title=body.title)
    await db.commit()
    return _session_resp(session)


@router.get("/chat/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.chat")],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ChatSessionListResponse:
    svc = _make_chat(db, user)
    items = await svc.list_sessions(limit=limit)
    return ChatSessionListResponse(items=[_session_resp(s) for s in items], total=len(items))


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.chat")],
) -> ChatSessionResponse:
    svc = _make_chat(db, user)
    session = await svc.get_session(session_id)
    return _session_resp(session)


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.chat")],
) -> dict:
    svc = _make_chat(db, user)
    await svc.delete_session(session_id)
    await db.commit()
    return {"ok": True}


@router.post("/chat/sessions/{session_id}/clear-context", response_model=ChatSessionResponse)
async def clear_chat_context(
    session_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.chat")],
) -> ChatSessionResponse:
    svc = _make_chat(db, user)
    await svc.clear_context(session_id)
    session = await svc.get_session(session_id)
    await db.commit()
    return _session_resp(session)


@router.get("/chat/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
async def list_chat_messages(
    session_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.chat")],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChatMessageListResponse:
    svc = _make_chat(db, user)
    items, total = await svc.list_messages(session_id, limit=limit, offset=offset)
    return ChatMessageListResponse(
        items=[
            ChatMessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                tool_name=m.tool_name,
                tool_payload=m.tool_payload,
                created_at=m.created_at,
            )
            for m in items
        ],
        total=total,
    )


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatSendResponse)
async def send_chat_message(
    session_id: UUID,
    body: ChatMessageCreate,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.chat")],
) -> ChatSendResponse:
    svc = _make_chat(db, user)
    result = await svc.send_message(session_id, body.content)
    await db.commit()
    return ChatSendResponse(**result)


@router.get("/admin/ai/runtime")
async def admin_ai_runtime(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
) -> dict:
    """Sanitized Lottery IA runtime — no secrets."""
    from app.lottery.ai.runtime import runtime_snapshot

    _ = db  # reserved for future DB-backed prompt metrics
    return runtime_snapshot()


@router.get("/admin/ai/metrics")
async def admin_ai_metrics(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> dict:
    from app.lottery.ai.metrics import ai_quality_metrics

    return await ai_quality_metrics(db, days=days)


@router.post("/admin/ai/prompts/{version}/activate")
async def admin_ai_prompt_activate(
    version: str,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
) -> dict:
    from app.lottery.ai.prompts.lottery_assistant_system_v1 import activate_prompt_version

    p = activate_prompt_version(version)
    return {"ok": True, "active_version": p.version, "name": p.name}


@router.get("/admin/ai/prompts")
async def admin_ai_prompts(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_lottery_permission("lottery.admin")],
) -> dict:
    """Compat wrapper: never shadow Admin Center DB prompts with in-memory registry."""
    from app.core.tenant import require_tenant_context
    from app.services.lottery_ai_admin_service import LotteryAiAdminService

    ctx = require_tenant_context()
    svc = LotteryAiAdminService(db, tenant_id=ctx.tenant_id, user_id=user.id)
    data = await svc.list_prompts()
    await db.commit()
    items = list(data.get("items") or [])
    active = next((i for i in items if i.get("status") == "active"), None)
    # Keep legacy keys for older clients while exposing Admin Center contract.
    return {
        **data,
        "items": items,
        "versions": items,
        "active": active
        or {
            "name": data.get("active_version"),
            "version": data.get("active_version"),
            "status": "active" if data.get("active_version") else None,
        },
    }


@router.post("/chat/sessions/{session_id}/retry", response_model=ChatSendResponse)
async def retry_chat_message(
    session_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.chat")],
) -> ChatSendResponse:
    svc = _make_chat(db, user)
    result = await svc.retry_last(session_id)
    await db.commit()
    return ChatSendResponse(**result)


@router.get("/saved-queries", response_model=SavedQueryListResponse)
async def list_saved_queries(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.saved_queries")],
) -> SavedQueryListResponse:
    svc = _make_chat(db, user)
    rows = await svc.list_saved_queries()
    return SavedQueryListResponse(
        items=[
            SavedQueryResponse(
                id=r.id,
                name=r.name,
                payload=r.payload or {},
                description=getattr(r, "description", None),
                query_type=getattr(r, "query_type", None),
                is_favorite=bool(getattr(r, "is_favorite", False)),
                run_count=int(getattr(r, "run_count", 0) or 0),
                last_run_at=getattr(r, "last_run_at", None),
                tags=list(getattr(r, "tags", None) or []),
                created_at=getattr(r, "created_at", None),
                updated_at=getattr(r, "updated_at", None),
            )
            for r in rows
        ],
        total=len(rows),
    )


@router.patch("/saved-queries/{query_id}", response_model=SavedQueryResponse)
async def rename_saved_query(
    query_id: UUID,
    body: SavedQueryRename,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.saved_queries")],
) -> SavedQueryResponse:
    svc = _make_chat(db, user)
    row = await svc.rename_saved_query(query_id, body.name)
    await db.commit()
    return SavedQueryResponse(
        id=row.id,
        name=row.name,
        payload=row.payload or {},
        created_at=getattr(row, "created_at", None),
        updated_at=getattr(row, "updated_at", None),
    )


@router.delete("/saved-queries/{query_id}")
async def delete_saved_query(
    query_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.saved_queries")],
) -> dict:
    svc = _make_chat(db, user)
    await svc.delete_saved_query(query_id)
    await db.commit()
    return {"ok": True}


# --- Producto Fase 5 ---


def _make_product(db, user) -> LotteryProductService:
    ctx = require_tenant_context()
    if not ctx.tenant_id:
        raise forbidden("Tenant requerido")
    return LotteryProductService(db, tenant_id=ctx.tenant_id, user_id=user.id)


def _make_export(db, user) -> LotteryExportService:
    ctx = require_tenant_context()
    if not ctx.tenant_id:
        raise forbidden("Tenant requerido")
    return LotteryExportService(db, tenant_id=ctx.tenant_id, user_id=user.id)


@router.get("/dashboard", response_model=LotteryDashboardResponse)
async def lottery_dashboard(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> LotteryDashboardResponse:
    return await _make_product(db, user).dashboard()


@router.get("/dashboard/v2", response_model=LotteryDashboardV2)
async def lottery_dashboard_v2(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery_view")],
    from_date: date | None = None,
    to_date: date | None = None,
) -> LotteryDashboardV2:
    ctx = require_tenant_context()
    if not ctx.tenant_id:
        raise forbidden("Tenant requerido")
    return await LotteryAdminService(db).dashboard_v2(
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/dashboard/v3")
async def lottery_dashboard_v3(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery_view")],
    from_date: date | None = None,
    to_date: date | None = None,
):
    """Executive ops dashboard (Lottery 3.0)."""
    ctx = require_tenant_context()
    if not ctx.tenant_id:
        raise forbidden("Tenant requerido")
    return await LotteryAdminService(db).dashboard_v3(
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/sync/windows")
async def lottery_sync_windows(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.admin", "lottery_view")],
):
    from app.lottery.sync.dispatcher import dispatch_status

    return await dispatch_status(db)


@router.post("/admin/metadata/recompute")
async def admin_recompute_metadata(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin", "lottery_admin_lotteries")],
    lottery_id: UUID | None = None,
):
    """Recompute denormalized metadata from lottery_draws (fixes Real 2099 etc.). Does not enable sync."""
    from app.lottery.core.metadata import recompute_all_lottery_metadata, recompute_lottery_metadata

    if lottery_id:
        result = await recompute_lottery_metadata(db, lottery_id)
    else:
        result = await recompute_all_lottery_metadata(db)
    await db.commit()
    return result


@router.get("/analytics/coverage")
async def analytics_coverage(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search", "lottery.statistics")],
    lottery_id: UUID | None = None,
):
    from app.lottery.analytics import LotteryAnalyticsEngine

    return await LotteryAnalyticsEngine(db).coverage(lottery_id)


@router.get("/analytics/{lottery_id}/frequencies")
async def analytics_frequencies(
    lottery_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.statistics")],
    from_date: date | None = None,
    to_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    from app.lottery.analytics import LotteryAnalyticsEngine

    return await LotteryAnalyticsEngine(db).frequencies(
        lottery_id, from_date=from_date, to_date=to_date, limit=limit
    )


@router.get("/analytics/{lottery_id}/hot-cold")
async def analytics_hot_cold(
    lottery_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.statistics")],
    window_draws: Annotated[int, Query(ge=5, le=365)] = 30,
    cold_days_threshold: Annotated[int, Query(ge=1, le=3650)] = 30,
):
    from app.lottery.analytics import LotteryAnalyticsEngine

    return await LotteryAnalyticsEngine(db).hot_cold(
        lottery_id, window_draws=window_draws, cold_days_threshold=cold_days_threshold
    )


@router.get("/analytics/{lottery_id}/quality")
async def analytics_quality(
    lottery_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.statistics", "lottery.admin")],
):
    from app.lottery.analytics import LotteryAnalyticsEngine

    return await LotteryAnalyticsEngine(db).data_quality(lottery_id)


@router.get("/analytics/{lottery_id}/anomalies")
async def analytics_anomalies(
    lottery_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.statistics", "lottery.admin")],
):
    from app.lottery.analytics import LotteryAnalyticsEngine

    return await LotteryAnalyticsEngine(db).anomalies(lottery_id)


@router.get("/analytics/coincidences")
async def analytics_coincidences(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.compare", "lottery.statistics")],
    lottery_ids: Annotated[list[UUID], Query(min_length=2)],
    on_date: date | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
):
    from app.lottery.analytics import LotteryAnalyticsEngine

    return await LotteryAnalyticsEngine(db).coincidences(
        lottery_ids, on_date=on_date, from_date=from_date, to_date=to_date
    )


@router.get("/catalog", response_model=LotteryCatalogResponse)
async def lottery_catalog(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search", "lottery_view")],
    q: str | None = None,
    country: str | None = None,
    featured_only: bool = True,
    favorites_only: bool = False,
    include_archived: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> LotteryCatalogResponse:
    ctx = require_tenant_context()
    if not ctx.tenant_id:
        raise forbidden("Tenant requerido")
    if include_archived:
        role = get_current_role()
        if not user.is_superadmin and not (
            role_has_permission(role, "lottery.admin")
            or role_has_permission(role, "lottery_admin_lotteries")
        ):
            raise forbidden("Archivo histórico requiere lottery.admin")
    return await LotteryAdminService(db).list_catalog(
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        q=q,
        country=country,
        featured_only=featured_only,
        favorites_only=favorites_only,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/lotteries", response_model=list[LotteryAdminLotteryResponse])
async def admin_list_lotteries(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin", "lottery_admin_lotteries")],
    q: str | None = None,
    active: bool | None = None,
    visible: bool | None = None,
    sync_enabled: bool | None = None,
    featured: bool | None = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LotteryAdminLotteryResponse]:
    """Por defecto solo destacadas. featured=false → archivadas; omitir con cuidado (None=todas)."""
    rows, _total = await LotteryAdminService(db).list_admin(
        q=q,
        active=active,
        visible=visible,
        sync_enabled=sync_enabled,
        featured=featured,
        limit=limit,
        offset=offset,
    )
    return [to_admin_response(r) for r in rows]


@router.patch("/admin/lotteries/{lottery_id}", response_model=LotteryAdminLotteryResponse)
async def admin_update_lottery(
    lottery_id: UUID,
    body: LotteryAdminLotteryUpdate,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin", "lottery_admin_lotteries")],
) -> LotteryAdminLotteryResponse:
    svc = LotteryAdminService(db)
    lot = await svc.get(lottery_id)
    if not lot:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Lotería no encontrada")
    updated = await svc.update(lot, body)
    await db.commit()
    return to_admin_response(updated)


@router.post("/admin/lotteries/bulk", response_model=LotteryAdminBulkResponse)
async def admin_bulk_lotteries(
    body: LotteryAdminBulkRequest,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin", "lottery_admin_lotteries")],
) -> LotteryAdminBulkResponse:
    result = await LotteryAdminService(db).bulk(body)
    await db.commit()
    return result


@router.get("/lotteries/{slug}", response_model=LotteryDetailResponse)
async def lottery_detail(
    slug: str,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> LotteryDetailResponse:
    return await _make_product(db, user).get_lottery_by_slug(slug)


@router.get("/favorites", response_model=LotteryFavoriteListResponse)
async def list_favorites(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> LotteryFavoriteListResponse:
    return await _make_product(db, user).list_favorites()


@router.post("/favorites/{lottery_id}", response_model=LotteryFavoriteResponse)
async def add_favorite(
    lottery_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> LotteryFavoriteResponse:
    res = await _make_product(db, user).add_favorite(lottery_id)
    await db.commit()
    return res


@router.delete("/favorites/{lottery_id}")
async def remove_favorite(
    lottery_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> dict:
    await _make_product(db, user).remove_favorite(lottery_id)
    await db.commit()
    return {"ok": True}


@router.patch("/favorites/reorder", response_model=LotteryFavoriteListResponse)
async def reorder_favorites(
    body: LotteryFavoriteReorderRequest,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> LotteryFavoriteListResponse:
    res = await _make_product(db, user).reorder_favorites(body.lottery_ids)
    await db.commit()
    return res


@router.get("/recent-queries", response_model=LotteryRecentQueryListResponse)
async def list_recent_queries(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> LotteryRecentQueryListResponse:
    return await _make_product(db, user).list_recent()


@router.delete("/recent-queries/{recent_id}")
async def delete_recent_query(
    recent_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> dict:
    await _make_product(db, user).delete_recent(recent_id)
    await db.commit()
    return {"ok": True}


@router.delete("/recent-queries")
async def clear_recent_queries(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access", "lottery.search")],
) -> dict:
    await _make_product(db, user).clear_recent()
    await db.commit()
    return {"ok": True}


@router.get("/preferences", response_model=LotteryPreferences)
async def get_preferences(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> LotteryPreferences:
    return await _make_product(db, user).get_preferences()


@router.patch("/preferences", response_model=LotteryPreferences)
async def patch_preferences(
    body: LotteryPreferencesUpdate,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> LotteryPreferences:
    res = await _make_product(db, user).update_preferences(body)
    await db.commit()
    return res


@router.post("/exports", response_model=LotteryExportResponse)
async def create_export(
    body: LotteryExportRequest,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.export")],
) -> LotteryExportResponse:
    try:
        res = await _make_export(db, user).create(body)
        await db.commit()
        return res
    except LotteryQueryError as exc:
        _raise_query(exc)


@router.get("/exports/{export_id}", response_model=LotteryExportResponse)
async def get_export(
    export_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.export")],
) -> LotteryExportResponse:
    row = await _make_export(db, user).get(export_id)
    return LotteryExportResponse(
        export_id=row.id,
        status=row.status,
        filename=row.filename,
        mime_type=row.mime_type,
        size=row.size_bytes,
        row_count=row.row_count,
        expires_at=row.expires_at,
        download_url=f"/api/v1/lottery/exports/{row.id}/download",
    )


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.export")],
):
    from fastapi.responses import Response

    from app.core.content_disposition import build_content_disposition

    row, content = await _make_export(db, user).download(export_id)
    return Response(
        content=content,
        media_type=row.mime_type,
        headers={"Content-Disposition": build_content_disposition("attachment", row.filename)},
    )


@router.delete("/exports/{export_id}")
async def delete_export(
    export_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.export")],
) -> dict:
    await _make_export(db, user).delete(export_id)
    await db.commit()
    return {"ok": True}


@router.get("/me/home")
async def lottery_client_home_hint(
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    """Hint de redirección post-login para clientes del módulo."""
    role = get_current_role()
    return {
        "role": role,
        "is_lottery_client": role == LOTTERY_CLIENT_ROLE,
        "home_path": "/lottery" if role == LOTTERY_CLIENT_ROLE else "/dashboard",
        "allowed_ui_prefixes": ["/lottery"] if role == LOTTERY_CLIENT_ROLE else None,
    }


def _make_share(db: DbSession, user: CurrentUser) -> LotteryShareService:
    ctx = require_tenant_context()
    return LotteryShareService(db, tenant_id=ctx.tenant_id, user_id=user.id)


@router.post("/shares", response_model=LotteryShareResponse)
async def create_share(
    body: LotteryShareCreateRequest,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.share")],
) -> LotteryShareResponse:
    try:
        result = await _make_share(db, user).create(body)
        await db.commit()
        return result
    except LotteryQueryError as exc:
        _raise_query(exc)
        raise  # pragma: no cover


@router.get("/shares", response_model=LotteryShareListResponse)
async def list_shares(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.share")],
) -> LotteryShareListResponse:
    return await _make_share(db, user).list_mine()


@router.get("/shares/{share_id}", response_model=LotteryShareResponse)
async def get_share(
    share_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.share")],
) -> LotteryShareResponse:
    return await _make_share(db, user).get_mine(share_id)


@router.post("/shares/{share_id}/revoke", response_model=LotteryShareResponse)
async def revoke_share(
    share_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.share")],
) -> LotteryShareResponse:
    result = await _make_share(db, user).revoke(share_id)
    await db.commit()
    return result


@router.delete("/shares/{share_id}")
async def delete_share(
    share_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.share")],
) -> dict:
    await _make_share(db, user).delete(share_id)
    await db.commit()
    return {"ok": True}


@router.get("/shared/{token}", response_model=LotterySharedViewResponse)
async def view_shared(
    token: str,
    db: DbSession,
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> LotterySharedViewResponse:
    """Vista pública limitada del snapshot — sin sesión requerida."""
    if not settings.lottery_module_enabled:
        raise forbidden("Módulo Resultados de Loterías deshabilitado")
    result = await view_shared_by_token(db, token)
    await db.commit()
    return result


@router.post("/sync/dry-run", response_model=LotterySyncDryRunResponse)
async def sync_dry_run(
    body: LotterySyncDryRunRequest,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin")],
) -> LotterySyncDryRunResponse:
    """Dry-run de sincronización — nunca escribe sorteos."""
    svc = LotterySyncService(db, database_url=settings.database_url)
    from_d = date_cls.fromisoformat(body.from_date) if body.from_date else None
    to_d = date_cls.fromisoformat(body.to_date) if body.to_date else None
    report = await svc.dry_run(
        source=body.source,
        sqlite_path=Path("/Users/faustosantana/Projects/lottery-history-scraper/data/lottery.db"),
        from_date=from_d,
        to_date=to_d,
        lottery_source_id=body.lottery_source_id,
        limit=body.limit,
    )
    await db.commit()
    return LotterySyncDryRunResponse(
        run_id=report.run_id,
        dry_run=True,
        status=report.status,
        source=report.source,
        records_fetched=report.records_fetched,
        records_new=report.records_new,
        records_updated=report.records_updated,
        records_skipped=report.records_skipped,
        conflicts=report.conflicts,
        errors=report.errors,
        classifications=report.classifications,
        sample=report.sample,
        wrote_to_database=False,
    )


@router.get("/observability")
async def lottery_observability(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> dict:
    """Estado operativo del módulo — sin secretos."""
    from sqlalchemy import func, select

    from app.models.lottery import LotteryDraw, LotteryExport, LotterySharedQuery, LotterySyncRun

    draws = int(await db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    last_draw = await db.scalar(select(func.max(LotteryDraw.draw_date)))
    last_sync = await db.scalar(select(func.max(LotterySyncRun.completed_at)))
    last_write = await db.scalar(
        select(func.max(LotterySyncRun.completed_at)).where(
            LotterySyncRun.write_enabled.is_(True), LotterySyncRun.dry_run.is_(False)
        )
    )
    exports_ready = int(
        await db.scalar(select(func.count()).select_from(LotteryExport).where(LotteryExport.status == "ready")) or 0
    )
    shares_active = int(
        await db.scalar(
            select(func.count())
            .select_from(LotterySharedQuery)
            .where(LotterySharedQuery.revoked_at.is_(None))
        )
        or 0
    )
    return {
        "module_enabled": settings.lottery_module_enabled,
        "environment": "staging" if "jaios_lottery_staging" in (settings.database_url or "") else "local",
        "sync_enabled": settings.lottery_sync_enabled,
        "sync_write_enabled": settings.lottery_sync_write_enabled,
        "automatic_write_enabled": settings.lottery_sync_automatic_write_enabled,
        "scheduler_enabled": settings.lottery_scheduler_enabled,
        "scheduler_mode": settings.lottery_scheduler_mode,
        "scraping_enabled": settings.lottery_scraping_enabled,
        "draws_count": draws,
        "last_draw_date": last_draw.isoformat() if last_draw else None,
        "max_draw_date": last_draw.isoformat() if last_draw else None,
        "last_sync_attempt": last_sync.isoformat() if last_sync else None,
        "last_successful_sync": last_sync.isoformat() if last_sync else None,
        "last_write_sync": last_write.isoformat() if last_write else None,
        "exports_ready": exports_ready,
        "shares_non_revoked": shares_active,
        "llm_configured": bool(settings.openai_api_key or settings.anthropic_api_key),
        "timezone": settings.lottery_sync_timezone,
        "source_contract_version": settings.lottery_source_contract_version,
        "allowed_database": settings.lottery_sync_allowed_database,
        "allowed_port": settings.lottery_sync_allowed_port,
        "backup_gate": __import__(
            "app.services.lottery_sync_gate_backup", fromlist=["gate_backup_status_dict"]
        ).gate_backup_status_dict(database_url=settings.database_url),
        "worker_standalone": bool(settings.lottery_sync_worker_standalone),
    }


@router.get("/admin/sync/runs")
async def admin_sync_runs(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin")],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    from sqlalchemy import select

    from app.models.lottery import LotterySyncRun

    q = await db.execute(select(LotterySyncRun).order_by(LotterySyncRun.started_at.desc()).limit(limit))
    items = [
        {
            "id": str(r.id),
            "source": r.source,
            "status": r.status,
            "dry_run": r.dry_run,
            "write_enabled": r.write_enabled,
            "records_inserted": r.records_inserted,
            "records_unchanged": getattr(r, "records_unchanged", 0),
            "conflicts": r.conflicts,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "rollback_status": r.rollback_status,
        }
        for r in q.scalars().all()
    ]
    return {"items": items, "total": len(items)}


@router.get("/admin/sync/runs/{run_id}")
async def admin_sync_run_detail(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin")],
) -> dict:
    from app.models.lottery import LotterySyncRun

    r = await db.get(LotterySyncRun, run_id)
    if not r:
        raise forbidden("Run no encontrado")
    return {
        "id": str(r.id),
        "source": r.source,
        "status": r.status,
        "dry_run": r.dry_run,
        "write_enabled": r.write_enabled,
        "environment": r.environment,
        "from_date": r.from_date.isoformat() if r.from_date else None,
        "to_date": r.to_date.isoformat() if r.to_date else None,
        "checkpoint": r.checkpoint,
        "report": r.report,
        "inserted_draw_ids": r.inserted_draw_ids,
        "draws_before": r.draws_before,
        "draws_after": r.draws_after,
        "rollback_status": r.rollback_status,
        "change_policy": r.change_policy,
        "error_message": r.error_message,
    }


@router.post("/admin/sync/dry-run")
async def admin_sync_dry_run_write_path(
    body: LotterySyncDryRunRequest,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin")],
) -> dict:
    from app.services.lottery_sync_writer import LotterySyncWriter

    writer = LotterySyncWriter(db, database_url=settings.database_url)
    from_d = date_cls.fromisoformat(body.from_date) if body.from_date else None
    to_d = date_cls.fromisoformat(body.to_date) if body.to_date else None
    report = await writer.run(
        source=body.source if body.source in ("sqlite", "api", "fixture") else "fixture",
        write=False,
        from_date=from_d,
        to_date=to_d,
        lottery_source_id=body.lottery_source_id,
        limit=body.limit,
        initiated_by=str(user.id),
    )
    await db.commit()
    return {
        "run_id": str(report.run_id) if report.run_id else None,
        "dry_run": True,
        "wrote_to_database": False,
        "status": report.status,
        "classifications": report.classifications,
        "records_fetched": report.records_fetched,
        "records_new": report.records_new,
        "sample": report.sample,
    }


@router.get("/admin/scheduler")
async def admin_scheduler_status(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin")],
) -> dict:
    from app.services.lottery_scheduler import lottery_scheduler_running
    from app.services.lottery_scheduler_service import status_payload

    payload = await status_payload(db)
    payload["worker_running"] = lottery_scheduler_running()
    payload["requested_by"] = str(user.id)
    return payload


@router.post("/admin/scheduler/disable")
async def admin_scheduler_disable(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
) -> dict:
    from app.services.lottery_scheduler_service import LotterySchedulerService

    svc = LotterySchedulerService(db)
    state = await svc.set_mode("disabled", enabled=False, by=str(user.id))
    await db.commit()
    return {"mode": state.mode, "enabled": state.enabled}


@router.post("/admin/scheduler/enable")
async def admin_scheduler_enable(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
    mode: Annotated[str, Query()] = "observe",
) -> dict:
    """Habilita scheduler en modo observe (default). guarded_write requiere set-mode + confirmación."""
    from app.services.lottery_scheduler_service import LotterySchedulerService

    if (mode or "").lower() == "guarded_write":
        raise forbidden("Use /admin/scheduler/set-mode con confirmación fuerte")
    svc = LotterySchedulerService(db)
    state = await svc.set_mode(mode or "observe", enabled=True, by=str(user.id))
    await db.commit()
    return {"mode": state.mode, "enabled": state.enabled}


@router.post("/admin/scheduler/set-mode")
async def admin_scheduler_set_mode(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
    mode: Annotated[str, Query()],
    confirmation: Annotated[str | None, Query()] = None,
) -> dict:
    from app.services.lottery_scheduler_service import LotterySchedulerService

    svc = LotterySchedulerService(db)
    state = await svc.set_mode(
        mode,
        enabled=mode.lower() != "disabled",
        confirmation=confirmation,
        by=str(user.id),
    )
    await db.commit()
    return {"mode": state.mode, "enabled": state.enabled}


@router.post("/admin/scheduler/run-now")
async def admin_scheduler_run_now(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin")],
    source: Annotated[str, Query()] = "fixture",
) -> dict:
    from app.services.lottery_scheduler_service import LotterySchedulerService
    from app.services.lottery_sync_writer import FixtureSourceAdapter

    svc = LotterySchedulerService(db)
    fixture = FixtureSourceAdapter() if source == "fixture" else None
    result = await svc.tick(
        source=source if source in ("api", "fixture", "sqlite") else "fixture",
        fixture=fixture,
        force=True,
        initiated_by=f"admin:{user.id}",
    )
    await db.commit()
    return {
        "status": result.status,
        "mode": result.mode,
        "wrote": result.wrote,
        "blocked_reason": result.blocked_reason,
        "dry_run_id": result.dry_run_id,
        "write_run_id": result.write_run_id,
        "metrics": result.metrics,
        "alerts": result.alerts,
        "from_date": result.from_date,
        "to_date": result.to_date,
        "circuit_state": result.circuit_state,
    }


@router.get("/admin/scheduler/alerts")
async def admin_scheduler_alerts(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin", "lottery.audit")],
    status: Annotated[str | None, Query()] = "open",
) -> dict:
    from app.services.lottery_sync_alerts import list_alerts

    items = await list_alerts(db, status=status)
    return {
        "items": [
            {
                "id": str(a.id),
                "severity": a.severity,
                "code": a.code,
                "title": a.title,
                "message": a.message,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ]
    }


@router.post("/admin/scheduler/alerts/{alert_id}/acknowledge")
async def admin_scheduler_ack_alert(
    alert_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
) -> dict:
    from app.services.lottery_sync_alerts import acknowledge_alert

    alert = await acknowledge_alert(db, alert_id, by=str(user.id))
    if not alert:
        raise forbidden("Alerta no encontrada")
    await db.commit()
    return {"id": str(alert.id), "status": alert.status}


@router.post("/admin/scheduler/alerts/{alert_id}/resolve")
async def admin_scheduler_resolve_alert(
    alert_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
) -> dict:
    from app.services.lottery_sync_alerts import resolve_alert

    alert = await resolve_alert(db, alert_id, by=str(user.id))
    if not alert:
        raise forbidden("Alerta no encontrada")
    await db.commit()
    return {"id": str(alert.id), "status": alert.status}


@router.post("/admin/scheduler/circuit-breaker/reset")
async def admin_scheduler_reset_circuit(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.admin")],
) -> dict:
    from app.services.lottery_scheduler_service import LotterySchedulerService

    state = await LotterySchedulerService(db).reset_circuit(by=str(user.id))
    await db.commit()
    return {"circuit_state": state.circuit_state, "consecutive_failures": state.consecutive_failures}


@router.get("/admin/scheduler/history")
async def admin_scheduler_history(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin", "lottery.audit")],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> dict:
    from sqlalchemy import or_, select

    from app.models.lottery import LotterySyncRun

    q = await db.execute(
        select(LotterySyncRun)
        .where(
            or_(
                LotterySyncRun.initiated_by.ilike("%scheduler%"),
                LotterySyncRun.initiated_by.ilike("admin:%"),
            )
        )
        .order_by(LotterySyncRun.started_at.desc())
        .limit(limit)
    )
    # Fallback: recent runs if filter too strict
    items = list(q.scalars().all())
    if not items:
        q2 = await db.execute(select(LotterySyncRun).order_by(LotterySyncRun.started_at.desc()).limit(limit))
        items = list(q2.scalars().all())
    return {
        "items": [
            {
                "id": str(r.id),
                "source": r.source,
                "status": r.status,
                "mode": r.mode,
                "dry_run": r.dry_run,
                "records_inserted": r.records_inserted,
                "initiated_by": r.initiated_by,
                "started_at": r.started_at.isoformat() if r.started_at else None,
            }
            for r in items
        ]
    }
