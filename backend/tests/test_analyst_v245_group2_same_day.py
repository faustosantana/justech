"""v2.4.5 Grupo 2 — C.1–C.4 same_day 55+24.

Root cause: lottery_tools called QueryService.same_day_number_coincidences
but selective deploy omitted lottery_query_service + lottery_repository,
so prod raised AttributeError → tool status=error → «No pude completar».
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.conversation_state import ConversationState
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_query_service import LotteryQueryService
from app.services.lottery_repository import LotteryRepository
from app.services.lottery_tools import LotteryToolExecutor


Q_SAME = "¿Han salido el 55 y el 24 el mismo día?"


def test_c1_classifier_and_planner_same_day_contract():
    st = ConversationState()
    q = QuestionClassifier.classify(Q_SAME, st, {})
    assert q is not None
    assert q.kind == "coincidences_only"
    assert q.params.get("relation") == "same_day"
    assert set(q.params.get("numbers") or []) >= {"55", "24"}
    steps, meta = DynamicResearchPlanner.build(q, st)
    assert meta.get("relation") == "same_day"
    primary = next(s for s in steps if s.purpose == "same_day_coincidence")
    assert primary.tool == LotteryToolName.GET_NUMBER_OCCURRENCES.value
    assert primary.params.get("relation") == "same_day"
    assert set(primary.params.get("numbers") or []) >= {"55", "24"}


def test_c2_nacional_followup_keeps_pair_and_lottery():
    st = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        active_lotteries=["Nacional"],
        active_filters={"lottery_explicit": True},
    )
    q = QuestionClassifier.classify(
        "¿Y en Nacional?",
        st,
        {"lotteries": ["Nacional"], "lottery_filter": True, "active_relation": "same_day"},
    )
    assert q is not None
    assert q.kind == "coincidences_only"
    assert q.params.get("relation") == "same_day"
    steps, _meta = DynamicResearchPlanner.build(q, st)
    primary = next(s for s in steps if s.purpose == "same_day_coincidence")
    assert primary.params.get("lottery") == "Nacional" or "Nacional" in (
        primary.params.get("lotteries") or []
    )


def test_query_and_repo_expose_same_day_method():
    """Deploy contract: tools depend on these methods existing."""
    assert hasattr(LotteryQueryService, "same_day_number_coincidences")
    assert hasattr(LotteryRepository, "same_day_number_coincidences")
    assert callable(LotteryQueryService.same_day_number_coincidences)
    assert callable(LotteryRepository.same_day_number_coincidences)


@pytest.mark.asyncio
async def test_tool_same_day_dispatch_uses_query_method():
    db = MagicMock()
    ex = LotteryToolExecutor(
        db,
        tenant_id=MagicMock(),
        user_id=MagicMock(),
        role="admin",
        is_superadmin=True,
    )
    ex.query.same_day_number_coincidences = AsyncMock(
        return_value={
            "relation": "same_day",
            "numbers": ["55", "24"],
            "total": 2,
            "items": [
                {"date": "2026-07-19", "appearances": []},
                {"date": "2026-06-01", "appearances": []},
            ],
            "last_date": "2026-07-19",
        }
    )
    data, total, summary = await ex._dispatch(
        LotteryToolName.GET_NUMBER_OCCURRENCES,
        {
            "numbers": ["55", "24"],
            "relation": "same_day",
            "active_relation": "same_day",
            "limit": 200,
        },
        {},
    )
    ex.query.same_day_number_coincidences.assert_awaited_once()
    assert total == 2
    assert summary.get("semantics") == "same_day_coincidence"
    assert summary.get("found") is True
    assert summary.get("last_occurrence_date") == "2026-07-19"
