"""Fase X.1 — Default Research Policy tests (v2.3.2)."""

from __future__ import annotations

from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.nlp_stability import classify_nlp
from app.lottery.ai.research_policy import policy_manifest
from app.lottery.ai.understanding import understand
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)


def test_motor_intact_phase_x1():
    for nums, expect in (([35, 14], 54), ([39, 58], 94)):
        r = run_complete_analysis(
            {
                "numbers": [nums[0]],
                "same_day_confirmers": nums[1:],
                "mode": "socio",
                "derivation_depth": 0,
                "create_signals": False,
            },
            persist=False,
        )
        assert r.primary_signal["number"] == expect


def test_engines_intact_phase_x1():
    from app.lottery.ai.analyst import (
        get_discovery_engine,
        get_knowledge_engine,
        get_research_engine,
    )

    assert get_active_prompt().version == "v5"
    assert get_research_engine().VERSION == "2.0"
    assert get_discovery_engine().ENABLED is True
    assert get_knowledge_engine().version == "2.3.0"


def test_greeting_conversational():
    for g in ("Hola", "¿Cómo estás?", "Buenos días"):
        nlp = classify_nlp(g)
        assert nlp.intent == "GREETING"
        assert nlp.run_tools is False
        assert "investigar" in (nlp.conversational_reply or "").lower() or "hola" in (
            nlp.conversational_reply or ""
        ).lower()
        r = resolve_intent(g, LotterySessionContext())
        assert r.kind == "chat"
        u, _ = understand(g, ConversationState())
        assert u.intent == "greeting"
        assert u.needs_clarification is False


def test_count_54_investigates_immediately():
    text = "¿Cuántas veces salió el 54?"
    r = resolve_intent(text, LotterySessionContext())
    assert r.kind == "tool"
    assert r.kind != "clarify"
    blob = (r.clarify_message or "").lower()
    assert "loter" not in blob
    assert "fecha" not in blob
    u, _ = understand(text, ConversationState())
    assert u.needs_clarification is False or "lottery" not in (u.missing_slots or [])
    assert "date" not in (u.missing_slots or [])


def test_analyze_completamente_no_clarify():
    text = "Analiza completamente el 54"
    r = resolve_intent(text, LotterySessionContext())
    assert r.kind == "tool"
    u, _ = understand(text, ConversationState())
    assert u.needs_clarification is False


def test_compare_with_context():
    ctx = LotterySessionContext(last_numbers=["54"])
    r = resolve_intent("Compáralo con el 94", ctx)
    # Should not clarify lottery/date
    if r.kind == "clarify":
        assert "loter" not in (r.clarify_message or "").lower()
        assert "fecha" not in (r.clarify_message or "").lower()
    state = ConversationState(active_numbers=["54"])
    u, _ = understand("Compáralo con el 94", state)
    assert "lottery" not in (u.missing_slots or [])
    assert "date" not in (u.missing_slots or [])


def test_last_without_number_asks_number_only():
    r = resolve_intent("¿Cuál fue la última?", LotterySessionContext())
    assert r.kind == "clarify"
    assert "número" in (r.clarify_message or "").lower() or "numero" in (r.clarify_message or "").lower()
    assert "loter" not in (r.clarify_message or "").lower()


def test_last_with_context_investigates():
    r = resolve_intent("¿Cuál fue la última?", LotterySessionContext(last_numbers=["54"]))
    assert r.kind == "tool"


def test_policy_manifest():
    m = policy_manifest()
    assert m["version"] in {"2.3.2", "2.4.0"}
    assert m["rules_changed_count"] >= 10
    assert "lottery" in m["non_material_slots"]
    assert "date" in m["non_material_slots"]
