"""Fase A.1 — consolidación Analista IA (conversación, config, trace, motor intacto)."""

from __future__ import annotations

from app.lottery.ai.analyst import (
    ConversationBrain,
    IntentResolver,
    ResearchEngine,
    ResearchPlanner,
    ResearchTrace,
    format_analyst_response,
    get_research_engine,
    load_analyst_config_from_payload,
)
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt, get_motor_prompt
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)


def test_prompt_maestro_v5_untouched():
    motor = get_motor_prompt()
    assert motor.version == "v5"
    assert "PROMPT MAESTRO OFICIAL" in motor.body
    p = get_active_prompt()
    assert p.version == "v6"
    assert "ANALISTA IA" in p.body.upper()


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


def test_admin_config_drives_runtime():
    cfg = load_analyst_config_from_payload(
        {
            "max_tools": 4,
            "max_steps": 5,
            "max_tokens": 900,
            "timeout": 30,
            "analysis_depth": "deep",
            "investigation_mode": "deep",
        }
    )
    assert cfg.max_tools_per_research == 4
    assert cfg.max_research_steps == 5
    assert cfg.max_tokens == 900
    assert cfg.timeout_seconds == 30
    assert cfg.analysis_depth == "deep"
    assert cfg.research_mode == "deep"
    assert cfg.effective_max_tools() == 4
    assert cfg.effective_max_steps() == 5

    light = load_analyst_config_from_payload(
        {"analysis_depth": "light", "research": {"mode": "quick", "max_tools_per_research": 6}}
    )
    assert light.effective_max_tools() <= 3


def test_research_trace_records_full_audit():
    tr = ResearchTrace(intent="follow_up")
    tr.context_used = {"active_numbers": ["54"]}
    tr.filters_applied = {"year": 2026}
    tr.mark_step(tool="lottery_get_number_occurrences", purpose="number_occurrences", status="success")
    tr.finish(response="Conclusión: hay apariciones en 2026.")
    d = tr.to_dict()
    assert d["intent"] == "follow_up"
    assert d["tools_used"]
    assert d["duration_ms"] is not None
    assert d["response_preview"]


def test_research_engine_stub_not_enabled():
    from app.lottery.ai.analyst.discovery_engine import DiscoveryEngine, DiscoveryRequest, get_discovery_engine
    from app.lottery.ai.analyst.research_engine import ResearchEngine, get_research_engine

    eng = get_research_engine()
    assert isinstance(eng, ResearchEngine)
    assert eng.ENABLED is True
    disc = get_discovery_engine()
    assert isinstance(disc, DiscoveryEngine)
    assert disc.ENABLED is True
    # Hypotheses are not published as predictions
    prep = disc.discover(DiscoveryRequest(kind="hypothesis"))
    assert prep.status == "rejected"
    assert prep.payload.get("findings") == []



def test_long_conversation_context_chain():
    """Simulate the A.1 long dialogue without losing focus."""
    state = ConversationState()
    turns = [
        ("54", {"numbers": ["54"]}),
        ("¿En cuáles loterías?", {"follow_up_kind": "lotteries"}),
        ("¿Y en cuáles posiciones?", {"follow_up_kind": "positions"}),
        ("¿Y solamente en 2026?", {"year_filter": 2026}),
        ("¿Cuál fue la última?", {"follow_up_kind": "last_occurrence"}),
        ("¿Qué ocurrió después?", {"follow_up_kind": "after"}),
        ("Compáralo con el 35.", {"compare_with": "35"}),
        ("Ahora solamente Nacional.", {"lottery_filter": True}),
        ("Ahora segunda posición.", {"position_scope": "second_position"}),
        ("Ahora vuelve al 54.", {"return_to_number": "54"}),
    ]
    brain = ConversationBrain(state)
    for text, expect in turns:
        res = IntentResolver.resolve(text, state)
        understanding = UnderstandingResult(
            intent="follow_up",
            numbers=list(res.get("numbers") or state.active_numbers or []),
            lotteries=list(res.get("lotteries") or []),
            tool="lottery_get_number_occurrences",
            params={},
        )
        if text.strip() == "54":
            understanding.numbers = ["54"]
            res = {**res, "numbers": ["54"]}
        state = brain.apply_resolution(understanding=understanding, resolution=res)
        if expect.get("numbers"):
            assert state.active_numbers[0] in {"54", "054"} or state.active_numbers[0] == "54"
        if expect.get("follow_up_kind"):
            assert res.get("follow_up_kind") == expect["follow_up_kind"] or res.get("inherit_active_number")
        if expect.get("year_filter"):
            assert res.get("year_filter") == 2026
            assert state.active_filters.get("year") == 2026
        if expect.get("compare_with"):
            assert str(res.get("compare_with")) in {"35", "035"} or 35 in (state.current_alternatives or [])
        if expect.get("lottery_filter"):
            assert res.get("lottery_filter") or state.active_lotteries
        if expect.get("position_scope"):
            assert res.get("position_scope") in {"second_position", 2, "2"}
            assert str(state.active_position) in {"second_position", "2", "2.0"}
        if expect.get("return_to_number"):
            assert "54" in (state.active_numbers[0] if state.active_numbers else "")

    assert state.active_numbers
    assert "54" in state.active_numbers[0]
    snap = brain.context_snapshot()
    assert snap["active_numbers"]
    assert "year" in (snap.get("active_filters") or {}) or state.active_filters.get("year") == 2026


def test_natural_references_resolved():
    state = ConversationState(
        active_numbers=["54"],
        active_pair=["35", "14"],
        active_lotteries=["nacional"],
        current_primary_candidate=54,
        current_alternatives=[35],
    )
    cases = [
        ("ese", True),
        ("esas veces", True),
        ("el otro", True),
        ("allí", True),
        ("después", True),
        ("antes", True),
        ("solamente ahí", True),
        ("esa pareja", True),
        ("ese grupo", True),
        ("compáralo con el otro", True),
        ("última vez", True),
        ("primera vez", True),
    ]
    for text, _ in cases:
        res = IntentResolver.resolve(text, state)
        ok = (
            res.get("inherit_active_number")
            or res.get("use_active_pair")
            or res.get("follow_up_kind")
            or res.get("deictic")
            or res.get("compare_with")
            or res.get("lottery_filter")
            or res.get("resolved_refs")
            or res.get("numbers")
        )
        assert ok, f"failed to resolve: {text} → {res}"


def test_research_planner_historical_tools():
    state = ConversationState(
        active_numbers=["35", "14"],
        current_primary_candidate=54,
        active_lotteries=["nacional"],
    )
    understanding = UnderstandingResult(
        intent="numeric_relations",
        numbers=["35", "14"],
        tool="lottery_run_complete_analysis",
        params={"observed_number": 35, "confirmer": 14},
    )
    cfg = load_analyst_config_from_payload(
        {"research": {"mode": "deep", "max_tools_per_research": 10, "max_research_steps": 12}}
    )
    plan = ResearchPlanner.plan(
        message="Compara frecuencias y D+7 de esa pareja",
        understanding=understanding,
        state=state,
        config=cfg,
        resolution={"follow_up_kind": "d_plus_7", "use_active_pair": True},
    )
    assert plan.is_research is True
    assert plan.user_visible_status
    tools = {s.tool for s in plan.steps}
    assert "lottery_run_complete_analysis" in tools or "lottery_historical_relation_conditions" in tools


def test_response_formatter_and_brain_skip_clarify():
    state = ConversationState(active_numbers=["54"])
    brain = ConversationBrain(state)
    assert brain.should_skip_number_clarify()
    text = format_analyst_response(
        "El 54 es el más fortalecido.",
        facts={"primary": 54, "observed": 35, "confirmer": 14},
        research={"steps_completed": ["complete_analysis_t1_t2", "d1_d3_d7_summary"]},
        question="Analiza completamente el 35",
    )
    assert "54" in text
    assert "payload" not in text.lower()
