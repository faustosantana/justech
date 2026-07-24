"""J-10L — Contexto de IA limitado al universo activo (is_featured)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.lottery.numeric_relations.active_scope import get_active_analysis_lotteries
from app.lottery.numeric_relations.active_scope_policy import (
    ACTIVE_ANALYSIS_USER_REPLY,
    build_analysis_scope_metadata,
)


async def active_lottery_context_for_llm(db: AsyncSession) -> dict[str, Any]:
    """Payload para el LLM: solo IDs/nombres activos. No ampliar por pregunta del usuario."""
    active = await get_active_analysis_lotteries(db)
    meta = build_analysis_scope_metadata(active)
    return {
        "active_lottery_ids": meta["active_lottery_ids"],
        "active_lottery_names": meta["active_lottery_names"],
        "active_lottery_count": meta["active_lottery_count"],
        "analysis_scope": meta["analysis_scope"],
        "scope_set_hash": meta["scope_set_hash"],
        "policy": "featured_only",
        "refusal_if_user_asks_all_db_lotteries": ACTIVE_ANALYSIS_USER_REPLY,
    }
