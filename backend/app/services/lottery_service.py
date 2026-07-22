"""Servicio base del módulo lottery (Fase 1)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, text
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

    async def list_lotteries(self, *, limit: int = 50, offset: int = 0) -> LotteryListResponse:
        if not settings.lottery_module_enabled:
            return LotteryListResponse(
                items=[],
                total=0,
                module_enabled=False,
                note="Módulo deshabilitado.",
            )

        total = int((await self.db.execute(select(func.count()).select_from(LotteryLottery))).scalar_one())
        rows = (
            await self.db.execute(
                select(LotteryLottery)
                .order_by(LotteryLottery.name.asc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        note = None
        if total == 0:
            note = "Catálogo vacío: la importación histórica se realizará en Fase 2."

        return LotteryListResponse(
            items=[LotteryLotteryResponse.model_validate(r) for r in rows],
            total=total,
            module_enabled=True,
            note=note,
        )
