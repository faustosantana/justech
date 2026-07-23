"""AI usage metrics recorder — Lottery 3.0."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotteryAiUsage


async def record_ai_usage(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    session_id: uuid.UUID | None = None,
    provider: str | None = None,
    model: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    latency_ms: int | None = None,
    estimated_cost_usd: float | None = None,
    tool_names: list[str] | None = None,
    ok: bool = True,
) -> LotteryAiUsage:
    row = LotteryAiUsage(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens
        if total_tokens is not None
        else (
            (prompt_tokens or 0) + (completion_tokens or 0)
            if prompt_tokens is not None or completion_tokens is not None
            else None
        ),
        latency_ms=latency_ms,
        estimated_cost_usd=estimated_cost_usd,
        tool_names=tool_names or [],
        ok=ok,
    )
    db.add(row)
    await db.flush()
    return row


def estimate_cost_usd(*, prompt_tokens: int = 0, completion_tokens: int = 0, rate_per_1k: float = 0.002) -> float:
    """Rough cost estimate for observability (not billing)."""
    return round(((prompt_tokens + completion_tokens) / 1000.0) * rate_per_1k, 6)
