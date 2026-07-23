"""Lottery IA 4.2 — memory, references, domain gate unit tests."""

from __future__ import annotations

from datetime import date

from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.domain_classifier import classify_domain
from app.lottery.ai.reference_resolver import derive_per_lottery_base_dates, resolve_references
from app.lottery.ai.understanding import understand


def test_remember_occurrence_roundtrip():
    state = ConversationState()
    state.remember_occurrence(
        lottery="Real",
        number="24",
        draw_date=date(2026, 6, 15),
        position=3,
    )
    state.remember_occurrence(
        lottery="Leidsa",
        number="24",
        draw_date="2026-07-04",
        position="1ro",
    )
    dumped = state.to_store()
    restored = ConversationState.from_store(dumped)
    assert restored.active_numbers == ["24"]
    assert set(restored.active_lotteries) == {"Real", "Leidsa"}
    assert restored.last_occurrences["Real"].date == "2026-06-15"
    assert restored.date_context == date(2026, 7, 4)


def test_reference_esas_loterias_and_despues():
    state = ConversationState(
        active_lotteries=["Real", "Leidsa"],
        active_numbers=["24"],
    )
    state.remember_occurrence(
        lottery="Real", number="24", draw_date="2026-06-15"
    )
    state.remember_occurrence(
        lottery="Leidsa", number="24", draw_date="2026-07-04"
    )
    refs = resolve_references(
        "¿Cuáles números salieron los 7 días después en esas loterías?",
        state,
    )
    assert refs["used_pronoun_lotteries"] is True
    assert refs["lotteries"] == ["Real", "Leidsa"]
    assert refs["numbers"] == ["24"]
    assert refs["post_window"]["unit"] == "days"
    assert refs["post_window"]["count"] == 7
    per = derive_per_lottery_base_dates(state, refs["lotteries"], "24")
    assert per["Real"] == date(2026, 6, 15)
    assert per["Leidsa"] == date(2026, 7, 4)


def test_understand_post_occurrence_does_not_clarify():
    state = ConversationState(
        active_lotteries=["Real", "Leidsa"],
        active_numbers=["24"],
        last_intent="last_occurrence",
    )
    state.remember_occurrence(
        lottery="Real", number="24", draw_date="2026-06-15"
    )
    state.remember_occurrence(
        lottery="Leidsa", number="24", draw_date="2026-07-04"
    )
    result, new_state = understand(
        "¿Cuáles números salieron los siete días después en esas loterías?",
        state,
    )
    assert result.needs_clarification is False
    assert result.intent == "post_occurrence_window"
    assert result.tool == "lottery_analyze_post_occurrence_window"
    assert "Real" in result.params.get("per_lottery_dates", {})
    assert "Leidsa" in result.params.get("per_lottery_dates", {})
    assert new_state.calendar_window == 7


def test_domain_out_of_scope_and_restricted():
    d1 = classify_domain("¿Cuál es la capital de Francia?")
    assert d1.classification == "out_of_domain"
    assert d1.refuse_message
    d2 = classify_domain("¿Qué base de datos usan?")
    assert d2.classification == "restricted_technical"
    d3 = classify_domain("¿Qué número va a salir mañana?")
    assert d3.classification == "prediction_request"
    d4 = classify_domain("¿Cuántos sorteos hay de Real?")
    assert d4.classification in {"lottery_domain", "lottery_operational"}


def test_understand_out_of_domain_refuses():
    state = ConversationState()
    result, _ = understand("¿Cuál es la capital de Francia?", state)
    assert result.intent == "out_of_domain"
    assert result.params.get("refuse_message")


def test_swap_number_keeps_lotteries():
    state = ConversationState(
        active_lotteries=["Real", "Leidsa"],
        active_numbers=["24"],
        last_intent="last_occurrence",
    )
    result, new_state = understand("Ahora hazlo con el 57", state)
    assert result.intent == "last_occurrence"
    assert result.numbers == ["57"]
    assert "Real" in (result.lotteries or new_state.active_lotteries)
