"""Servicios de producto Fase 5 — dashboard, favoritos, prefs, recientes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import forbidden, not_found
from app.models.lottery import (
    LotteryAlias,
    LotteryDraw,
    LotteryDrawNumber,
    LotteryLottery,
    LotteryRecentQuery,
    LotterySavedQuery,
    LotteryUserFavorite,
    LotteryUserPreferences,
)
from app.schemas.lottery import DrawNumberResult, DrawResult, LotteryLotteryResponse
from app.schemas.lottery_product import (
    LotteryDashboardResponse,
    LotteryDetailResponse,
    LotteryFavoriteListResponse,
    LotteryFavoriteResponse,
    LotteryPreferences,
    LotteryPreferencesUpdate,
    LotteryRecentQueryListResponse,
    LotteryRecentQueryResponse,
)
from app.services.lottery_query_service import LotteryQueryService
from app.services.lottery_service import LotteryService


DISCLAIMER = (
    "Los resultados históricos y las estadísticas son únicamente informativos. "
    "No garantizan resultados futuros."
)


def _lot_resp(lot: LotteryLottery) -> LotteryLotteryResponse:
    return LotteryLotteryResponse.model_validate(lot)


class LotteryProductService:
    def __init__(self, db: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.catalog = LotteryService(db)
        self.query = LotteryQueryService(db)

    async def dashboard(self) -> LotteryDashboardResponse:
        health = await self.catalog.health()
        favs = await self.list_favorites()
        recent = await self.list_recent(limit=8)
        saved = await self.db.execute(
            select(LotterySavedQuery)
            .where(
                LotterySavedQuery.tenant_id == self.tenant_id,
                LotterySavedQuery.user_id == self.user_id,
            )
            .order_by(LotterySavedQuery.updated_at.desc())
            .limit(5)
        )
        saved_items = [
            {
                "id": str(r.id),
                "name": r.name,
                "query_type": r.query_type,
                "is_favorite": r.is_favorite,
                "run_count": r.run_count,
            }
            for r in saved.scalars().all()
        ]
        # coverage dates
        first = await self.db.scalar(select(func.min(LotteryDraw.draw_date)))
        last = await self.db.scalar(select(func.max(LotteryDraw.draw_date)))
        numbers = await self.db.scalar(select(func.count()).select_from(LotteryDrawNumber))
        return LotteryDashboardResponse(
            module_enabled=health.module_enabled,
            sync_enabled=False,
            lotteries_count=health.lotteries_count,
            draws_count=health.draws_count,
            numbers_count=int(numbers or 0),
            first_draw_date=first.isoformat() if first else None,
            last_draw_date=last.isoformat() if last else None,
            favorites=[f.lottery for f in favs.items],
            recent_queries=recent.items,
            saved_queries=saved_items,
            note="Sincronización automática desactivada en desarrollo.",
            disclaimer=DISCLAIMER,
        )

    async def get_lottery_by_slug(self, slug: str) -> LotteryDetailResponse:
        q = await self.db.execute(select(LotteryLottery).where(LotteryLottery.slug == slug))
        lot = q.scalar_one_or_none()
        if not lot:
            # try normalized / source_id
            if slug.isdigit():
                q = await self.db.execute(
                    select(LotteryLottery).where(LotteryLottery.source_id == int(slug))
                )
                lot = q.scalar_one_or_none()
        if not lot:
            raise not_found("Lotería no encontrada")
        aliases_q = await self.db.execute(
            select(LotteryAlias.alias).where(LotteryAlias.lottery_id == lot.id)
        )
        aliases = [a for (a,) in aliases_q.all()]
        is_fav = await self.db.scalar(
            select(func.count())
            .select_from(LotteryUserFavorite)
            .where(
                LotteryUserFavorite.tenant_id == self.tenant_id,
                LotteryUserFavorite.user_id == self.user_id,
                LotteryUserFavorite.lottery_id == lot.id,
            )
        )
        draws_q = await self.db.execute(
            select(LotteryDraw)
            .where(LotteryDraw.lottery_id == lot.id)
            .options(selectinload(LotteryDraw.numbers))
            .order_by(LotteryDraw.draw_date.desc(), LotteryDraw.draw_time.desc().nullslast())
            .limit(5)
        )
        recent: list[DrawResult] = []
        for d in draws_q.scalars().unique().all():
            nums = sorted(d.numbers, key=lambda n: (n.position, n.number_type))
            recent.append(
                DrawResult(
                    id=d.id,
                    draw_date=d.draw_date,
                    draw_time=d.draw_time,
                    game_name=d.game_name,
                    source_reference=d.source_reference,
                    numbers=[
                        DrawNumberResult(
                            position=n.position,
                            position_label=n.position_label,
                            number_value=n.number_value,
                            number_raw=n.number_raw,
                            number_type=n.number_type,
                        )
                        for n in nums
                    ],
                )
            )
        return LotteryDetailResponse(
            lottery=_lot_resp(lot),
            aliases=aliases,
            is_favorite=bool(is_fav),
            recent_draws=recent,
        )

    async def list_favorites(self) -> LotteryFavoriteListResponse:
        q = await self.db.execute(
            select(LotteryUserFavorite, LotteryLottery)
            .join(LotteryLottery, LotteryLottery.id == LotteryUserFavorite.lottery_id)
            .where(
                LotteryUserFavorite.tenant_id == self.tenant_id,
                LotteryUserFavorite.user_id == self.user_id,
            )
            .order_by(LotteryUserFavorite.display_order.asc(), LotteryUserFavorite.created_at.asc())
        )
        items = [
            LotteryFavoriteResponse(
                lottery_id=fav.lottery_id,
                lottery=_lot_resp(lot),
                display_order=fav.display_order,
                created_at=fav.created_at,
            )
            for fav, lot in q.all()
        ]
        return LotteryFavoriteListResponse(items=items, total=len(items))

    async def add_favorite(self, lottery_id: uuid.UUID) -> LotteryFavoriteResponse:
        lot = await self.db.get(LotteryLottery, lottery_id)
        if not lot:
            raise not_found("Lotería no encontrada")
        existing = await self.db.scalar(
            select(LotteryUserFavorite).where(
                LotteryUserFavorite.tenant_id == self.tenant_id,
                LotteryUserFavorite.user_id == self.user_id,
                LotteryUserFavorite.lottery_id == lottery_id,
            )
        )
        if existing:
            return LotteryFavoriteResponse(
                lottery_id=lottery_id,
                lottery=_lot_resp(lot),
                display_order=existing.display_order,
                created_at=existing.created_at,
            )
        max_ord = await self.db.scalar(
            select(func.coalesce(func.max(LotteryUserFavorite.display_order), -1)).where(
                LotteryUserFavorite.tenant_id == self.tenant_id,
                LotteryUserFavorite.user_id == self.user_id,
            )
        )
        row = LotteryUserFavorite(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            lottery_id=lottery_id,
            display_order=int(max_ord or -1) + 1,
        )
        self.db.add(row)
        await self.db.flush()
        return LotteryFavoriteResponse(
            lottery_id=lottery_id,
            lottery=_lot_resp(lot),
            display_order=row.display_order,
            created_at=row.created_at,
        )

    async def remove_favorite(self, lottery_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(LotteryUserFavorite).where(
                LotteryUserFavorite.tenant_id == self.tenant_id,
                LotteryUserFavorite.user_id == self.user_id,
                LotteryUserFavorite.lottery_id == lottery_id,
            )
        )
        await self.db.flush()

    async def reorder_favorites(self, lottery_ids: list[uuid.UUID]) -> LotteryFavoriteListResponse:
        q = await self.db.execute(
            select(LotteryUserFavorite).where(
                LotteryUserFavorite.tenant_id == self.tenant_id,
                LotteryUserFavorite.user_id == self.user_id,
            )
        )
        by_id = {f.lottery_id: f for f in q.scalars().all()}
        for i, lid in enumerate(lottery_ids):
            if lid in by_id:
                by_id[lid].display_order = i
        await self.db.flush()
        return await self.list_favorites()

    async def get_preferences(self) -> LotteryPreferences:
        row = await self._prefs_row()
        data = dict(row.preferences or {}) if row else {}
        return LotteryPreferences.model_validate({**LotteryPreferences().model_dump(), **data})

    async def update_preferences(self, patch: LotteryPreferencesUpdate) -> LotteryPreferences:
        row = await self._prefs_row(create=True)
        assert row is not None
        current = LotteryPreferences.model_validate(
            {**LotteryPreferences().model_dump(), **(row.preferences or {})}
        )
        updates = patch.model_dump(exclude_unset=True)
        merged = current.model_copy(update=updates)
        row.preferences = merged.model_dump(mode="json")
        await self.db.flush()
        return merged

    async def _prefs_row(self, *, create: bool = False) -> LotteryUserPreferences | None:
        q = await self.db.execute(
            select(LotteryUserPreferences).where(
                LotteryUserPreferences.tenant_id == self.tenant_id,
                LotteryUserPreferences.user_id == self.user_id,
            )
        )
        row = q.scalar_one_or_none()
        if row or not create:
            return row
        row = LotteryUserPreferences(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            preferences=LotteryPreferences().model_dump(mode="json"),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def record_recent(
        self, *, query_type: str, title: str, parameters: dict[str, Any]
    ) -> None:
        self.db.add(
            LotteryRecentQuery(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                query_type=query_type[:64],
                title=title[:255],
                parameters=parameters,
            )
        )
        # keep last 50
        ids = await self.db.execute(
            select(LotteryRecentQuery.id)
            .where(
                LotteryRecentQuery.tenant_id == self.tenant_id,
                LotteryRecentQuery.user_id == self.user_id,
            )
            .order_by(LotteryRecentQuery.created_at.desc())
            .offset(50)
        )
        old = [r for (r,) in ids.all()]
        if old:
            await self.db.execute(delete(LotteryRecentQuery).where(LotteryRecentQuery.id.in_(old)))
        await self.db.flush()

    async def list_recent(self, *, limit: int = 20) -> LotteryRecentQueryListResponse:
        q = await self.db.execute(
            select(LotteryRecentQuery)
            .where(
                LotteryRecentQuery.tenant_id == self.tenant_id,
                LotteryRecentQuery.user_id == self.user_id,
            )
            .order_by(LotteryRecentQuery.created_at.desc())
            .limit(min(limit, 50))
        )
        items = [
            LotteryRecentQueryResponse(
                id=r.id,
                query_type=r.query_type,
                title=r.title,
                parameters=r.parameters or {},
                created_at=r.created_at,
            )
            for r in q.scalars().all()
        ]
        return LotteryRecentQueryListResponse(items=items, total=len(items))

    async def delete_recent(self, recent_id: uuid.UUID) -> None:
        row = await self.db.get(LotteryRecentQuery, recent_id)
        if not row or row.tenant_id != self.tenant_id or row.user_id != self.user_id:
            raise not_found("Consulta reciente no encontrada")
        await self.db.delete(row)
        await self.db.flush()

    async def clear_recent(self) -> None:
        await self.db.execute(
            delete(LotteryRecentQuery).where(
                LotteryRecentQuery.tenant_id == self.tenant_id,
                LotteryRecentQuery.user_id == self.user_id,
            )
        )
        await self.db.flush()
