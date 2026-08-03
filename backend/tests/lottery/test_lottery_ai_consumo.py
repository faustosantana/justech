"""Unit tests — Lottery AI usage tokens + cost estimates + period bounds."""

from __future__ import annotations

from datetime import datetime, timezone

from app.lottery.ai.usage import (
    estimate_cost_usd,
    merge_usage,
    normalize_usage_tokens,
)
from app.services.lottery_ai_consumption_service import resolve_period_bounds


def test_normalize_usage_openai_style():
    p, c, t = normalize_usage_tokens(
        {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140}
    )
    assert (p, c, t) == (100, 40, 140)


def test_normalize_usage_huawei_aliases():
    p, c, t = normalize_usage_tokens({"input_tokens": 12, "output_tokens": 8})
    assert (p, c, t) == (12, 8, 20)


def test_merge_usage_sums_calls():
    merged = merge_usage(
        {"prompt_tokens": 10, "completion_tokens": 5},
        {"input_tokens": 20, "output_tokens": 7},
    )
    assert merged["prompt_tokens"] == 30
    assert merged["completion_tokens"] == 12
    assert merged["total_tokens"] == 42


def test_estimate_cost_differs_by_model():
    flash = estimate_cost_usd(
        prompt_tokens=1000, completion_tokens=1000, model="deepseek-v4-flash", provider="huawei"
    )
    gpt5 = estimate_cost_usd(
        prompt_tokens=1000, completion_tokens=1000, model="gpt-5", provider="openai"
    )
    assert flash > 0
    assert gpt5 > flash


def test_resolve_period_today():
    since, until, label = resolve_period_bounds("today")
    assert label == "today"
    assert since.tzinfo is not None
    assert until >= since
    assert since.hour == 0


def test_resolve_period_custom_range():
    since, until, label = resolve_period_bounds(
        "range", date_from="2026-07-01", date_to="2026-07-15"
    )
    assert label == "range"
    assert since == datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert until.day == 15
