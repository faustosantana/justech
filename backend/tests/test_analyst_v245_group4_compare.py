"""v2.4.5 Grupo 4 — D.2–D.4 compare 54/94 with same filters.

Root causes:
1. ToolOrchestrator collapsed active_numbers to the last compare tool's
   single number (94), so year/position follow-ups clarified instead of
   re-comparing.
2. Unscoped compare pinned occurrences to sticky Nacional while
   compare_across used multiple lotteries (mismatched filters).
"""

from __future__ import annotations

from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.historical_comparator import compare_numbers_steps
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES


def _compare_state() -> ConversationState:
    return ConversationState(
        active_numbers=["54", "94"],
        active_pair=["54", "94"],
        active_filters={"compare_active": True},
        last_intent="compare_numbers",
    )


def test_d2_year_followup_replays_compare_with_both_subjects():
    st = _compare_state()
    q = "¿Y solo en 2026?"
    res = IntentResolver.resolve(q, st)
    rq = QuestionClassifier.classify(q, st, res)
    assert rq is not None
    assert rq.kind == "compare_numbers"
    assert rq.params["numbers"][:2] == ["54", "94"]
    assert int(rq.params.get("year_filter") or res.get("year_filter") or 0) == 2026
    steps, meta = DynamicResearchPlanner.build(rq, st)
    assert meta.get("subjects") == ["54", "94"]
    # Same date window on every primary step
    for s in steps:
        if s.purpose and s.purpose.startswith("compare_") and s.params.get("number"):
            assert s.params.get("from_date") == "2026-01-01"
            assert s.params.get("to_date") == "2026-12-31"


def test_d3_position_followup_same_filters_both_subjects():
    st = _compare_state()
    st.active_filters = {"compare_active": True, "year": 2026}
    q = "Ahora solo en primera posición."
    res = IntentResolver.resolve(q, st)
    rq = QuestionClassifier.classify(q, st, res)
    assert rq is not None
    assert rq.kind == "compare_numbers"
    assert rq.params["numbers"][:2] == ["54", "94"]
    steps, _meta = DynamicResearchPlanner.build(rq, st)
    pos_steps = [s for s in steps if s.params.get("number") in {"54", "94"}]
    assert pos_steps
    for s in pos_steps:
        if s.purpose and (
            "last" in (s.purpose or "")
            or "lotteries" in (s.purpose or "")
            or "occurrences" in (s.purpose or "")
        ):
            assert s.params.get("position") == 1


def test_d4_which_more_recent_keeps_pair():
    st = _compare_state()
    q = "¿Cuál de los dos salió más recientemente?"
    res = IntentResolver.resolve(q, st)
    rq = QuestionClassifier.classify(q, st, res)
    assert rq is not None
    assert rq.kind == "compare_numbers"
    assert rq.params["numbers"][:2] == ["54", "94"]


def test_d1_unscoped_compare_same_lottery_scope_for_a_and_b():
    st = ConversationState(active_lotteries=["Nacional", "Leidsa"])
    rq = QuestionClassifier.classify(
        "Compara el 54 con el 94 en todo el histórico.",
        st,
        {"numbers": ["54", "94"]},
    )
    steps, meta = DynamicResearchPlanner.build(rq, st)
    assert set(DEFAULT_ALL_HISTORY_LOTTERIES).issubset(set(meta.get("lotteries") or []))
    a_last = next(s for s in steps if s.purpose == "compare_a_last")
    b_last = next(s for s in steps if s.purpose == "compare_b_last")
    assert a_last.params.get("lotteries") == b_last.params.get("lotteries")
    assert "Gana Más" in (a_last.params.get("lotteries") or [])
    # No single-lottery occurrence step that would diverge from cross-lottery scope
    assert not any(s.purpose == "compare_a_occurrences" for s in steps)


def test_compare_numbers_steps_year_and_position_aligned():
    steps = compare_numbers_steps(
        a="54", b="94", lotteries=list(DEFAULT_ALL_HISTORY_LOTTERIES), year=2026, position=1
    )
    for s in steps:
        if s.params.get("number") in {"54", "94"}:
            assert s.params.get("from_date") == "2026-01-01"
            assert s.params.get("to_date") == "2026-12-31"
            if "last" in (s.purpose or "") or "lotteries" in (s.purpose or ""):
                assert s.params.get("position") == 1


def test_d2_research_engine_plan_survives_query_clarify_slot():
    """understand may mark material slot 'query'; Research Engine still plans compare."""
    from app.lottery.ai.analyst.config import AnalystRuntimeConfig
    from app.lottery.ai.analyst.research_planner import ResearchPlanner
    from app.lottery.ai.conversation_state import UnderstandingResult

    st = _compare_state()
    q = "¿Y solo en 2026?"
    res = IntentResolver.resolve(q, st)
    und = UnderstandingResult(
        intent="clarification_response",
        needs_clarification=True,
        missing_slots=["query"],
        numbers=["54", "94"],
        tool=None,
    )
    plan = ResearchPlanner.plan(
        message=q,
        understanding=und,
        state=st,
        config=AnalystRuntimeConfig(),
        resolution=res,
    )
    assert plan.is_research is True
    assert plan.steps
    assert any(
        s.purpose and s.purpose.startswith("compare_") for s in plan.steps
    )
