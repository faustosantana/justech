"""v2.4.5 Grupo 5 — E.2 after-window from last_n anchors.

Root cause: «tres días siguientes a cada una» matched neither IntentResolver._AFTER
nor QuestionClassifier._AFTER, so research never ran. When it does run, base dates
must come from last_analysis.items (not invented dates).
"""

from __future__ import annotations

from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.analyst.temporal_analysis import temporal_after_steps
from app.lottery.ai.conversation_state import ConversationState


ITEMS = [
    {"number": "54", "date": "2026-07-18", "lottery": "Loteka"},
    {"number": "54", "date": "2026-07-10", "lottery": "Nacional"},
    {"number": "54", "date": "2026-06-24", "lottery": "Loteka"},
    {"number": "54", "date": "2026-06-17", "lottery": "Gana Más"},
    {"number": "54", "date": "2026-06-16", "lottery": "Gana Más"},
]

Q_E2 = "¿Qué pasó en los tres días siguientes a cada una?"


def _state() -> ConversationState:
    return ConversationState(
        active_numbers=["54"],
        last_intent="last_n_occurrences",
        last_analysis={
            "observed": "54",
            "lottery": "Loteka",
            "date": "2026-07-18",
            "limit": 5,
            "items": list(ITEMS),
        },
    )


def test_e2_classifier_detects_following_days():
    st = _state()
    res = IntentResolver.resolve(Q_E2, st)
    assert res.get("follow_up_kind") == "after"
    assert res.get("windows") == [3]
    rq = QuestionClassifier.classify(Q_E2, st, res)
    assert rq is not None
    assert rq.kind == "what_usually_happens_after"


def test_e2_planner_uses_only_obtained_anchor_dates():
    st = _state()
    res = IntentResolver.resolve(Q_E2, st)
    rq = QuestionClassifier.classify(Q_E2, st, res)
    steps, meta = DynamicResearchPlanner.build(rq, st)
    assert steps
    dates = [s.params.get("base_date") or s.params.get("date") for s in steps]
    assert dates == [it["date"] for it in ITEMS]
    lots = [s.params.get("lottery") for s in steps]
    assert lots == [it["lottery"] for it in ITEMS]
    assert all(int(s.params.get("days") or 0) == 3 for s in steps)
    assert meta.get("anchors")


def test_temporal_after_does_not_invent_dates_without_anchors():
    steps = temporal_after_steps(number="54", lottery=None, base_date=None, windows=[3])
    assert steps == []


def test_e2_brain_preserves_last_analysis_items_on_after_followup():
    """inherit_active_number=False must not wipe anchors needed by after-window."""
    from app.lottery.ai.analyst.conversation_brain import ConversationBrain
    from app.lottery.ai.conversation_state import UnderstandingResult

    st = _state()
    res = IntentResolver.resolve(Q_E2, st)
    assert res.get("follow_up_kind") == "after"
    assert res.get("inherit_active_number") is False
    und = UnderstandingResult(
        intent="clarification_response",
        needs_clarification=True,
        missing_slots=["query"],
        numbers=["54"],
    )
    st2 = ConversationBrain(st).apply_resolution(understanding=und, resolution=res)
    assert (st2.last_analysis or {}).get("items")
    assert len(st2.last_analysis["items"]) == len(ITEMS)

