"""Fase X — NLP Intent & Context Stability tests (v2.3.1)."""

from __future__ import annotations

from app.lottery.ai.nlp_battery import evaluate_battery
from app.lottery.ai.nlp_stability import classify_nlp, extract_entities
from app.lottery.ai.understanding import understand
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt, get_motor_prompt
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)


def test_motor_intact_phase_x():
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


def test_engines_intact_phase_x():
    from app.lottery.ai.analyst import (
        get_discovery_engine,
        get_knowledge_engine,
        get_research_engine,
    )

    assert get_motor_prompt().version == "v5"
    assert get_active_prompt().version == "v6"
    re = get_research_engine()
    assert re.ENABLED is True and re.VERSION == "2.0"
    de = get_discovery_engine()
    assert de.ENABLED is True
    ke = get_knowledge_engine()
    assert ke.version == "2.3.0"


def test_greeting_no_tools():
    for g in ("Hola", "Buenos días", "¿Cómo estás?", "Saludos"):
        nlp = classify_nlp(g)
        assert nlp.intent == "GREETING"
        assert nlp.run_tools is False
        r = resolve_intent(g, LotterySessionContext())
        assert r.kind == "chat"
        u, st = understand(g, ConversationState(pending_slots=["lottery"], pending_intent="x"))
        assert u.intent == "greeting"
        assert st.pending_slots == []


def test_general_chat_no_tools():
    for g in ("Gracias", "Perfecto", "Excelente"):
        nlp = classify_nlp(g)
        assert nlp.intent == "GENERAL_CHAT"
        assert nlp.run_tools is False


def test_count_54_no_lottery_clarify():
    text = "¿Cuántas veces salió el 54?"
    nlp = classify_nlp(text)
    assert nlp.intent == "COUNT"
    assert nlp.needs_clarification is False
    r = resolve_intent(text, LotterySessionContext())
    assert r.kind == "tool"
    assert r.kind != "clarify"
    msg = (r.clarify_message or "").lower()
    assert "fecha" not in msg
    assert "loter" not in msg or r.kind == "tool"
    u, _ = understand(text, ConversationState())
    assert not u.needs_clarification or "lottery" not in (u.missing_slots or [])


def test_analyze_completamente_not_count():
    text = "Analiza completamente el 54"
    nlp = classify_nlp(text)
    assert nlp.intent == "ANALYZE"
    r = resolve_intent(text, LotterySessionContext())
    assert r.kind == "tool"
    assert r.tool is not None
    assert "complete_analysis" in r.tool.value or r.structured_type == "lottery_complete_analysis"


def test_estudio_and_grupo_analyze():
    for t in ("Haz un estudio del 35", "Investiga el grupo del 18"):
        assert classify_nlp(t).intent == "ANALYZE"


def test_cuando_salio_asks_number():
    nlp = classify_nlp("¿Cuándo salió?")
    assert nlp.intent == "DATE"
    assert nlp.needs_clarification is True
    assert "number" in nlp.missing_slots


def test_follow_up_explicit_only():
    nlp = classify_nlp("¿Y en Nacional?", has_active_context=True)
    assert nlp.intent in {"FOLLOW_UP", "LOTTERY"}
    assert nlp.inherit_context is True
    nlp2 = classify_nlp("¿Cuántas veces salió el 54?", has_active_context=True)
    assert nlp2.intent == "COUNT"
    assert nlp2.inherit_context is False


def test_entity_extraction():
    e = extract_entities("Compara 54 vs 94 en Nacional en 2026 en primera")
    assert "54" in e["numbers"] and "94" in e["numbers"]
    assert e["years"] == [2026]
    assert e["lotteries"]
    assert "primera" in e["positions"]


def test_battery_metrics_ge_98():
    m = evaluate_battery()
    assert m["battery_size"] >= 500
    assert m["accuracy_classification"] >= 98.0, m
    assert m["accuracy_entities"] >= 95.0, m
    assert m["pass_threshold_98"] is True
