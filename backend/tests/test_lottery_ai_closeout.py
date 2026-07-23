"""Lottery AI closeout unit tests — no DB / no network."""

from __future__ import annotations

from datetime import date

from app.lottery.ai.alert_notifications import (
    CHANNELS,
    clear_throttle_cache,
    default_channels_config,
    notify_alert,
)
from app.lottery.ai.alert_thresholds import DEFAULT_ALERT_THRESHOLDS, merge_thresholds
from app.lottery.ai.benchmark import (
    _build_cases,
    build_benchmark_300,
    compare_v2_v3,
    run_benchmark,
)
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.tone_templates import (
    CRITICAL_SAFETY_KEYS,
    TONE_TEMPLATES,
    apply_tone_to_prompt,
    sanitize_tone_overrides,
)


def test_tone_templates_all_six_and_safety():
    assert set(TONE_TEMPLATES) >= {
        "conservador",
        "conversacional",
        "analitico",
        "ejecutivo",
        "profundo",
        "estricto",
    }
    dirty = sanitize_tone_overrides(
        {
            "tone": "x",
            "strict_domain": False,
            "no_prediction": False,
            "domain_restriction": False,
        }
    )
    for key in CRITICAL_SAFETY_KEYS:
        assert key not in dirty
    assert dirty.get("tone") == "x"

    out = apply_tone_to_prompt("BASE", "estricto")
    assert out.startswith("BASE")
    assert "seguridad" in out.lower() or "dominio estricto" in out.lower()
    assert "TONO ESTRICTO" in out


def test_alert_thresholds_defaults_load():
    assert DEFAULT_ALERT_THRESHOLDS["max_p0"] == 0
    assert DEFAULT_ALERT_THRESHOLDS["max_p1"] == 0
    assert "fallback_rate_warning" in DEFAULT_ALERT_THRESHOLDS
    merged = merge_thresholds({"error_rate_warning": 0.33})
    assert merged["error_rate_warning"] == 0.33
    assert merged["benchmark_min_score"] == DEFAULT_ALERT_THRESHOLDS["benchmark_min_score"]


def test_benchmark_300_and_v2_v3_gate():
    assert len(build_benchmark_300()) >= 300
    assert len(_build_cases()) >= 300
    cmp = compare_v2_v3(limit=40)
    gate = cmp["v3_activation_gate"]
    assert "activate_v3" in gate
    if cmp["v3"]["p0"] > 0 or cmp["v3"]["p1"] > 0:
        assert gate["activate_v3"] is False


def test_conversation_state_from_store_draw_date_and_lotteries():
    state = ConversationState.from_store(
        {
            "active_lotteries": ["Real", "Leidsa"],
            "active_numbers": ["24"],
            "last_occurrences": {
                "Real": {"number": "24", "draw_date": "2026-06-15", "lottery": "Real"},
            },
        }
    )
    assert state.active_lotteries == ["Real", "Leidsa"]
    occ = state.last_occurrences["Real"]
    assert occ.date == "2026-06-15"
    assert not hasattr(occ, "draw_date") or getattr(occ, "draw_date", None) is None
    assert state.occurrence_date_for("Real") == date(2026, 6, 15)

    legacy = ConversationState.from_store({"last_lottery": "Nacional", "base_date": "2026-01-02"})
    assert legacy.active_lotteries == ["Nacional"]
    assert legacy.date_context == date(2026, 1, 2)


def test_alert_notifications_disabled_by_default_skips_send():
    clear_throttle_cache()
    cfg = default_channels_config()
    for ch in CHANNELS:
        assert cfg[ch].get("enabled") is False

    result = notify_alert(
        {"code": "TEST_ALERT", "fingerprint": "fp-test-1", "severity": "high", "message": "x"},
        channels_config=cfg,
    )
    assert result["sent"] == []
    assert set(result["skipped"]) == set(CHANNELS)
    assert result["reasons"]
    assert all("disabled" in r or "no_" in r for r in result["reasons"])

    # Explicit enable without recipients still skips (no external send)
    forced = notify_alert(
        {"code": "TEST_ALERT", "fingerprint": "fp-test-2", "message": "y"},
        channels_config={
            "throttle_seconds": 60,
            "email": {"enabled": True, "recipients": []},
            "webhook": {"enabled": False},
            "slack": {"enabled": False},
            "teams": {"enabled": False},
            "jaios_internal": {"enabled": False},
        },
    )
    assert "email" not in forced["sent"]
    assert "email_no_recipients" in forced["reasons"]


def test_publish_gate_blocked_when_p0():
    report = run_benchmark(prompt_version="v2", limit=80)
    assert "publish_blocked" in report
    assert report["publish_blocked"] == bool(report["p0"] or report["p1"])
    if report["p0"] > 0:
        assert report["publish_blocked"] is True
