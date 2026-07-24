"""Administración de loterías — Lottery 2.0."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.lottery import (
    LotteryDraw,
    LotteryDrawNumber,
    LotteryLottery,
    LotterySyncRun,
    LotteryUserFavorite,
)
from app.schemas.lottery_admin import (
    LotteryAdminBulkRequest,
    LotteryAdminBulkResponse,
    LotteryAdminLotteryResponse,
    LotteryAdminLotteryUpdate,
    LotteryCatalogCard,
    LotteryCatalogResponse,
    LotteryDashboardV2,
)


# J-10H — Universo de producto ordinario = is_featured (eligible_for_active_analysis).
_PRODUCT_SCOPE = (
    LotteryLottery.is_featured.is_(True),
    LotteryLottery.is_aggregate.is_(False),
)


class LotteryAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_admin(
        self,
        *,
        q: str | None = None,
        active: bool | None = None,
        visible: bool | None = None,
        sync_enabled: bool | None = None,
        featured: bool | None = True,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[LotteryLottery], int]:
        """Lista admin. Por defecto solo destacadas (producto). featured=False → archivadas."""
        stmt = select(LotteryLottery)
        count_stmt = select(func.count()).select_from(LotteryLottery)
        filters = [LotteryLottery.is_aggregate.is_(False)]
        if featured is True:
            filters.append(LotteryLottery.is_featured.is_(True))
        elif featured is False:
            filters.append(LotteryLottery.is_featured.is_(False))
        if q:
            like = f"%{q.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(LotteryLottery.name).like(like),
                    func.lower(LotteryLottery.slug).like(like),
                    func.lower(func.coalesce(LotteryLottery.commercial_name, "")).like(like),
                )
            )
        if active is not None:
            filters.append(LotteryLottery.active.is_(active))
        if visible is not None:
            filters.append(LotteryLottery.is_visible.is_(visible))
        if sync_enabled is not None:
            filters.append(LotteryLottery.is_sync_enabled.is_(sync_enabled))
        stmt = stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))
        total = int((await self.db.execute(count_stmt)).scalar_one())
        rows = (
            await self.db.execute(
                stmt.order_by(LotteryLottery.display_order.asc(), LotteryLottery.name.asc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return list(rows), total

    async def get(self, lottery_id: uuid.UUID) -> LotteryLottery | None:
        return await self.db.get(LotteryLottery, lottery_id)

    async def update(self, lottery: LotteryLottery, body: LotteryAdminLotteryUpdate) -> LotteryLottery:
        data = body.model_dump(exclude_unset=True)
        if data.get("is_auto_write_enabled") and not data.get("is_sync_enabled", lottery.is_sync_enabled):
            # Auto-write implies sync must be enabled
            if "is_sync_enabled" not in data:
                data["is_sync_enabled"] = True
        if data.get("is_auto_write_enabled") and not lottery.is_sync_enabled and not data.get("is_sync_enabled"):
            data["is_sync_enabled"] = True
        for key, value in data.items():
            setattr(lottery, key, value)
        await self.db.flush()
        await self.db.refresh(lottery)
        return lottery

    async def bulk(self, body: LotteryAdminBulkRequest) -> LotteryAdminBulkResponse:
        rows = (
            await self.db.execute(select(LotteryLottery).where(LotteryLottery.id.in_(body.lottery_ids)))
        ).scalars().all()
        updated = 0
        for lot in rows:
            if body.action == "enable":
                lot.active = True
            elif body.action == "disable":
                lot.active = False
            elif body.action == "show":
                lot.is_visible = True
                lot.is_visible_catalog = True
                lot.is_visible_dashboard = True
            elif body.action == "hide":
                lot.is_visible = False
                lot.is_visible_catalog = False
                lot.is_visible_dashboard = False
            elif body.action == "allow_search":
                lot.is_searchable = True
            elif body.action == "block_search":
                lot.is_searchable = False
            elif body.action == "enable_ai":
                lot.is_ai_enabled = True
            elif body.action == "disable_ai":
                lot.is_ai_enabled = False
            elif body.action == "enable_sync":
                lot.is_sync_enabled = True
            elif body.action == "disable_sync":
                lot.is_sync_enabled = False
                lot.is_auto_write_enabled = False
            elif body.action == "enable_auto_write":
                lot.is_sync_enabled = True
                lot.is_auto_write_enabled = True
            elif body.action == "disable_auto_write":
                lot.is_auto_write_enabled = False
            elif body.action == "feature":
                lot.is_featured = True
            elif body.action == "unfeature":
                lot.is_featured = False
            elif body.action == "set_order" and body.display_order is not None:
                lot.display_order = body.display_order
            else:
                continue
            updated += 1
        await self.db.flush()
        return LotteryAdminBulkResponse(updated=updated, action=body.action)

    async def list_catalog(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        q: str | None = None,
        country: str | None = None,
        featured_only: bool = True,
        favorites_only: bool = False,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> LotteryCatalogResponse:
        """Catálogo ordinario: solo is_featured. include_archived=True → solo no destacadas (admin)."""
        page = max(1, page)
        page_size = min(max(1, page_size), 500)
        filters = [
            LotteryLottery.is_aggregate.is_(False),
        ]
        if include_archived:
            filters.append(LotteryLottery.is_featured.is_(False))
        else:
            # J-10H: producto ordinario = destacadas (aunque featured_only llegue False).
            filters.append(LotteryLottery.is_featured.is_(True))
            filters.append(LotteryLottery.is_visible.is_(True))
            filters.append(LotteryLottery.is_visible_catalog.is_(True))
        if q:
            like = f"%{q.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(LotteryLottery.name).like(like),
                    func.lower(func.coalesce(LotteryLottery.commercial_name, "")).like(like),
                    func.lower(LotteryLottery.slug).like(like),
                )
            )
        if country:
            filters.append(LotteryLottery.country == country)
        # featured_only retained for API compat; ordinary path already forces featured.

        fav_ids: set[uuid.UUID] = set()
        fav_rows = (
            await self.db.execute(
                select(LotteryUserFavorite.lottery_id).where(
                    LotteryUserFavorite.tenant_id == tenant_id,
                    LotteryUserFavorite.user_id == user_id,
                )
            )
        ).scalars().all()
        fav_ids = set(fav_rows)
        if favorites_only:
            if not fav_ids:
                return LotteryCatalogResponse(items=[], total=0, page=page, page_size=page_size)
            filters.append(LotteryLottery.id.in_(fav_ids))

        where = and_(*filters)
        total = int(
            (await self.db.execute(select(func.count()).select_from(LotteryLottery).where(where))).scalar_one()
        )
        rows = (
            await self.db.execute(
                select(LotteryLottery)
                .where(where)
                .order_by(
                    LotteryLottery.is_featured.desc(),
                    LotteryLottery.display_order.asc(),
                    LotteryLottery.name.asc(),
                )
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        ).scalars().all()

        cards: list[LotteryCatalogCard] = []
        for lot in rows:
            last_numbers: list[str] = []
            if lot.last_draw_date:
                draw = (
                    await self.db.execute(
                        select(LotteryDraw)
                        .where(
                            LotteryDraw.lottery_id == lot.id,
                            LotteryDraw.draw_date == lot.last_draw_date,
                        )
                        .order_by(LotteryDraw.created_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if draw:
                    nums = (
                        await self.db.execute(
                            select(LotteryDrawNumber)
                            .where(LotteryDrawNumber.draw_id == draw.id)
                            .order_by(LotteryDrawNumber.position.asc())
                        )
                    ).scalars().all()
                    last_numbers = [n.number_value for n in nums]
            cards.append(
                LotteryCatalogCard(
                    id=lot.id,
                    slug=lot.slug,
                    name=lot.name,
                    commercial_name=lot.commercial_name,
                    short_name=lot.short_name,
                    country=lot.country,
                    country_code=getattr(lot, "country_code", None),
                    flag_emoji=getattr(lot, "flag_emoji", None),
                    timezone=lot.timezone,
                    logo_url=lot.logo_url,
                    icon_key=lot.icon_key,
                    is_featured=lot.is_featured,
                    is_favorite=lot.id in fav_ids,
                    draw_count=lot.draw_count,
                    last_draw_date=lot.last_draw_date,
                    last_numbers=last_numbers,
                    last_sync_at=lot.last_sync_at,
                    next_draw_estimated_at=lot.next_draw_estimated_at,
                    draw_times=lot.draw_times,
                    health_status=lot.health_status,
                    is_searchable=lot.is_searchable,
                    is_comparable=lot.is_comparable,
                    is_ai_enabled=lot.is_ai_enabled,
                    is_sync_enabled=lot.is_sync_enabled,
                )
            )
        return LotteryCatalogResponse(items=cards, total=total, page=page, page_size=page_size)

    async def dashboard_v2(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> LotteryDashboardV2:
        tz_name = settings.lottery_sync_timezone or "America/Santo_Domingo"
        try:
            today = datetime.now(ZoneInfo(tz_name)).date()
        except Exception:
            today = datetime.now(timezone.utc).date()
        # J-10H: KPIs de producto = solo is_featured (no contaminar con inventario histórico).
        active = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(LotteryLottery).where(*_PRODUCT_SCOPE)
                )
            ).scalar_one()
        )
        visible = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(LotteryLottery).where(
                        *_PRODUCT_SCOPE,
                        LotteryLottery.is_visible.is_(True),
                    )
                )
            ).scalar_one()
        )
        synced = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(LotteryLottery).where(
                        *_PRODUCT_SCOPE,
                        LotteryLottery.is_sync_enabled.is_(True),
                    )
                )
            ).scalar_one()
        )
        draws_hist = int((await self.db.execute(select(func.count()).select_from(LotteryDraw))).scalar_one())
        numbers = int(
            (await self.db.execute(select(func.count()).select_from(LotteryDrawNumber))).scalar_one()
        )
        featured_ids_sq = select(LotteryLottery.id).where(*_PRODUCT_SCOPE)
        results_today = int(
            (
                await self.db.execute(
                    select(func.count())
                    .select_from(LotteryDraw)
                    .where(
                        LotteryDraw.draw_date == today,
                        LotteryDraw.lottery_id.in_(featured_ids_sq),
                    )
                )
            ).scalar_one()
        )
        healthy = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(LotteryLottery).where(
                        *_PRODUCT_SCOPE,
                        LotteryLottery.health_status == "healthy",
                    )
                )
            ).scalar_one()
        )
        errored = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(LotteryLottery).where(
                        *_PRODUCT_SCOPE,
                        LotteryLottery.health_status == "error",
                    )
                )
            ).scalar_one()
        )
        # Prefer live draw/sync timestamps over fragile denormalized last_result_at
        last_draw_touch = (
            await self.db.execute(
                select(func.max(func.coalesce(LotteryDraw.updated_at, LotteryDraw.created_at)))
            )
        ).scalar_one_or_none()
        last_sync_touch = (
            await self.db.execute(select(func.max(LotterySyncRun.completed_at)))
        ).scalar_one_or_none()
        last_meta = (
            await self.db.execute(select(func.max(LotteryLottery.last_result_at)))
        ).scalar_one_or_none()
        candidates = [t for t in (last_draw_touch, last_sync_touch, last_meta) if t is not None]
        last_update = max(candidates) if candidates else None

        # Latest results: use actual max draw_date per lottery (ignore bogus metadata like 2099)
        latest_subq = (
            select(
                LotteryDraw.lottery_id.label("lottery_id"),
                func.max(LotteryDraw.draw_date).label("max_date"),
            )
            .group_by(LotteryDraw.lottery_id)
            .subquery()
        )
        latest_rows = (
            await self.db.execute(
                select(LotteryLottery, latest_subq.c.max_date)
                .join(latest_subq, latest_subq.c.lottery_id == LotteryLottery.id)
                .where(*_PRODUCT_SCOPE)
                .order_by(latest_subq.c.max_date.desc(), LotteryLottery.display_order.asc())
                .limit(12)
            )
        ).all()
        latest_results = []
        for lot, max_date in latest_rows:
            card_nums: list[str] = []
            draw = (
                await self.db.execute(
                    select(LotteryDraw)
                    .where(LotteryDraw.lottery_id == lot.id, LotteryDraw.draw_date == max_date)
                    .order_by(LotteryDraw.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if draw:
                nums = (
                    await self.db.execute(
                        select(LotteryDrawNumber)
                        .where(LotteryDrawNumber.draw_id == draw.id)
                        .order_by(LotteryDrawNumber.position.asc())
                    )
                ).scalars().all()
                card_nums = [n.number_value for n in nums]
            latest_results.append(
                {
                    "lottery": lot.commercial_name or lot.name,
                    "slug": lot.slug,
                    "date": max_date.isoformat() if max_date else None,
                    "numbers": card_nums,
                }
            )

        featured = (
            await self.list_catalog(
                tenant_id=tenant_id, user_id=user_id, featured_only=True, page=1, page_size=8
            )
        ).items
        favorites = (
            await self.list_catalog(
                tenant_id=tenant_id, user_id=user_id, favorites_only=True, page=1, page_size=8
            )
        ).items

        # Top/bottom numbers — solo sorteos de loterías destacadas (producto).
        freq_filters = [LotteryDraw.lottery_id.in_(select(LotteryLottery.id).where(*_PRODUCT_SCOPE))]
        if from_date:
            freq_filters.append(LotteryDraw.draw_date >= from_date)
        if to_date:
            freq_filters.append(LotteryDraw.draw_date <= to_date)
        freq_stmt = (
            select(LotteryDrawNumber.number_value, func.count().label("cnt"))
            .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
            .where(and_(*freq_filters))
            .group_by(LotteryDrawNumber.number_value)
            .order_by(func.count().desc())
            .limit(10)
        )
        top = [
            {"number": n, "count": int(c)}
            for n, c in (await self.db.execute(freq_stmt)).all()
        ]
        bottom_stmt = (
            select(LotteryDrawNumber.number_value, func.count().label("cnt"))
            .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
            .where(and_(*freq_filters))
            .group_by(LotteryDrawNumber.number_value)
            .order_by(func.count().asc())
            .limit(10)
        )
        bottom = [
            {"number": n, "count": int(c)}
            for n, c in (await self.db.execute(bottom_stmt)).all()
        ]

        first_d = (await self.db.execute(select(func.min(LotteryDraw.draw_date)))).scalar_one_or_none()
        last_d = (await self.db.execute(select(func.max(LotteryDraw.draw_date)))).scalar_one_or_none()

        return LotteryDashboardV2(
            lotteries_active=active,
            lotteries_visible=visible,
            lotteries_synced=synced,
            results_today=results_today,
            draws_historical=draws_hist,
            numbers_stored=numbers,
            last_update_at=last_update,
            sources_healthy=healthy,
            sources_error=errored,
            latest_results=latest_results,
            featured=featured,
            favorites=favorites,
            top_numbers=top,
            bottom_numbers=bottom,
            coverage={
                "first_draw_date": first_d.isoformat() if first_d else None,
                "last_draw_date": last_d.isoformat() if last_d else None,
                "lotteries_total": int(
                    (
                        await self.db.execute(select(func.count()).select_from(LotteryLottery))
                    ).scalar_one()
                ),
            },
            sync_summary={
                "sync_enabled_global": False,
                "lotteries_sync_enabled": synced,
                "lotteries_auto_write_enabled": int(
                    (
                        await self.db.execute(
                            select(func.count()).select_from(LotteryLottery).where(
                                *_PRODUCT_SCOPE,
                                LotteryLottery.is_auto_write_enabled.is_(True),
                            )
                        )
                    ).scalar_one()
                ),
                "product_scope": "FEATURED_SEVEN",
                "archived_inventory_excluded": True,
            },
        )

    async def dashboard_v3(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        from app.lottery.sync.dispatcher import dispatch_status
        from app.models.lottery import LotterySchedulerState, LotterySource
        from app.schemas.lottery_admin import LotteryDashboardV3

        base = await self.dashboard_v2(
            tenant_id=tenant_id, user_id=user_id, from_date=from_date, to_date=to_date
        )
        tz_name = settings.lottery_sync_timezone or "America/Santo_Domingo"
        try:
            today = datetime.now(ZoneInfo(tz_name)).date()
        except Exception:
            today = datetime.now(timezone.utc).date()

        windows = await dispatch_status(self.db)
        recent_runs = (
            await self.db.execute(
                select(LotterySyncRun).order_by(LotterySyncRun.started_at.desc()).limit(8)
            )
        ).scalars().all()
        run_rows = [
            {
                "id": str(r.id),
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "status": r.status,
                "dry_run": r.dry_run,
                "write_enabled": r.write_enabled,
                "records_inserted": r.records_inserted,
                "records_unchanged": r.records_unchanged,
                "records_new": r.records_new,
                "errors": r.errors,
                "mode": r.mode,
            }
            for r in recent_runs
        ]
        state = (await self.db.execute(select(LotterySchedulerState).limit(1))).scalar_one_or_none()
        circuits = []
        if state:
            circuits.append(
                {
                    "scope": "scheduler",
                    "state": state.circuit_state,
                    "reason": state.circuit_reason,
                    "opened_at": state.circuit_opened_at.isoformat() if state.circuit_opened_at else None,
                }
            )
        source_health: list[dict] = []
        try:
            sources = (
                await self.db.execute(
                    select(LotterySource).order_by(LotterySource.priority.asc()).limit(50)
                )
            ).scalars().all()
            source_health = [
                {
                    "lottery_id": str(s.lottery_id),
                    "source_key": s.source_key,
                    "role": s.role,
                    "health_status": s.health_status,
                    "circuit_state": s.circuit_state,
                    "latency_ema_ms": s.latency_ema_ms,
                    "enabled": s.enabled,
                }
                for s in sources
            ]
        except Exception:
            # DEV / esquemas parciales sin lottery_sources: no bloquear dashboard de producto.
            await self.db.rollback()
            source_health = []
        sync_lots = (
            await self.db.execute(
                select(LotteryLottery).where(
                    *_PRODUCT_SCOPE,
                    LotteryLottery.is_sync_enabled.is_(True),
                )
            )
        ).scalars().all()
        visible_lots = (
            await self.db.execute(
                select(LotteryLottery).where(*_PRODUCT_SCOPE)
            )
        ).scalars().all()

        async def _missing(lots: list) -> tuple[int, list[dict]]:
            n = 0
            detail = []
            for lot in lots:
                has_today = int(
                    (
                        await self.db.execute(
                            select(func.count())
                            .select_from(LotteryDraw)
                            .where(LotteryDraw.lottery_id == lot.id, LotteryDraw.draw_date == today)
                        )
                    ).scalar_one()
                )
                if has_today == 0:
                    n += 1
                    detail.append(
                        {
                            "source_id": lot.source_id,
                            "name": lot.commercial_name or lot.name,
                            "sync_enabled": lot.is_sync_enabled,
                            "auto_write": lot.is_auto_write_enabled,
                            "last_draw_date": lot.last_draw_date.isoformat() if lot.last_draw_date else None,
                        }
                    )
            return n, detail

        pending_sync, pending_sync_detail = await _missing(list(sync_lots))
        pending_vis, pending_vis_detail = await _missing(list(visible_lots))
        expected_today = len(visible_lots)
        pending = pending_sync  # backward-compatible primary pending = sync scope

        last_sync_at = (
            await self.db.execute(select(func.max(LotterySyncRun.completed_at)))
        ).scalar_one_or_none()
        next_sync_at = None
        if state and state.next_run_at:
            next_sync_at = state.next_run_at
        due = windows.get("sync_enabled_due") or []
        if due and due[0].get("next_draw_at"):
            # informational; worker loop also polls every 60s
            pass

        worker_status = {
            "standalone_configured": bool(settings.lottery_sync_worker_standalone),
            "scheduler_enabled": bool(settings.lottery_scheduler_enabled),
            "scheduler_mode": settings.lottery_scheduler_mode,
            "api_starts_scheduler": not bool(settings.lottery_sync_worker_standalone),
            "worker_owns_ticks": bool(settings.lottery_sync_worker_standalone),
            "loop_seconds": int(getattr(settings, "lottery_sync_worker_loop_seconds", 60) or 60),
        }

        from app.services.lottery_sync_gate_backup import gate_backup_status_dict

        backup_gate = gate_backup_status_dict(database_url=settings.database_url)
        operational_alerts: list[dict] = []
        if backup_gate.get("alert"):
            operational_alerts.append(
                {
                    "code": backup_gate["alert"],
                    "severity": "critical" if not backup_gate.get("ok") else "warning",
                    "message": f"Backup gate: {backup_gate['alert']}",
                }
            )
        if state and (state.circuit_state or "").lower() == "open":
            operational_alerts.append(
                {
                    "code": "circuit_breaker_open",
                    "severity": "error",
                    "message": state.circuit_reason or "Circuit breaker abierto",
                }
            )
        if bool(settings.lottery_sync_worker_standalone) and not last_sync_at:
            operational_alerts.append(
                {
                    "code": "scheduler_sin_tick",
                    "severity": "warning",
                    "message": "Worker standalone sin ticks registrados aún",
                }
            )
        for s in source_health:
            if (s.get("health_status") or "").lower() in {"degraded", "error", "down"}:
                operational_alerts.append(
                    {
                        "code": "fuente_degradada",
                        "severity": "warning",
                        "message": f"Fuente {s.get('source_key')}={s.get('health_status')}",
                    }
                )
        if pending_sync > 0:
            operational_alerts.append(
                {
                    "code": "resultado_esperado_pendiente",
                    "severity": "info",
                    "message": (
                        f"{pending_sync} lotería(s) con sync activa sin resultado de hoy "
                        "(solo 3 tienen sincronización automática)."
                    ),
                }
            )

        payload = base.model_dump()
        payload.update(
            {
                "local_today": today,
                "timezone": tz_name,
                "pending_results": pending,
                "expected_today": expected_today,
                "pending_sync_enabled": pending_sync,
                "pending_visible": pending_vis,
                "last_sync_at": last_sync_at,
                "next_sync_at": next_sync_at,
                "worker_status": worker_status,
                "recent_sync_runs": run_rows,
                "next_sync_windows": due,
                "circuit_breakers": circuits,
                "source_health": source_health,
                "backup_gate": backup_gate,
                "operational_alerts": operational_alerts,
                "results_today_note": (
                    "J-10H: todos los indicadores de producto usan únicamente las loterías "
                    "destacadas (is_featured). El inventario archivado no cuenta. "
                    "Resultados hoy = draws de hoy (TZ America/Santo_Domingo) de las siete. "
                    "Esperados = cantidad de loterías activas del producto. "
                    "Pendientes sync = destacadas con sync_enabled sin resultado de hoy. "
                    "Pendientes visibles = destacadas sin resultado de hoy."
                ),
                "kpis": {
                    "results_today": base.results_today,
                    "expected_today": expected_today,
                    "pending_sync_enabled": pending_sync,
                    "pending_visible": pending_vis,
                    "pending_sync_detail": pending_sync_detail[:20],
                    "pending_visible_detail": pending_vis_detail[:20],
                    "inserts_last_runs": sum(int(r.get("records_inserted") or 0) for r in run_rows),
                    "errors_last_runs": sum(int(r.get("errors") or 0) for r in run_rows),
                    "phases": windows.get("phases") or {},
                    "auto_write": windows.get("auto_write_lotteries") or [],
                    "sync_auto_write_note": "Solo 3 loterías tienen sincronización automática activa.",
                },
            }
        )
        return LotteryDashboardV3(**payload)


def to_admin_response(row: LotteryLottery) -> LotteryAdminLotteryResponse:
    return LotteryAdminLotteryResponse.model_validate(row)
