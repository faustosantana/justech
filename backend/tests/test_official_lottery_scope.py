"""OFFICIAL_LOTTERY_SCOPE — mandatory product universe for Lottery Analyst."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES
from app.lottery.ai.official_lottery_scope import (
    OFFICIAL_LOTTERY_SCOPE,
    canonicalize_lottery_name,
    evidence_uses_non_official_lotteries,
    external_lottery_message,
    is_official_lottery,
    official_lottery_names,
    reject_non_official,
    replace_global_lottery_phrasing,
    resolve_query_lotteries,
    scope_label_es,
)
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_exceptions import LotteryQueryError
from app.services.lottery_intent import resolve_intent
from app.services.lottery_query_service import LotteryQueryService


EXTERNAL_LOTTERIES = ("Haiti Bolet", "King Lottery", "Anguila", "Cash4Life", "Florida")


def test_01_official_scope_is_exactly_seven():
    assert len(OFFICIAL_LOTTERY_SCOPE) == 7
    assert official_lottery_names() == list(OFFICIAL_LOTTERY_SCOPE)
    assert DEFAULT_ALL_HISTORY_LOTTERIES == OFFICIAL_LOTTERY_SCOPE
    # Product seven must include NY draws + core quinielas (not Haiti/Anguila)
    blob = " ".join(OFFICIAL_LOTTERY_SCOPE).lower()
    assert "new york" in blob
    assert "leidsa" in blob
    assert "haiti" not in blob


def test_02_aliases_resolve():
    assert canonicalize_lottery_name("leidsa") == "Leidsa"
    assert canonicalize_lottery_name("Gana mas") == "Gana Más"
    assert canonicalize_lottery_name("Nacional Día") == "New York 2:30"
    assert canonicalize_lottery_name("Loteria Nacional") == "Nacional"
    assert canonicalize_lottery_name("Quiniela Real") == "Real"
    assert canonicalize_lottery_name("Anguila") is None
    assert canonicalize_lottery_name("Haiti Bolet") is None


def test_03_resolve_empty_defaults_to_official():
    assert resolve_query_lotteries(None) == list(OFFICIAL_LOTTERY_SCOPE)
    assert resolve_query_lotteries([]) == list(OFFICIAL_LOTTERY_SCOPE)


def test_04_resolve_filters_external():
    out = resolve_query_lotteries(["Leidsa", "Anguila", "Haiti Bolet", "Real"])
    assert out == ["Leidsa", "Real"]
    assert reject_non_official(["Leidsa", "Anguila"]) == ["Anguila"]


def test_05_scope_label_and_phrasing():
    assert "7 loterías habilitadas" in scope_label_es(short=True)
    text = replace_global_lottery_phrasing("Buscando en todas las loterías del histórico.")
    assert "habilitadas" in text.lower()


def test_06_external_message():
    msg = external_lottery_message("King Lottery")
    assert "King Lottery" in msg
    assert "7" in msg


def test_07_evidence_pollution_detection():
    clean = {
        "lotteries": ["Leidsa", "Real"],
        "last": {"lottery": "Nacional", "appearances": [{"lottery": "Leidsa"}]},
    }
    dirty = {
        "lotteries": ["Leidsa"],
        "last": {
            "appearances": [
                {"lottery": "Leidsa"},
                {"lottery": "Haiti Bolet"},
            ]
        },
    }
    assert evidence_uses_non_official_lotteries(clean) is False
    assert evidence_uses_non_official_lotteries(dirty) is True


@pytest.mark.asyncio
async def test_08_same_day_query_always_passes_lottery_ids():
    svc = LotteryQueryService(db=MagicMock())
    svc.repo = MagicMock()
    svc.repo.same_day_number_coincidences = AsyncMock(return_value=[])

    class _R:
        def __init__(self, name: str):
            self.name = name
            self.id = hash(name) % 10_000

    svc.resolver = MagicMock()
    svc.resolver.resolve_or_raise = AsyncMock(side_effect=lambda name: _R(name))

    await svc.same_day_number_coincidences(["35", "14"], lotteries=None)
    assert svc.repo.same_day_number_coincidences.await_count >= 1
    kwargs = svc.repo.same_day_number_coincidences.await_args.kwargs
    assert kwargs.get("lottery_ids") is not None
    assert len(kwargs["lottery_ids"]) == 7


@pytest.mark.asyncio
async def test_09_same_day_rejects_only_external():
    svc = LotteryQueryService(db=MagicMock())
    with pytest.raises(LotteryQueryError) as exc:
        await svc.same_day_number_coincidences(["35", "14"], lotteries=["Haiti Bolet"])
    assert "habilitadas" in exc.value.message.lower()


def test_10_individual_and_pair_planner_scope():
    st = ConversationState()
    q = QuestionClassifier.classify("¿Cuántas veces han salido el 35 y el 14?", st, {})
    assert q is not None
    assert q.kind == "coincidences_only"
    steps, meta = DynamicResearchPlanner.build(q, st)
    assert meta.get("relation") == "same_day"
    primary = next(s for s in steps if s.purpose == "same_day_coincidence")
    assert primary.tool == LotteryToolName.GET_NUMBER_OCCURRENCES.value
    lots = primary.params.get("lotteries") or []
    assert set(lots) == set(OFFICIAL_LOTTERY_SCOPE)
    for ext in EXTERNAL_LOTTERIES:
        assert ext not in lots


def test_11_last_n_defaults_to_official_in_tools():
    from app.lottery.ai.official_lottery_scope import official_lottery_names

    # Mirrors lottery_tools last_n empty-lotteries branch
    lots = resolve_query_lotteries(None)
    assert lots == official_lottery_names()


def test_12_intent_rejects_haiti():
    ctx = LotterySessionContext()
    res = resolve_intent("¿Cuántas veces salió el 35 en Haiti Bolet?", ctx)
    assert res.kind == "refuse"
    assert "Haiti" in (res.refuse_message or "")


def test_13_session_expiration_invalidates_dirty_evidence():
    from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
    from app.lottery.ai.active_investigation.session_expiration import SessionExpirationManager

    inv = ActiveInvestigationSession(
        subjects=["35", "14"],
        relation="same_day",
        evidence={
            "lotteries": ["Leidsa"],
            "last": {"appearances": [{"lottery": "Anguila", "number": "35"}]},
        },
        last_event={"appearances": [{"lottery": "Anguila"}]},
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    state = ConversationState(active_investigation=inv.to_store(), active_relation="same_day")
    mgr = SessionExpirationManager()
    state2, inv2, meta = mgr.apply_on_turn_start(state)
    assert inv2 is None
    assert meta.get("status") == "invalidated_out_of_scope"
    assert state2.active_investigation == {}


def test_14_hermes_refuses_reuse_of_dirty_evidence():
    from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecisionEngine

    ok = HermesDecisionEngine._can_answer_from_evidence(
        "lotteries",
        {"lotteries": ["Leidsa"], "appearances": [{"lottery": "Leidsa"}]},
        {},
    )
    dirty = HermesDecisionEngine._can_answer_from_evidence(
        "lotteries",
        {"lotteries": ["King Lottery"], "appearances": [{"lottery": "King Lottery"}]},
        {},
    )
    assert ok is True
    assert dirty is False


def test_15_follow_up_preserves_pair_and_official_scope():
    st = ConversationState(
        active_numbers=["35", "14"],
        active_pair=["35", "14"],
        active_relation="same_day",
    )
    q = QuestionClassifier.classify("¿En cuáles loterías han coincidido?", st, {})
    assert q is not None
    steps, meta = DynamicResearchPlanner.build(q, st)
    # Attribute follow-ups may reuse evidence OR re-plan same_day — either way subjects stay
    nums = list(meta.get("subjects") or [])
    if not nums:
        for s in steps:
            params = s.params if hasattr(s, "params") else {}
            nums = list(params.get("numbers") or [])
            if nums:
                break
    if nums:
        assert set(nums[:2]) == {"35", "14"} or {"35", "14"}.issubset(set(nums))
    for s in steps:
        params = s.params if hasattr(s, "params") else {}
        lots = params.get("lotteries") or []
        for ext in EXTERNAL_LOTTERIES:
            assert ext not in lots


def test_16_switch_official_lottery_stays_in_scope():
    st = ConversationState(
        active_numbers=["35"],
        active_lotteries=["Leidsa"],
        active_relation=None,
    )
    q = QuestionClassifier.classify("Ahora en la Real", st, {})
    # May clarify or plan — never inject external
    if q is None:
        return
    steps, _meta = DynamicResearchPlanner.build(q, st)
    for s in steps:
        params = s.params if hasattr(s, "params") else {}
        for key in ("lottery", "lotteries"):
            val = params.get(key)
            names = [val] if isinstance(val, str) else list(val or [])
            for n in names:
                if n:
                    assert is_official_lottery(str(n))


def test_17_no_external_names_in_scope_helpers():
    for name in OFFICIAL_LOTTERY_SCOPE:
        assert is_official_lottery(name)
    for ext in EXTERNAL_LOTTERIES:
        assert not is_official_lottery(ext)


def test_18_evidence_aggregator_strips_external():
    from app.lottery.ai.active_investigation.evidence_aggregator import EvidenceAggregator

    ev = EvidenceAggregator.from_same_day_summary(
        {
            "numbers": ["35", "14"],
            "total": 1,
            "items": [
                {
                    "date": "2024-01-01",
                    "appearances": [
                        {"number": "35", "lottery": "Leidsa"},
                        {"number": "14", "lottery": "Anguila"},
                    ],
                }
            ],
            "last": {
                "date": "2024-01-01",
                "appearances": [
                    {"number": "35", "lottery": "Leidsa"},
                    {"number": "14", "lottery": "Anguila"},
                ],
            },
        }
    )
    assert "Anguila" not in (ev.get("lotteries") or [])
    assert all(is_official_lottery(x) for x in (ev.get("lotteries") or []))
