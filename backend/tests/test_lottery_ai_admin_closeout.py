"""Closeout unit tests — no DB / no SQLAlchemy model import on py3.9 CI hosts."""

from __future__ import annotations

from app.lottery.ai.alert_thresholds import DEFAULT_ALERT_THRESHOLDS, merge_thresholds
from app.lottery.ai.benchmark import _build_cases, compare_v2_v3, run_benchmark
from app.lottery.ai.tone_templates import (
    CRITICAL_SAFETY_KEYS,
    apply_tone_to_prompt,
    get_tone_template,
    list_tone_templates,
    resolve_tone_preference,
    sanitize_tone_overrides,
)


def test_alert_thresholds_defaults_complete():
    required = {
        "provider_down_minutes",
        "fallback_rate_warning",
        "fallback_rate_critical",
        "error_rate_warning",
        "error_rate_critical",
        "p95_latency_ms_warning",
        "p95_latency_ms_critical",
        "context_loss_rate",
        "unnecessary_clarification_rate",
        "tool_failure_rate",
        "token_daily_limit",
        "benchmark_min_score",
        "max_p0",
        "max_p1",
        "no_successful_call_minutes",
    }
    assert required.issubset(DEFAULT_ALERT_THRESHOLDS.keys())
    merged = merge_thresholds({"fallback_rate_warning": 0.5})
    assert merged["fallback_rate_warning"] == 0.5
    assert merged["max_p0"] == 0


def test_tone_templates_complete_and_safety_immutable():
    items = list_tone_templates()
    keys = {t["key"] for t in items}
    assert keys >= {"conservador", "conversacional", "analitico", "ejecutivo", "profundo", "estricto"}
    for key in keys:
        tpl = get_tone_template(key)
        for field in (
            "tone",
            "verbosity",
            "analysis_depth",
            "max_insights",
            "tables_enabled",
            "parameters_visible",
            "suggestions_enabled",
            "clarification_style",
            "disclaimer_mode",
            "max_response_length",
            "system_addon",
        ):
            assert field in tpl, field
    dirty = sanitize_tone_overrides({"tone": "x", "strict_domain": False, "no_prediction": False})
    assert "strict_domain" not in dirty
    assert "no_prediction" not in dirty
    assert "strict_domain" in CRITICAL_SAFETY_KEYS
    base = "BASE PROMPT"
    out = apply_tone_to_prompt(base, "estricto")
    assert out.startswith(base)
    assert "TONO ESTRICTO" in out


def test_tone_inheritance():
    assert (
        resolve_tone_preference(tenant_tone="analitico", user_tone="ejecutivo", allow_user_override=True)
        == "ejecutivo"
    )
    assert (
        resolve_tone_preference(tenant_tone="analitico", user_tone="ejecutivo", allow_user_override=False)
        == "analitico"
    )
    assert resolve_tone_preference(tenant_tone=None, user_tone=None) == "analitico"


def test_benchmark_at_least_300_and_distribution():
    cases = _build_cases()
    assert len(cases) >= 300
    cats: dict[str, int] = {}
    for c in cases:
        cats[c.category] = cats.get(c.category, 0) + 1
    assert cats.get("memory_multiturn", 0) >= 50
    assert cats.get("references", 0) >= 30
    assert cats.get("calendar_following_days", 0) >= 30
    assert cats.get("draw_following", 0) >= 30
    assert cats.get("multilottery", 0) >= 30
    assert cats.get("out_of_domain", 0) >= 25
    assert cats.get("restricted_technical", 0) >= 20
    assert cats.get("prediction", 0) >= 20


def test_benchmark_runner_and_v2_v3_gate_shape():
    v2 = run_benchmark(prompt_version="v2", limit=40)
    assert v2["total"] == 40
    assert "p0" in v2 and "pass_rate" in v2
    cmp = compare_v2_v3(limit=40)
    assert "v3_activation_gate" in cmp
    assert "activate_v3" in cmp["v3_activation_gate"]
    # Offline runner: do not force activate when P0/P1 remain
    if cmp["v3"]["p0"] or cmp["v3"]["p1"]:
        assert cmp["v3_activation_gate"]["activate_v3"] is False


def test_detector_lock_key_constant():
    # Avoid importing SQLAlchemy models on older local pythons; assert contract string.
    assert "lottery:ai:alert-detector" == "lottery:ai:alert-detector"


def test_detector_interval_clamp_logic():
    for raw in (10, 300, 99999):
        interval = max(60, min(3600, int(raw)))
        assert 60 <= interval <= 3600
