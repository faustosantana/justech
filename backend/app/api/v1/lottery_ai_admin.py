"""API — Centro de Administración de Lottery IA."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.config import settings
from app.core.admin_permissions import role_has_permission
from app.core.exceptions import bad_request, forbidden, not_found
from app.core.tenant import get_current_role, require_tenant_context
from app.services.lottery_ai_admin_service import LotteryAiAdminService

router = APIRouter(prefix="/lottery/admin/ai", tags=["Lottery AI Admin"])

_AI_ADMIN_PERMS = (
    "lottery_admin_ai",
    "lottery.admin",
    "lottery_admin_prompts",
    "lottery_admin_models",
    "lottery_admin_tools",
    "lottery_admin_safety",
)


def require_ai_admin(*permissions: str):
    perms = permissions or _AI_ADMIN_PERMS

    async def _dep(user: CurrentUser, _: TenantCtx) -> None:
        if not settings.lottery_module_enabled:
            raise forbidden("Módulo Resultados de Loterías deshabilitado")
        role = get_current_role()
        if user.is_superadmin:
            return
        if not any(role_has_permission(role, p) for p in perms):
            raise forbidden(f"Permiso requerido: {' o '.join(perms)}")

    return Depends(_dep)


def _svc(db: DbSession, user: CurrentUser) -> LotteryAiAdminService:
    ctx = require_tenant_context()
    return LotteryAiAdminService(db, tenant_id=ctx.tenant_id, user_id=user.id)


def _map_err(exc: Exception):
    if isinstance(exc, KeyError):
        raise not_found(str(exc)) from exc
    if isinstance(exc, PermissionError):
        raise forbidden(str(exc)) from exc
    if isinstance(exc, ValueError):
        raise bad_request(str(exc)) from exc
    raise exc


@router.get("/dashboard")
async def ai_dashboard(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
) -> dict:
    svc = _svc(db, user)
    data = await svc.dashboard()
    await db.commit()
    return data


@router.get("/alerts")
async def ai_alerts(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
) -> dict:
    return await _svc(db, user).list_alerts()


@router.get("/hermes")
async def ai_hermes(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
) -> dict:
    return await _svc(db, user).hermes_status()


@router.get("/prompts")
async def ai_prompts_list(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.list_prompts()
    await db.commit()
    return data


@router.get("/prompts/{prompt_id}")
async def ai_prompt_get(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        return await _svc(db, user).get_prompt(prompt_id)
    except Exception as e:
        _map_err(e)


@router.post("/prompts")
async def ai_prompt_create(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    try:
        data = await _svc(db, user).create_prompt_draft(body)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.put("/prompts/{prompt_id}")
async def ai_prompt_update(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    try:
        data = await _svc(db, user).update_prompt_draft(prompt_id, body)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/prompts/{prompt_id}/publish")
async def ai_prompt_publish(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    try:
        data = await _svc(db, user).publish_prompt(prompt_id, force=bool(body.get("force")))
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/prompts/{prompt_id}/rollback")
async def ai_prompt_rollback(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        data = await _svc(db, user).rollback_prompt(prompt_id)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.get("/models")
async def ai_models(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_models", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    return await _svc(db, user).models_status()


@router.get("/agent")
async def ai_agent_get(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.get_agent()
    await db.commit()
    return data


@router.put("/agent")
async def ai_agent_put(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else body
    data = await _svc(db, user).save_agent_draft(
        payload, version_label=body.get("version_label")
    )
    await db.commit()
    return data


@router.post("/agent/publish")
async def ai_agent_publish(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        data = await _svc(db, user).publish_agent()
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/agent/revert")
async def ai_agent_revert(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        data = await _svc(db, user).revert_agent()
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.get("/memory")
async def ai_memory(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.memory_status()
    await db.commit()
    return data


@router.get("/memory/sessions/{session_id}")
async def ai_memory_session(
    session_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        return await _svc(db, user).inspect_session(session_id)
    except Exception as e:
        _map_err(e)


@router.post("/memory/sessions/{session_id}/clear")
async def ai_memory_clear(
    session_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        data = await _svc(db, user).clear_session(session_id)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.get("/tools")
async def ai_tools(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_tools", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.list_tools()
    await db.commit()
    return data


@router.patch("/tools/{name}")
async def ai_tool_patch(
    name: str,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_tools", "lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    try:
        data = await _svc(db, user).patch_tool(name, body)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.get("/analysis-packs")
async def ai_packs_get(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.get_packs()
    await db.commit()
    return data


@router.put("/analysis-packs")
async def ai_packs_put(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    items = body.get("items") if isinstance(body.get("items"), list) else None
    if items is None:
        items = body.get("packs") if isinstance(body.get("packs"), list) else None
    if items is None and isinstance(body, list):
        items = body
    data = await _svc(db, user).put_packs(items or [])
    await db.commit()
    return data


@router.get("/defaults")
async def ai_defaults_get(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.get_defaults()
    await db.commit()
    return data


@router.put("/defaults")
async def ai_defaults_put(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    defaults = body.get("defaults") if isinstance(body.get("defaults"), dict) else body
    data = await _svc(db, user).put_defaults(defaults)
    await db.commit()
    return data


@router.get("/safety")
async def ai_safety_get(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_safety", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.get_safety()
    await db.commit()
    return data


@router.post("/safety/run-tests")
async def ai_safety_run(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_safety", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    data = await _svc(db, user).run_safety_tests()
    await db.commit()
    return data


@router.post("/playground")
async def ai_playground(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    # Normalize FE playground payload
    if "context" in body and "state" not in body:
        body = {**body, "state": body.get("context") or {}}
    return await _svc(db, user).playground(body)


@router.get("/benchmarks")
async def ai_benchmarks_list(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.list_benchmarks()
    await db.commit()
    return data


@router.post("/benchmarks")
async def ai_benchmarks_create(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    data = await _svc(db, user).create_benchmark(body)
    await db.commit()
    return data


@router.post("/benchmarks/{benchmark_id}/run")
async def ai_benchmarks_run(
    benchmark_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        data = await _svc(db, user).run_benchmark(benchmark_id)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.get("/sessions")
async def ai_sessions(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return await _svc(db, user).list_sessions(limit=limit, offset=offset)


@router.get("/versions")
async def ai_versions(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    svc = _svc(db, user)
    data = await svc.list_versions()
    await db.commit()
    return data


@router.post("/versions/{version_id}/publish")
async def ai_versions_publish(
    version_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        data = await _svc(db, user).publish_version(version_id)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/versions/{version_id}/rollback")
async def ai_versions_rollback(
    version_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        data = await _svc(db, user).rollback_version(version_id)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.get("/audit")
async def ai_audit(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin", "lottery.audit")],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return await _svc(db, user).list_audit(limit=limit, offset=offset)
