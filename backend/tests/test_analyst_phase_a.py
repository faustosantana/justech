"""Fase A — Analista IA professional layer (no motor changes)."""

from __future__ import annotations

from app.lottery.ai.analyst import (
    AnalystGuardrails,
    ConversationBrain,
    IntentResolver,
    ResearchPlanner,
    format_analyst_response,
    load_analyst_config_from_payload,
)
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)


def test_prompt_maestro_v5_untouched():
    p = get_active_prompt()
    assert p.version == "v5"
    assert "PROMPT MAESTRO OFICIAL" in p.body


def test_motor_cases_unchanged():
    cases = [([35, 14], 54), ([39, 58], 94)]
    for nums, expect in cases:
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


def test_intent_resolver_inherits_active_number():
    state = ConversationState(active_numbers=["54"])
    res = IntentResolver.resolve("¿En cuáles loterías?", state)
    assert res["inherit_active_number"] is True
    assert res["numbers"] == ["54"]
    assert res["follow_up_kind"] == "lotteries"


def test_conversation_brain_remembers_pair():
    state = ConversationState()
    brain = ConversationBrain(state)
    understanding = UnderstandingResult(
        intent="follow_up",
        numbers=["35", "14"],
        tool="lottery_run_complete_analysis",
        params={},
    )
    state = brain.apply_resolution(understanding=understanding, resolution={"numbers": ["35", "14"]})
    assert state.active_pair == ["35", "14"]
    state = brain.remember_analysis(
        {"observed": 35, "confirmer": 14, "primary": 54, "type": "complete_analysis"}
    )
    assert state.current_primary_candidate == 54
    assert brain.should_skip_number_clarify()


def test_research_planner_builds_deep_plan_for_pair_history():
    state = ConversationState(active_numbers=["35", "14"])
    understanding = UnderstandingResult(
        intent="numeric_relations",
        numbers=["35", "14"],
        tool="lottery_run_complete_analysis",
        params={"observed_number": 35, "confirmer": 14},
    )
    cfg = load_analyst_config_from_payload({"research": {"mode": "auto"}})
    plan = ResearchPlanner.plan(
        message="¿Qué pasó las últimas veces que salieron el 35 y el 14?",
        understanding=understanding,
        state=state,
        config=cfg,
        resolution={},
    )
    assert plan.is_research is True
    assert plan.user_visible_status
    tools = {s.tool for s in plan.steps}
    assert (
        "lottery_run_complete_analysis" in tools
        or "lottery_get_number_occurrences" in tools
        or "lottery_historical_relation_conditions" in tools
        or "lottery_get_following_days" in tools
    )


def test_guardrails_block_non_lottery_tools_and_sanitize():
    g = AnalystGuardrails()
    assert g.allow_tool("lottery_get_last_occurrence") is True
    assert g.allow_tool("sql_drop_table") is False
    assert g.allow_tool("admin_mutate_ranking") is False
    cleaned = g.sanitize_llm_text("El 54 va a salir seguro mañana.")
    assert "va a salir" not in cleaned.lower() or "limitaciones" in cleaned.lower()
    assert g.assert_ranking_unchanged(before_primary=54, after_primary=54)


def test_response_formatter_sections():
    text = format_analyst_response(
        "El 54 es el más fortalecido.",
        facts={"primary": 54, "observed": 35, "confirmer": 14},
        research={"steps_completed": ["complete_analysis_t1_t2"]},
    )
    assert "Conclusión" in text
    assert "Limitaciones" in text
    assert "54" in text
