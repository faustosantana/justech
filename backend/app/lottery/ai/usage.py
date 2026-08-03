"""AI usage metrics recorder — Lottery 3.0 (real provider tokens + cost estimates)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotteryAiUsage

# Estimated USD rates per 1K tokens (input, output). Observability only — not billing.
# Keys are matched case-insensitively; longest prefix / substring wins via lookup helpers.
_MODEL_RATES_PER_1K: dict[str, tuple[float, float]] = {
    "deepseek-v4-flash": (0.00014, 0.00028),
    "deepseek-v3.2": (0.00027, 0.00110),
    "deepseek-v3": (0.00027, 0.00110),
    "deepseek": (0.00027, 0.00110),
    "gpt-5-mini": (0.00025, 0.00200),
    "gpt-5": (0.00125, 0.01000),
    "gpt-4.1-mini": (0.00040, 0.00160),
    "gpt-4.1": (0.00200, 0.00800),
    "gpt-4o-mini": (0.00015, 0.00060),
    "gpt-4o": (0.00250, 0.01000),
    "gpt-4-turbo": (0.01000, 0.03000),
    "gpt-4": (0.03000, 0.06000),
}

_PROVIDER_DEFAULT_PER_1K: dict[str, tuple[float, float]] = {
    "openai": (0.00250, 0.01000),
    "huawei": (0.00027, 0.00110),
    "huawei_modelarts": (0.00027, 0.00110),
}


def normalize_usage_tokens(usage: dict[str, Any] | None) -> tuple[int, int, int]:
    """Extract prompt/completion/total from provider usage payloads (OpenAI or Huawei style)."""
    if not isinstance(usage, dict):
        return 0, 0, 0
    prompt = int(
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("prompt_eval_count")
        or 0
    )
    completion = int(
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("eval_count")
        or 0
    )
    total = int(usage.get("total_tokens") or 0)
    if total <= 0:
        total = prompt + completion
    return max(0, prompt), max(0, completion), max(0, total)


def merge_usage(*parts: dict[str, Any] | None) -> dict[str, int]:
    """Sum token counts across multiple LLM calls in one chat turn."""
    prompt = completion = total = 0
    for part in parts:
        p, c, t = normalize_usage_tokens(part)
        prompt += p
        completion += c
        total += t
    if total <= 0:
        total = prompt + completion
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


def _rate_for_model(model: str | None, provider: str | None) -> tuple[float, float]:
    key = (model or "").strip().lower()
    if key:
        if key in _MODEL_RATES_PER_1K:
            return _MODEL_RATES_PER_1K[key]
        # Prefer longest matching known key (e.g. gpt-4o-mini before gpt-4o)
        matches = [k for k in _MODEL_RATES_PER_1K if k in key or key in k]
        if matches:
            matches.sort(key=len, reverse=True)
            return _MODEL_RATES_PER_1K[matches[0]]
    prov = (provider or "").strip().lower()
    if prov in _PROVIDER_DEFAULT_PER_1K:
        return _PROVIDER_DEFAULT_PER_1K[prov]
    if "openai" in prov:
        return _PROVIDER_DEFAULT_PER_1K["openai"]
    if "huawei" in prov or "deepseek" in prov:
        return _PROVIDER_DEFAULT_PER_1K["huawei"]
    return (0.002, 0.002)


def estimate_cost_usd(
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    model: str | None = None,
    provider: str | None = None,
    rate_per_1k: float | None = None,
) -> float:
    """Estimated USD cost for observability (not billing)."""
    if rate_per_1k is not None:
        return round(((prompt_tokens + completion_tokens) / 1000.0) * rate_per_1k, 6)
    in_rate, out_rate = _rate_for_model(model, provider)
    cost = (prompt_tokens / 1000.0) * in_rate + (completion_tokens / 1000.0) * out_rate
    return round(cost, 6)


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
    lottery_key: str | None = None,
) -> LotteryAiUsage:
    p = int(prompt_tokens or 0) if prompt_tokens is not None else None
    c = int(completion_tokens or 0) if completion_tokens is not None else None
    if total_tokens is None and (p is not None or c is not None):
        total_tokens = (p or 0) + (c or 0)
    if estimated_cost_usd is None and (p is not None or c is not None):
        estimated_cost_usd = estimate_cost_usd(
            prompt_tokens=p or 0,
            completion_tokens=c or 0,
            model=model,
            provider=provider,
        )
    lottery = (lottery_key or "").strip()[:64] or None
    row = LotteryAiUsage(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        provider=provider,
        model=model,
        prompt_tokens=p,
        completion_tokens=c,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        estimated_cost_usd=estimated_cost_usd,
        tool_names=tool_names or [],
        ok=ok,
        lottery_key=lottery,
    )
    db.add(row)
    await db.flush()
    return row
