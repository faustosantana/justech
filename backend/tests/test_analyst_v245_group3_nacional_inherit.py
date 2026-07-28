"""v2.4.5 Grupo 3 — B.2: «¿Y las últimas 3?» must inherit Nacional.

Root cause: ConversationBrain.apply_resolution only set
active_filters.lottery_explicit when resolution.lottery_explicit or
lottery_filter was set. IntentResolver left lottery_explicit=False for
«en Nacional» because resolve_references filled lotteries without the
flag → B.2 last_n scanned all lotteries.
"""

from __future__ import annotations

from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult


Q_B1 = "¿Cuándo salió por última vez el 35 en Nacional y en primera posición?"
Q_B2 = "¿Y las últimas 3?"


def test_b1_brain_persists_lottery_explicit_from_named_lotteries():
    st = ConversationState()
    res = IntentResolver.resolve(Q_B1, st)
    assert "Nacional" in (res.get("lotteries") or [])
    # Smoking gun of B.2: flag may be false even when Nacional is named
    und = UnderstandingResult(
        intent="last_times",
        numbers=res.get("numbers") or ["35"],
        lotteries=res.get("lotteries") or [],
    )
    st2 = ConversationBrain(st).apply_resolution(understanding=und, resolution=res)
    assert st2.active_lotteries[:1] == ["Nacional"]
    assert (st2.active_filters or {}).get("lottery_explicit") is True
    assert (st2.active_filters or {}).get("lottery") == "Nacional"


def test_b2_last_n_inherits_nacional_after_brain():
    st = ConversationState()
    res1 = IntentResolver.resolve(Q_B1, st)
    und = UnderstandingResult(
        intent="last_times",
        numbers=["35"],
        lotteries=res1.get("lotteries") or ["Nacional"],
    )
    st = ConversationBrain(st).apply_resolution(understanding=und, resolution=res1)
    assert st.active_lotteries == ["Nacional"]
    res2 = IntentResolver.resolve(Q_B2, st)
    q = QuestionClassifier.classify(Q_B2, st, res2)
    assert q is not None
    assert q.kind == "last_n_occurrences"
    assert q.params.get("lottery_explicit") is True
    assert q.params.get("lotteries") == ["Nacional"]
    steps, meta = DynamicResearchPlanner.build(q, st)
    assert meta.get("lottery_explicit") is True or q.params.get("lottery_explicit")
    primary = next(s for s in steps if s.purpose == "last_n_occurrences")
    lots = primary.params.get("lotteries") or []
    assert lots == ["Nacional"] or primary.params.get("lottery") == "Nacional"
