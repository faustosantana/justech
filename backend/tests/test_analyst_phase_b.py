"""Fase B — Research Engine profesional (no motor changes)."""

from __future__ import annotations

from app.lottery.ai.analyst import (
    EvidenceEngine,
    QuestionClassifier,
    ResearchEngine,
    ResearchPlanner,
    format_research_response,
    get_discovery_engine,
    get_research_engine,
    load_analyst_config_from_payload,
)
from app.lottery.ai.analyst.case_search import case_search_steps, describe_case_criteria
from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.historical_comparator import compare_numbers_steps
from app.lottery.ai.analyst.question_classifier import ResearchQuestion
from app.lottery.ai.analyst.research_cache import ResearchCache
from app.lottery.ai.analyst.temporal_analysis import temporal_after_steps
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)


def test_motor_intact_phase_b():
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


def test_prompt_maestro_intact_phase_b():
    p = get_active_prompt()
    assert p.version == "v5"
    assert "PROMPT MAESTRO OFICIAL" in p.body


def test_research_engine_enabled_and_plans_after_54():
    eng = get_research_engine()
    assert isinstance(eng, ResearchEngine)
    assert eng.ENABLED is True
    state = ConversationState(active_numbers=["54"])
    cfg = load_analyst_config_from_payload(
        {"research": {"mode": "deep", "max_tools_per_research": 20, "max_research_steps": 30}}
    )
    understanding = UnderstandingResult(
        intent="follow_up",
        numbers=["54"],
        tool="lottery_get_number_occurrences",
        params={"number": "54"},
    )
    plan = eng.build_plan(
        message="¿Qué suele pasar después del 54?",
        understanding=understanding,
        state=state,
        config=cfg,
        resolution={"inherit_active_number": True, "numbers": ["54"]},
    )
    assert plan is not None
    assert plan.is_research is True
    assert plan.question_kind == "what_usually_happens_after"
    assert len(plan.steps) >= 4
    purposes = [s.purpose for s in plan.steps]
    assert any(str(p).startswith("d_plus_") for p in purposes)


def test_dynamic_compare_54_vs_94():
    state = ConversationState(active_numbers=["54", "94"], active_lotteries=["nacional"])
    q = QuestionClassifier.classify(
        "Compárame el comportamiento histórico del 54 y el 94.",
        state,
        {},
    )
    assert q is not None
    assert q.kind == "compare_numbers"
    steps, meta = DynamicResearchPlanner.build(q, state, max_steps=40)
    assert len(steps) >= 8
    assert meta.get("dimension") == "numbers"
    tools = {s.tool for s in steps}
    assert "lottery_get_number_occurrences" in tools


def test_case_search_and_temporal_helpers():
    steps = case_search_steps(observed="54", confirmer="14", candidate=54, mode="all")
    assert any(s.purpose == "cases_equivalent" for s in steps)
    assert describe_case_criteria("equivalent")
    tsteps = temporal_after_steps(number="54", lottery="nacional", windows=[1, 3, 7, 15])
    assert any(s.purpose == "d_plus_15" for s in tsteps)
    csteps = compare_numbers_steps(a="54", b="94", lottery="nacional")
    assert len(csteps) >= 6


def test_evidence_confidence_qualitative():
    pkg = EvidenceEngine.assemble(
        kind="compare_numbers",
        tool_trace=[
            {"tool": "lottery_get_number_occurrences", "status": "success"},
            {"tool": "lottery_get_following_days", "status": "success"},
            {"tool": "lottery_calculate_frequencies", "status": "success"},
            {"tool": "lottery_compare_number_across_lotteries", "status": "success"},
        ],
        evidence_bundle=[
            {"purpose": "compare_a_occurrences", "tool": "x", "summary": {"count": 25}},
            {"purpose": "compare_b_occurrences", "tool": "y", "summary": {"count": 18}},
        ],
        context={"numbers": ["54", "94"], "year_filter": 2026},
        case_criteria=[{"code": "equivalent", "criterion": "exact match"}],
    )
    assert pkg.evidence_level in {"Alta", "Media", "Baja"}
    assert pkg.case_count >= 25
    assert "%" not in str(pkg.to_dict())
    text = format_research_response(
        "El 54 muestra más apariciones consultadas que el 94 en el recorte.",
        research={"question_kind": "compare_numbers", "confidence": pkg.evidence_level},
        evidence_package=pkg.to_dict(),
    )
    assert "Resumen Ejecutivo" in text
    assert "Evidencias" in text
    assert "Limitaciones" in text
    assert "Sugerencias" in text


def test_research_cache_dedupes():
    cache = ResearchCache(ttl_seconds=60)
    cache.set("lottery_get_number_occurrences", {"number": "54"}, {"ok": True})
    hit = cache.get("lottery_get_number_occurrences", {"number": "54"})
    assert hit == {"ok": True}
    assert cache.get("lottery_get_number_occurrences", {"number": "94"}) is None


def test_discovery_engine_still_disabled():
    disc = get_discovery_engine()
    assert disc.ENABLED is False


def test_planner_prefers_research_engine():
    state = ConversationState(active_numbers=["54"], active_lotteries=["nacional", "loteka"])
    understanding = UnderstandingResult(
        intent="follow_up",
        numbers=["54"],
        tool="lottery_get_number_occurrences",
        params={"number": "54"},
    )
    cfg = load_analyst_config_from_payload({"research": {"mode": "auto", "max_tools_per_research": 16}})
    plan = ResearchPlanner.plan(
        message="¿Cuál lotería confirma primero?",
        understanding=understanding,
        state=state,
        config=cfg,
        resolution={"inherit_active_number": True},
    )
    assert plan.is_research is True
    assert plan.rationale.startswith("research_engine:")


def test_chained_context_research_kinds():
    state = ConversationState(active_numbers=["54"], active_lotteries=["nacional"])
    turns = [
        ("¿Y solamente Nacional?", "filtered_follow_up"),
        ("¿Qué ocurrió después?", "what_usually_happens_after"),
        ("Compáralo con el 94.", "compare_numbers"),
        ("Muéstrame solamente los casos equivalentes.", "equivalents_only"),
    ]
    for text, expect_kind in turns:
        q = QuestionClassifier.classify(text, state, {"inherit_active_number": True, "numbers": ["54"]})
        # compare / equivalents / after should classify; filter may be filtered_follow_up or lottery compare
        assert q is not None, text
        if expect_kind == "filtered_follow_up":
            assert q.kind in {"filtered_follow_up", "compare_lotteries", "open_investigation", "frequency_behavior"}
        else:
            assert q.kind == expect_kind or q.kind in RESEARCH_FALLBACKS.get(expect_kind, set()), (
                text,
                q.kind,
            )


RESEARCH_FALLBACKS = {
    "what_usually_happens_after": {"temporal_after", "temporal_windows", "open_investigation"},
    "compare_numbers": {"filtered_follow_up"},
    "equivalents_only": {"case_search"},
}
