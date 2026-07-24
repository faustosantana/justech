"""Servicio base del módulo lottery (Fase 1)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.lottery import LotteryDraw, LotteryImportRun, LotteryLottery
from app.schemas.lottery import LotteryHealthResponse, LotteryListResponse, LotteryLotteryResponse


class LotteryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def health(self) -> LotteryHealthResponse:
        module_enabled = settings.lottery_module_enabled
        db_ok = False
        schema_ok = False
        lotteries_count = 0
        draws_count = 0
        import_status = "never"
        sync_status = "disabled"

        try:
            await self.db.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False

        if db_ok:
            try:
                lotteries_count = int(
                    (await self.db.execute(select(func.count()).select_from(LotteryLottery))).scalar_one()
                )
                draws_count = int(
                    (await self.db.execute(select(func.count()).select_from(LotteryDraw))).scalar_one()
                )
                schema_ok = True
            except Exception:
                schema_ok = False

            try:
                last_run = (
                    await self.db.execute(
                        select(LotteryImportRun).order_by(LotteryImportRun.created_at.desc()).limit(1)
                    )
                ).scalar_one_or_none()
                if last_run:
                    import_status = last_run.status
            except Exception:
                pass

        if settings.lottery_sync_enabled:
            sync_status = "configured_idle"
        else:
            sync_status = "disabled"

        note = None
        if not module_enabled:
            note = "Módulo deshabilitado (LOTTERY_MODULE_ENABLED=false)."
        elif schema_ok and lotteries_count == 0:
            note = "Esquema disponible; histórico aún no importado (Fase 2)."

        return LotteryHealthResponse(
            module_enabled=module_enabled,
            database_connection=db_ok,
            schema_available=schema_ok,
            import_status=import_status,
            sync_status=sync_status,
            timestamp=datetime.now(timezone.utc),
            lotteries_count=lotteries_count,
            draws_count=draws_count,
            note=note,
        )

    async def list_lotteries(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        searchable_only: bool = False,
        visible_only: bool = False,
        ai_only: bool = False,
        comparable_only: bool = False,
        include_aggregates: bool = False,
        featured_only: bool = True,
        include_archived: bool = False,
    ) -> LotteryListResponse:
        if not settings.lottery_module_enabled:
            return LotteryListResponse(
                items=[],
                total=0,
                module_enabled=False,
                note="Módulo deshabilitado.",
            )

        filters = []
        if not include_aggregates:
            filters.append(LotteryLottery.is_aggregate.is_(False))
        # J-10H: selectores ordinarios = solo destacadas (salvo include_archived admin).
        if include_archived:
            filters.append(LotteryLottery.is_featured.is_(False))
        elif featured_only:
            filters.append(LotteryLottery.is_featured.is_(True))
        if searchable_only:
            filters.append(LotteryLottery.is_searchable.is_(True))
        if visible_only:
            filters.append(LotteryLottery.is_visible.is_(True))
        if ai_only:
            filters.append(LotteryLottery.is_ai_enabled.is_(True))
        if comparable_only:
            filters.append(LotteryLottery.is_comparable.is_(True))

        count_q = select(func.count()).select_from(LotteryLottery)
        list_q = select(LotteryLottery)
        if filters:
            count_q = count_q.where(and_(*filters))
            list_q = list_q.where(and_(*filters))

        total = int((await self.db.execute(count_q)).scalar_one())
        rows = (
            await self.db.execute(
                list_q.order_by(LotteryLottery.display_order.asc(), LotteryLottery.name.asc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        note = None
        if total == 0:
            note = "Catálogo vacío o filtros sin resultados."

        return LotteryListResponse(
            items=[LotteryLotteryResponse.model_validate(r) for r in rows],
            total=total,
            module_enabled=True,
            note=note,
        )
