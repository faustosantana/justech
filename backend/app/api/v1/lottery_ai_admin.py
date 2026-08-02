"""API — Centro de Administración de Lottery IA."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.config import settings
from app.core.admin_permissions import role_has_permission
from app.core.exceptions import forbidden, not_found
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    status: str | None = Query(None),
    severity: str | None = Query(None),
    code: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    return await _svc(db, user).list_alerts(status=status, severity=severity, code=code, limit=limit)


@router.post("/alerts/detector/run-now")
async def ai_alert_detector_run_now(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    """Manual detector run — uses Redis lock; never parallel with worker tick."""
    try:
        data = await _svc(db, user).run_alert_detector_now()
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.get("/alerts/{alert_id}")
async def ai_alert_get(
    alert_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
) -> dict:
    try:
        return await _svc(db, user).get_alert(alert_id)
    except Exception as e:
        _map_err(e)


@router.post("/alerts/{alert_id}/acknowledge")
async def ai_alert_ack(
    alert_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    try:
        data = await _svc(db, user).acknowledge_alert(alert_id, user_id=user.id, note=body.get("note"))
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/alerts/{alert_id}/resolve")
async def ai_alert_resolve(
    alert_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    try:
        data = await _svc(db, user).resolve_alert(alert_id, user_id=user.id, note=body.get("note"))
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/alerts/{alert_id}/silence")
async def ai_alert_silence(
    alert_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
    body: dict[str, Any] = Body(...),
) -> dict:
    try:
        until = body.get("until")
        if not until:
            raise HTTPException(status_code=400, detail="until_required")
        data = await _svc(db, user).silence_alert(
            alert_id, until=until, user_id=user.id, reason=body.get("reason")
        )
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/alerts/{alert_id}/reopen")
async def ai_alert_reopen(
    alert_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    try:
        data = await _svc(db, user).reopen_alert(alert_id, note=body.get("note"))
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.get("/alert-thresholds")
async def ai_alert_thresholds_get(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
) -> dict:
    return await _svc(db, user).get_alert_thresholds()


@router.put("/alert-thresholds")
async def ai_alert_thresholds_put(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(...),
) -> dict:
    data = await _svc(db, user).put_alert_thresholds(body.get("payload") or body, version_label=body.get("version_label"))
    await db.commit()
    return data


@router.get("/tones")
async def ai_tones_list(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
) -> dict:
    return await _svc(db, user).list_tones()


@router.get("/tones/preference")
async def ai_tones_preference_get(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
) -> dict:
    return await _svc(db, user).get_tone_preference()


@router.put("/tones/preference")
async def ai_tones_preference_put(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
    body: dict[str, Any] = Body(...),
) -> dict:
    data = await _svc(db, user).put_tone_preference(body)
    await db.commit()
    return data


@router.post("/tones/preference/reset")
async def ai_tones_preference_reset(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    data = await _svc(db, user).reset_tone_preference(scope=body.get("scope") or "user")
    await db.commit()
    return data


@router.post("/tones/preview")
async def ai_tones_preview(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
    body: dict[str, Any] = Body(...),
) -> dict:
    return await _svc(db, user).preview_tone(body)


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


@router.get("/prompt-runtime/status")
async def prompt_runtime_status(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    return await _svc(db, user).prompt_runtime_status()


@router.post("/prompt-runtime/seed-candidate")
async def prompt_runtime_seed_candidate(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    try:
        data = await _svc(db, user).ensure_reasoning_studio_candidate(activate=False)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/prompt-runtime/seed-rc35-candidate")
async def prompt_runtime_seed_rc35_candidate(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    """Create draft Lottery Analyst Prompt 7.0.0-rc3.5 (never auto-activates)."""
    try:
        data = await _svc(db, user).ensure_reasoning_studio_rc35_candidate(activate=False)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/prompts/{prompt_id}/publish-immutable")
async def ai_prompt_publish_immutable(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    """Publicar sin activar (draft → published). Guardar ≠ publicar ≠ activar."""
    try:
        data = await _svc(db, user).publish_prompt_immutable(prompt_id)
        await db.commit()
        return data
    except Exception as e:
        _map_err(e)


@router.post("/prompts/{prompt_id}/activate-dev")
async def ai_prompt_activate_dev(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    """Activar en runtime DEV (no hay botón Activar en Producción en esta fase)."""
    try:
        data = await _svc(db, user).activate_prompt_dev(prompt_id, reason=body.get("reason"))
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


@router.post("/models/probe")
async def ai_models_probe(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_models", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    data = await _svc(db, user).probe_model_connection()
    await db.commit()
    return data


@router.get("/conversation-settings")
async def ai_conversation_settings_get(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_models", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    """Lottery IA — proveedor conversacional (BD, no ENV)."""
    from app.services.lottery_ai_conversation_settings_service import (
        LotteryAiConversationSettingsService,
    )

    svc = LotteryAiConversationSettingsService(db, user_id=user.id)
    data = await svc.get_or_create_active()
    await db.commit()
    return data


@router.post("/conversation-settings/test")
async def ai_conversation_settings_test(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_models", "lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    from app.services.lottery_ai_conversation_settings_service import (
        LotteryAiConversationSettingsService,
    )

    svc = LotteryAiConversationSettingsService(db, user_id=user.id)
    try:
        data = await svc.test_connection(body)
        await db.commit()
        return data
    except Exception as e:
        await db.rollback()
        _map_err(e)


@router.put("/conversation-settings")
async def ai_conversation_settings_put(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_models", "lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    """Guardar solo si PROBAR CONEXIÓN pasa (test embebido)."""
    from app.services.lottery_ai_conversation_settings_service import (
        LotteryAiConversationSettingsService,
    )

    svc = LotteryAiConversationSettingsService(db, user_id=user.id)
    try:
        data = await svc.save(body, require_test_ok=True)
        await db.commit()
        return data
    except Exception as e:
        await db.rollback()
        _map_err(e)


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
    q: str | None = Query(None),
) -> dict:
    return await _svc(db, user).list_sessions(limit=limit, offset=offset, q=q)


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


@router.get("/publish-gates")
async def ai_publish_gates(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin(*_AI_ADMIN_PERMS)],
) -> dict:
    svc = _svc(db, user)
    data = await svc.publish_gates()
    await db.commit()
    return data


@router.post("/developer-mode")
async def ai_developer_mode(
    db: DbSession,
    user: CurrentUser,
    tenant: TenantCtx,
    _: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict:
    data = await _svc(db, user).audit_developer_mode(enabled=bool(body.get("enabled")))
    await db.commit()
    return data


# ---- Closeout: detector alias + benchmark 300 ----

@router.post("/alerts/detect-now")
async def ai_alerts_detect_now_alias(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    """Alias of /alerts/detector/run-now for closeout clients."""
    data = await _svc(db, user).run_alert_detector_now()
    await db.commit()
    return data


@router.post("/benchmarks/run-300")
async def ai_benchmark_run_300(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    data = await _svc(db, user).run_benchmark_300_suite()
    await db.commit()
    return data


@router.post("/benchmarks/compare-v2-v3")
async def ai_benchmark_compare_v2_v3(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    data = await _svc(db, user).compare_v2_v3_and_gate()
    await db.commit()
    return data


# ---- Control Center Prompt Studio (I-3..I-6) ----

@router.get("/prompt-studio/schema")
async def prompt_studio_schema(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    from app.lottery.ai.prompt_studio import prompt_schema
    from app.services.lottery_ai_contracts import LOTTERY_TOOL_CATALOG
    from app.lottery.ai.ui_catalog import TOOL_LABELS_ES, tool_label

    tools = []
    for t in LOTTERY_TOOL_CATALOG:
        meta = TOOL_LABELS_ES.get(t.name, {})
        tools.append(
            {
                "technical_name": t.name,
                "human_name": tool_label(t.name),
                "description": meta.get("description") or getattr(t, "description", ""),
                "examples": meta.get("examples"),
                "status": "registered",
            }
        )
    return {**prompt_schema(), "tools": tools}


@router.get("/prompts/{prompt_id}/compiled")
async def prompt_compiled(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
    q: str | None = Query(None),
) -> dict:
    from app.lottery.ai.prompt_studio import compile_prompt_from_blocks, estimate_tokens, scan_secrets

    svc = _svc(db, user)
    try:
        p = await svc.get_prompt(prompt_id)
    except Exception as e:
        _map_err(e)
        raise
    blocks = {k: str(v or "") for k, v in (p.get("blocks") or {}).items()}
    compiled = compile_prompt_from_blocks(blocks) if any(blocks.values()) else {
        "body": p.get("body") or "",
        "fragments": [{"key": "body", "title": "Body", "chars": len(p.get("body") or ""), "tokens": estimate_tokens(p.get("body") or "")}],
        "assembly_order": ["body"],
        "chars": len(p.get("body") or ""),
        "tokens_estimated": estimate_tokens(p.get("body") or ""),
    }
    body = compiled["body"]
    secrets = scan_secrets(body)
    matches = []
    if q:
        for i, line in enumerate(body.splitlines(), start=1):
            if q.lower() in line.lower():
                matches.append({"line": i, "text": line})
    return {
        "prompt_id": str(prompt_id),
        "compiled": compiled,
        "search_matches": matches,
        "secrets_detected": secrets,
        "view": "normal",
        "sensitive_stripped": True,
    }


@router.get("/prompt-studio/compare")
async def prompts_compare(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
    a: UUID = Query(...),
    b: UUID = Query(...),
) -> dict:
    svc = _svc(db, user)
    try:
        pa = await svc.get_prompt(a)
        pb = await svc.get_prompt(b)
    except Exception as e:
        _map_err(e)
        raise
    blocks_a = pa.get("blocks") or {}
    blocks_b = pb.get("blocks") or {}
    keys = sorted(set(blocks_a) | set(blocks_b))
    block_diff = []
    for k in keys:
        va, vb = blocks_a.get(k) or "", blocks_b.get(k) or ""
        if va != vb:
            block_diff.append({"key": k, "a_chars": len(va), "b_chars": len(vb), "changed": True})
    return {
        "a": {"id": pa["id"], "display_name": pa.get("display_name"), "version": pa["version"], "status_label": pa.get("status_label")},
        "b": {"id": pb["id"], "display_name": pb.get("display_name"), "version": pb["version"], "status_label": pb.get("status_label")},
        "block_diff": block_diff,
        "body_changed": (pa.get("body") or "") != (pb.get("body") or ""),
        "model_a": pa.get("recommended_model"),
        "model_b": pb.get("recommended_model"),
        "guide": pa.get("guide"),
    }


@router.post("/prompts/{prompt_id}/archive")
async def prompt_archive(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    from datetime import datetime, timezone

    svc = _svc(db, user)
    row = await db.get(__import__("app.models.lottery", fromlist=["LotteryAiPromptVersion"]).LotteryAiPromptVersion, prompt_id)
    if not row:
        raise not_found("prompt_not_found")
    if row.status == "active":
        raise HTTPException(status_code=400, detail="no_archivar_activo")
    row.status = "archived"
    row.archived_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    return await svc.get_prompt(prompt_id)


@router.post("/prompts/{prompt_id}/validate-draft")
async def prompt_validate_draft(
    prompt_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_prompts", "lottery_admin_ai", "lottery.admin")],
) -> dict:
    """BORRADOR → EN_VALIDACION (no publica / no activa)."""
    from app.lottery.ai.control_center_benchmark import run_intent_benchmark
    from app.lottery.ai.prompt_studio import scan_secrets

    svc = _svc(db, user)
    try:
        p = await svc.get_prompt(prompt_id)
    except Exception as e:
        _map_err(e)
        raise
    if p["status"] not in {"draft", "validated", "approved"}:
        raise HTTPException(status_code=400, detail="solo_borrador_o_validacion")
    secrets = scan_secrets(p.get("body") or "")
    if secrets:
        raise HTTPException(status_code=400, detail={"code": "secrets", "hits": secrets})
    bench = run_intent_benchmark()
    row = await db.get(__import__("app.models.lottery", fromlist=["LotteryAiPromptVersion"]).LotteryAiPromptVersion, prompt_id)
    if not row:
        raise not_found("prompt_not_found")
    row.benchmark_summary = {
        "p0_failures": bench["p0_failures"],
        "p1_failures": bench["p1_failures"],
        "can_approve": bench["can_approve"],
    }
    if bench["can_approve"]:
        row.status = "approved"
    else:
        row.status = "draft"
    await db.flush()
    await db.commit()
    return {
        "prompt": await svc.get_prompt(prompt_id),
        "benchmark": bench,
        "active_unchanged": True,
        "published": False,
    }


@router.post("/control-center/benchmark/run")
async def control_center_benchmark_run(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin")],
) -> dict:
    from app.lottery.ai.control_center_benchmark import run_intent_benchmark

    return run_intent_benchmark()


@router.post("/control-center/playground")
async def control_center_playground(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin("lottery_admin_ai", "lottery.admin", "lottery_admin_prompts")],
    body: dict[str, Any] = Body(...),
) -> dict:
    """Ejecuta intent contra borrador vs activo sin publicar."""
    import time

    from app.services.lottery_chat_context import LotterySessionContext
    from app.services.lottery_intent import resolve_intent

    message = str(body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message_required")
    ctx = LotterySessionContext()
    t0 = time.perf_counter()
    intent = resolve_intent(message, ctx)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "mode": body.get("mode") or "draft",
        "prompt_id": body.get("prompt_id"),
        "message": message,
        "intent": {
            "kind": intent.kind,
            "tool": getattr(intent.tool, "value", intent.tool),
            "params": intent.params,
            "clarify_message": intent.clarify_message,
            "refuse_message": intent.refuse_message,
        },
        "latency_ms": latency_ms,
        "note": "Playground de intent/planificación; no altera versión ACTIVA ni ejecuta motores salvo que se invoque analyze explícitamente en UI.",
        "active_unchanged": True,
    }
