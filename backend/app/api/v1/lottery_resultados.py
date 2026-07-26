"""Resultados center API — facade over LotteryResultService (reuses official sync/query)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.config import settings
from app.core.admin_permissions import role_has_permission
from app.core.exceptions import forbidden
from app.core.tenant import get_current_role
from app.services.lottery_result_service import LotteryResultService

router = APIRouter(prefix="/lottery/resultados", tags=["lottery-resultados"])


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


@router.get("/inventory")
async def resultados_inventory(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> dict:
    return await LotteryResultService(db).inventory()


@router.get("/sync-status")
async def resultados_sync_status(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> dict:
    return await LotteryResultService(db).sync_status()


@router.get("/lotteries")
async def resultados_lotteries(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> dict:
    items = await LotteryResultService(db).list_featured_lotteries()
    return {"items": items, "total": len(items)}


@router.get("")
async def resultados_list(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search", "lottery.access")],
    date_filter: date | None = Query(None, alias="date"),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    lottery: str | None = None,
    country: str | None = None,
    number: str | None = None,
    featured_only: bool = True,
    latest_n: int | None = Query(None, ge=1, le=90),
) -> dict:
    svc = LotteryResultService(db)
    if latest_n:
        items = await svc.get_latest_n_dates(latest_n, featured_only=featured_only)
    elif date_filter:
        items = await svc.get_by_date(
            date_filter,
            lottery=lottery,
            featured_only=featured_only,
            country=country,
            number=number,
        )
    elif from_date and to_date:
        items = await svc.get_range(
            from_date,
            to_date,
            lottery=lottery,
            featured_only=featured_only,
            country=country,
            number=number,
        )
    else:
        today = date.today()
        items = await svc.get_range(
            today - timedelta(days=1),
            today,
            lottery=lottery,
            featured_only=featured_only,
            country=country,
            number=number,
        )
    return {
        "items": items,
        "total": len(items),
        "filters": {
            "date": date_filter.isoformat() if date_filter else None,
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
            "lottery": lottery,
            "country": country,
            "number": number,
            "featured_only": featured_only,
        },
    }


@router.get("/pending")
async def resultados_pending(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
    date_filter: date | None = Query(None, alias="date"),
) -> dict:
    return await LotteryResultService(db).get_pending(date_filter)


@router.get("/history/{lottery}")
async def resultados_history(
    lottery: str,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.search", "lottery.access")],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict:
    return await LotteryResultService(db).get_history(lottery, page=page, page_size=page_size)


@router.post("/sync/trigger")
async def resultados_sync_trigger(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.sync", "lottery.admin")],
) -> dict:
    """Reuse existing scheduler tick — never a second scraper."""
    from app.services.lottery_scheduler_service import LotterySchedulerService

    if not settings.lottery_scheduler_enabled and not settings.lottery_sync_enabled:
        return {
            "ok": False,
            "reason": "SYNC_DISABLED",
            "message": "Enable lottery_sync_enabled / lottery_scheduler_enabled in DEV/UAT.",
            "reused": "LotterySchedulerService.tick",
            "production_modified": False,
        }
    svc = LotterySchedulerService(db, database_url=settings.database_url)
    result = await svc.tick(initiated_by=f"resultados-ui:{user.id}")
    await db.commit()
    status = await LotteryResultService(db).sync_status()
    return {
        "ok": True,
        "tick": {
            "status": result.status,
            "mode": result.mode,
            "wrote": result.wrote,
            "blocked_reason": result.blocked_reason,
        },
        "sync_status": status,
        "reused": "LotterySchedulerService.tick",
        "second_scraper_created": False,
        "production_modified": False,
    }
