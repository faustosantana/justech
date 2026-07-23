"""Aggregate Lottery AI quality metrics for admin (no query text)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotteryAiUsage


async def ai_quality_metrics(db: AsyncSession, *, days: int = 7) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))
    rows = (
        await db.execute(select(LotteryAiUsage).where(LotteryAiUsage.created_at >= since))
    ).scalars().all()
    total = len(rows)
    ok = sum(1 for r in rows if r.ok)
    latencies = [int(r.latency_ms) for r in rows if r.latency_ms is not None]
    providers: dict[str, int] = {}
    models: dict[str, int] = {}
    tools: dict[str, int] = {}
    fallbacks = 0
    for r in rows:
        providers[r.provider or "unknown"] = providers.get(r.provider or "unknown", 0) + 1
        models[r.model or "unknown"] = models.get(r.model or "unknown", 0) + 1
        if (r.provider or "").startswith("local") or r.model is None and not r.ok:
            fallbacks += 1
        for t in r.tool_names or []:
            tools[str(t)] = tools.get(str(t), 0) + 1
    return {
        "window_days": days,
        "since": since.isoformat(),
        "total_queries": total,
        "resolved_ok": ok,
        "resolved_rate": round(ok / total, 4) if total else None,
        "fallback_estimate": fallbacks,
        "fallback_rate": round(fallbacks / total, 4) if total else None,
        "latency_ms_avg": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "latency_ms_p95": sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else None,
        "providers": providers,
        "models": models,
        "tools_top": dict(sorted(tools.items(), key=lambda kv: kv[1], reverse=True)[:20]),
        "tokens_total": sum(int(r.total_tokens or 0) for r in rows),
        "note": "No se incluyen textos de consultas (privacidad).",
    }
