"""J-10L — Universo activo de análisis: únicamente loterías is_featured."""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lottery.numeric_relations.active_scope_policy import (
    ANALYSIS_SCOPE_LABEL,
    EXPECTED_PRODUCT_SEVEN_NAMES,
    SEED_FEATURED_SEVEN_NAMES,
    ActiveLottery,
    AnalysisScope,
    analysis_scope_for_featured,
    build_analysis_scope_metadata,
    filter_to_active_ids,
    name_set_discrepancy,
    scope_set_hash,
)
from app.models.lottery import LotteryLottery

__all__ = [
    "ANALYSIS_SCOPE_LABEL",
    "EXPECTED_PRODUCT_SEVEN_NAMES",
    "SEED_FEATURED_SEVEN_NAMES",
    "ActiveLottery",
    "AnalysisScope",
    "analysis_scope_for_featured",
    "build_analysis_scope_metadata",
    "filter_to_active_ids",
    "get_active_analysis_lotteries",
    "get_active_lottery_id_set",
    "get_archived_analysis_lotteries",
    "name_set_discrepancy",
    "resolve_active_scope_ids",
    "scope_set_hash",
]


async def get_active_analysis_lotteries(db: AsyncSession) -> list[ActiveLottery]:
    rows = (
        await db.execute(
            select(LotteryLottery.id, LotteryLottery.name, LotteryLottery.slug)
            .where(
                LotteryLottery.is_featured.is_(True),
                LotteryLottery.is_aggregate.is_(False),
            )
            .order_by(LotteryLottery.name.asc())
        )
    ).all()
    return [ActiveLottery(id=str(UUID(str(r.id))), name=r.name, slug=r.slug) for r in rows]


async def get_archived_analysis_lotteries(db: AsyncSession) -> list[ActiveLottery]:
    rows = (
        await db.execute(
            select(LotteryLottery.id, LotteryLottery.name, LotteryLottery.slug)
            .where(
                LotteryLottery.is_featured.is_(False),
                LotteryLottery.is_aggregate.is_(False),
            )
            .order_by(LotteryLottery.name.asc())
            .limit(500)
        )
    ).all()
    return [ActiveLottery(id=str(UUID(str(r.id))), name=r.name, slug=r.slug) for r in rows]


async def get_active_lottery_id_set(db: AsyncSession) -> set[str]:
    return {x.id for x in await get_active_analysis_lotteries(db)}


async def resolve_active_scope_ids(
    db: AsyncSession,
    requested: Sequence[str | UUID] | None,
    *,
    require_non_empty: bool = True,
) -> tuple[list[str], list[ActiveLottery], dict]:
    active = await get_active_analysis_lotteries(db)
    active_ids = {x.id for x in active}
    if not requested:
        accepted = [x.id for x in active]
        rejected: list[str] = []
    else:
        accepted, rejected = filter_to_active_ids(requested, active_ids)
        order = {x.id: i for i, x in enumerate(active)}
        accepted = sorted(accepted, key=lambda i: order.get(i, 10_000))
    if require_non_empty and not accepted:
        raise ValueError(
            "Ninguna lotería activa (destacada) quedó en el alcance. "
            "El análisis solo utiliza las loterías marcadas como destacadas."
        )
    active_used = [x for x in active if x.id in set(accepted)]
    meta = build_analysis_scope_metadata(active_used, rejected_ids=rejected)
    meta["name_discrepancy"] = name_set_discrepancy([x.name for x in active])
    return accepted, active_used, meta
