"""v2.4.5 Grupo 1 — A.2 / H.1: última vez del 22 must use full default scope.

Root cause: is_most_recent_request returned sticky active_lotteries[:4]
(Nacional…Leidsa) with lottery_explicit=False, so last_n missed Gana Más
(2026-07-20) and answered Nacional 2026-06-04.
"""

from __future__ import annotations

from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES


Q_LAST_22 = "¿Cuándo fue la última vez que salió el 22?"


def test_a2_most_recent_clears_sticky_truncated_lotteries():
    st = ConversationState(
        active_lotteries=["Nacional", "Nacional Día", "Nacional Noche", "Leidsa"]
    )
    resolution = IntentResolver.resolve(Q_LAST_22, st)
    rq = QuestionClassifier.classify(Q_LAST_22, st, resolution)
    assert rq is not None
    assert rq.kind == "last_times"
    assert rq.params.get("lottery_explicit") is False
    assert rq.params.get("lotteries") in (None, [], ())


def test_a2_planner_unscoped_uses_full_default_including_gana_mas():
    st = ConversationState(
        active_lotteries=["Nacional", "Nacional Día", "Nacional Noche", "Leidsa"]
    )
    # Simulate the pre-fix sticky params that caused A.2
    from app.lottery.ai.analyst.question_classifier import ResearchQuestion

    rq = ResearchQuestion(
        "last_times",
        {
            "numbers": ["22"],
            "lotteries": ["Nacional", "Nacional Día", "Nacional Noche", "Leidsa"],
            "lottery_explicit": False,
        },
        raw_message=Q_LAST_22,
    )
    steps, meta = DynamicResearchPlanner.build(rq, st)
    assert "Gana Más" in (meta.get("lotteries") or [])
    assert set(DEFAULT_ALL_HISTORY_LOTTERIES).issubset(set(meta.get("lotteries") or []))
    primary = next(
        s for s in steps if s.purpose == "last_occurrence_all_lotteries"
    )
    assert primary.params.get("mode") == "last_n"
    assert "Gana Más" in (primary.params.get("lotteries") or [])
    assert set(DEFAULT_ALL_HISTORY_LOTTERIES).issubset(
        set(primary.params.get("lotteries") or [])
    )


def test_a2_end_to_end_classifier_to_planner_includes_gana_mas():
    st = ConversationState(active_lotteries=list(DEFAULT_ALL_HISTORY_LOTTERIES))
    resolution = IntentResolver.resolve(Q_LAST_22, st)
    rq = QuestionClassifier.classify(Q_LAST_22, st, resolution)
    steps, meta = DynamicResearchPlanner.build(rq, st)
    primary = next(
        s for s in steps if s.purpose == "last_occurrence_all_lotteries"
    )
    lots = primary.params.get("lotteries") or []
    assert "Gana Más" in lots
    assert len(lots) >= 7


def test_a2_params_lotteries_slice4_must_not_drive_unscoped_plan():
    """A.2 smoking gun: params.lotteries[:4] dropped Gana Más while
    lottery_explicit=False; planner must ignore that sticky truncation.
    """
    sticky4 = ["Nacional", "New York 10:30", "New York 2:30", "Leidsa"]
    assert "Gana Más" not in sticky4
    st = ConversationState(active_lotteries=list(DEFAULT_ALL_HISTORY_LOTTERIES))
    from app.lottery.ai.analyst.question_classifier import ResearchQuestion

    rq = ResearchQuestion(
        "last_times",
        {
            "numbers": ["22"],
            "lotteries": sticky4,
            "lottery_explicit": False,
        },
        raw_message=Q_LAST_22,
    )
    steps, meta = DynamicResearchPlanner.build(rq, st)
    primary = next(
        s for s in steps if s.purpose == "last_occurrence_all_lotteries"
    )
    assert primary.params["lotteries"] == list(DEFAULT_ALL_HISTORY_LOTTERIES)[:8]
    assert "Gana Más" in primary.params["lotteries"]
    assert meta.get("lotteries") == list(DEFAULT_ALL_HISTORY_LOTTERIES)[:8]
