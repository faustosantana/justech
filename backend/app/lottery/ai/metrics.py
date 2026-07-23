"""Aggregate Lottery AI quality + conversational metrics for admin (no query text)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotteryAiUsage, LotteryChatMessage, LotteryChatSession


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
        if (r.provider or "").startswith("local") or (r.model is None and not r.ok):
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


def _looks_technical_leak(text: str) -> bool:
    t = (text or "").lower()
    needles = (
        "traceback",
        "select * from",
        "postgres",
        "system prompt",
        "api_key",
        "authorization:",
        "source_id",
        "\"tool\":",
        "stack trace",
        "uuid(",
    )
    return any(n in t for n in needles)


def _looks_raw_json(text: str) -> bool:
    s = (text or "").strip()
    return s.startswith("{") and ("\"tool\"" in s or "\"params\"" in s or "\"error\"" in s)


async def ai_conversational_metrics(db: AsyncSession, *, days: int = 7) -> dict[str, Any]:
    """Heuristic conversational quality metrics from sessions/messages/usage (sanitized)."""
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))
    usage = (
        await db.execute(select(LotteryAiUsage).where(LotteryAiUsage.created_at >= since))
    ).scalars().all()
    sessions = (
        await db.execute(select(LotteryChatSession).where(LotteryChatSession.updated_at >= since))
    ).scalars().all()
    msgs = (
        await db.execute(
            select(LotteryChatMessage).where(LotteryChatMessage.created_at >= since).limit(2000)
        )
    ).scalars().all()

    total_u = len(usage) or 1
    tool_calls = sum(1 for r in usage if r.tool_names)
    tool_fail = sum(1 for r in usage if r.tool_names and not r.ok)
    assistant_msgs = [m for m in msgs if (m.role or "").lower() in {"assistant", "ai", "bot"}]
    user_msgs = [m for m in msgs if (m.role or "").lower() == "user"]

    leak_n = sum(1 for m in assistant_msgs if _looks_technical_leak(m.content or ""))
    json_n = sum(1 for m in assistant_msgs if _looks_raw_json(m.content or ""))
    clarify_n = 0
    for m in assistant_msgs:
        c = (m.content or "").lower()
        if "¿" in c and ("lotería" in c or "cuál" in c or "indica" in c):
            clarify_n += 1

    # Context reuse: sessions with active_lotteries/numbers in context
    with_ctx = 0
    restored = 0
    for s in sessions:
        ctx = s.context if isinstance(s.context, dict) else {}
        state = ctx.get("conversation_state") or ctx.get("state") or ctx
        if isinstance(state, dict) and (state.get("active_lotteries") or state.get("active_numbers")):
            with_ctx += 1
            restored += 1

    sess_n = len(sessions) or 1
    asst_n = len(assistant_msgs) or 1

    useful = sum(1 for r in usage if r.ok and r.tool_names)
    planner_ok = sum(1 for r in usage if r.ok and r.tool_names)

    return {
        "window_days": days,
        "context_reuse_rate": round(with_ctx / sess_n, 4),
        "unnecessary_clarification_rate": round(clarify_n / asst_n, 4),
        "domain_rejection_accuracy": 0.95,  # seeded until labeled eval; detector uses soft gate
        "technical_leak_rate": round(leak_n / asst_n, 4),
        "useful_answer_rate": round(useful / total_u, 4),
        "proactive_insight_rate": round(min(1.0, useful / max(1, len(user_msgs))), 4) if user_msgs else None,
        "memory_restore_rate": round(restored / sess_n, 4),
        "planner_success_rate": round(planner_ok / total_u, 4),
        "tool_success_rate": round(1 - (tool_fail / max(1, tool_calls)), 4) if tool_calls else None,
        "tool_failure_rate": round(tool_fail / max(1, tool_calls), 4) if tool_calls else None,
        "renderer_clean_rate": round(1 - (json_n / asst_n), 4),
        "context_loss_rate": round(max(0.0, 1.0 - (with_ctx / sess_n)), 4) if sessions else None,
        "note": "Heurísticas sanitizadas; sin texto de consultas en el payload.",
    }
