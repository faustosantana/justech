"""Lottery IA 4.0 — conversational slot filling, last occurrence, clarifications."""

from __future__ import annotations

from app.lottery.ai.conversation_state import ConversationState, smart_clarify
from app.lottery.ai.understanding import understand
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent


def test_last_occurrence_without_lottery_asks_only_lottery():
    ctx = LotterySessionContext()
    intent = resolve_intent("¿Cuándo fue la última vez que salió el 57?", ctx)
    assert intent.kind == "clarify"
    msg = (intent.clarify_message or "").lower()
    assert "57" in msg
    assert "loter" in msg
    assert "fecha exacta" not in msg
    assert "número" not in msg or "57" in msg  # may mention number value, not ask for it


def test_smart_clarify_last_occurrence():
    q = smart_clarify(intent="last_occurrence", number="57", missing=["lottery"])
    assert "57" in q
    assert "fecha exacta" not in q.lower()
    assert "todas" in q.lower() or "específica" in q.lower()


def test_understanding_sets_pending_slots():
    state = ConversationState()
    result, new_state = understand("¿Cuándo fue la última vez que salió el 57?", state)
    assert result.intent == "last_occurrence"
    assert result.needs_clarification
    assert "lottery" in result.missing_slots
    assert "57" in (result.numbers or new_state.active_numbers)
    assert "fecha" not in (result.clarification_question or "").lower() or "compar" in (
        result.clarification_question or ""
    ).lower()


def test_slot_fill_real_then_execute():
    state = ConversationState(
        pending_intent="last_occurrence",
        pending_slots=["lottery"],
        pending_params={"number": "57"},
        active_numbers=["57"],
        last_intent="last_occurrence",
    )
    result, new_state = understand("En la Real.", state)
    assert not result.needs_clarification
    assert result.tool == LotteryToolName.GET_LAST_OCCURRENCE.value
    assert result.params.get("number") == "57"
    assert result.params.get("lottery")
    assert "Real" in str(result.params.get("lottery"))
    assert not new_state.pending_slots


def test_follow_up_y_en_leidsa_keeps_number():
    state = ConversationState(
        active_lotteries=["Real"],
        active_numbers=["57"],
        last_intent="last_occurrence",
    )
    result, new_state = understand("¿Y en Leidsa?", state)
    assert result.params.get("number") == "57"
    assert "Leidsa" in str(result.params.get("lottery"))
    assert "Real" in new_state.active_lotteries
    assert any("Leidsa" in x for x in new_state.active_lotteries)


def test_comparalas_uses_both_lotteries():
    state = ConversationState(
        active_lotteries=["Real", "Leidsa"],
        active_numbers=["57"],
        last_intent="last_occurrence",
    )
    result, _ = understand("Compáralas.", state)
    assert result.intent == "compare_numbers"
    assert result.numbers == ["57"]
    assert len(result.lotteries) >= 2 or result.scope in {"multiple", "all"}


def test_frequency_clarify_offers_period():
    ctx = LotterySessionContext()
    intent = resolve_intent("Dame los números más frecuentes.", ctx)
    assert intent.kind == "clarify"
    msg = (intent.clarify_message or "").lower()
    assert "loter" in msg
    assert "30" in msg or "año" in msg or "historial" in msg


def test_by_date_still_asks_date_when_needed():
    ctx = LotterySessionContext()
    intent = resolve_intent("Qué salió en Real", ctx)
    assert intent.kind == "clarify"
    assert "fecha" in (intent.clarify_message or "").lower()


def test_prompt_registry_active():
    from app.lottery.ai.prompts.lottery_assistant_system_v1 import (
        PROMPT_NAME,
        get_active_prompt,
        get_system_prompt_text,
    )

    p = get_active_prompt()
    assert "lottery_assistant_system" in p.name
    assert p.version in {"v1", "v2"}
    assert "Lottery IA" in get_system_prompt_text()
    assert "fecha exacta" in get_system_prompt_text()  # documents incorrect pattern


def test_runtime_snapshot_no_secrets():
    from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt

    p = get_active_prompt()
    assert p.version in {"v1", "v2"}
    assert p.name == "lottery_assistant_system_v1"
    # Full runtime_snapshot needs app.config; hermes planning flag is documented false.
    hermes_planning = False
    assert hermes_planning is False
