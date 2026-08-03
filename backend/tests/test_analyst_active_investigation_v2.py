"""Analyst 2.0 — Active Investigation Session unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.lottery.ai.active_investigation import (
    HermesDecisionEngine,
    InvestigationStateManager,
    NaturalResponseGenerator,
    SessionExpirationManager,
)
from app.lottery.ai.active_investigation.contextual_follow_up import ContextualFollowUpResolver
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession, TTL_SECONDS
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.same_day_coincidence import (
    build_same_day_follow_up_params,
    is_event_attribute_follow_up,
)


def _same_day_inv(**kwargs) -> ActiveInvestigationSession:
    base = dict(
        subjects=["78", "02"],
        relation="same_day",
        metric="same_day",
        event_type="same_day_coincidence",
        date_anchor="2026-07-19",
        last_event={
            "date": "2026-07-19",
            "lottery": "Real",
            "lotteries": ["Real", "Nacional"],
            "appearances": [
                {"number": "78", "lottery": "Real", "position": "1ro"},
                {"number": "02", "lottery": "Nacional", "position": "3ro"},
            ],
            "numbers": ["78", "02"],
        },
        evidence={
            "type": "same_day_coincidence",
            "numbers": ["78", "02"],
            "total": 5,
            "lotteries": ["Real", "Nacional"],
            "last": {
                "date": "2026-07-19",
                "lottery": "Real",
                "appearances": [
                    {"number": "78", "lottery": "Real", "position": "1ro"},
                    {"number": "02", "lottery": "Nacional", "position": "3ro"},
                ],
            },
        },
    )
    base.update(kwargs)
    return ActiveInvestigationSession(**base)


def test_ttl_active_at_9_minutes():
    inv = _same_day_inv()
    inv.updated_at = datetime.now(timezone.utc)
    inv.expires_at = inv.updated_at + timedelta(seconds=TTL_SECONDS)
    assert not inv.is_expired(now=inv.updated_at + timedelta(minutes=9))


def test_ttl_expires_at_10_minutes():
    inv = _same_day_inv()
    inv.updated_at = datetime.now(timezone.utc) - timedelta(minutes=11)
    inv.expires_at = inv.updated_at + timedelta(seconds=TTL_SECONDS)
    assert inv.is_expired()


def test_ttl_renew_on_touch():
    inv = _same_day_inv()
    inv.expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    before = inv.expires_at
    inv.touch()
    assert inv.expires_at > before


def test_expiration_manager_clears_sticky_same_day():
    st = ConversationState(
        active_numbers=["78", "02"],
        active_relation="same_day",
        active_filters={"relation": "same_day"},
        active_investigation=_same_day_inv(
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
        ).to_store(),
    )
    st2, inv, meta = SessionExpirationManager().apply_on_turn_start(st)
    assert inv is None
    assert meta["status"] == "expired_cleared"
    assert st2.active_relation is None
    assert not st2.active_investigation


def test_en_cuales_loterias_is_attribute_follow_up():
    assert is_event_attribute_follow_up("¿En cuáles loterías salió?")
    assert ContextualFollowUpResolver.detect_attribute("¿En cuáles loterías?") == "lotteries"
    assert ContextualFollowUpResolver.detect_attribute("¿Y en qué posiciones?") == "positions"


def test_build_same_day_follow_up_keeps_pair_for_lotteries_ask():
    fu = build_same_day_follow_up_params(
        "¿En cuáles loterías salió?",
        active_numbers=["78", "02"],
    )
    assert fu is not None
    assert fu["numbers"] == ["78", "02"]
    assert fu["relation"] == "same_day"
    assert fu.get("want_last_only") is True


def test_classifier_keeps_compound_on_loterias_follow_up():
    st = ConversationState(
        active_numbers=["78", "02"],
        active_pair=["78", "02"],
        active_relation="same_day",
        last_intent="coincidences_only",
        active_filters={"relation": "same_day"},
        last_analysis={"type": "same_day_coincidence", "numbers": ["78", "02"]},
    )
    msg = "¿En cuáles loterías salió?"
    res = IntentResolver.resolve(msg, st)
    q = QuestionClassifier.classify(msg, st, res)
    assert q is not None
    assert q.kind == "coincidences_only"
    assert q.params.get("numbers") == ["78", "02"]
    assert q.params.get("relation") == "same_day"


def test_hermes_reuses_evidence_for_lotteries():
    st = ConversationState(
        active_numbers=["78", "02"],
        active_pair=["78", "02"],
        active_relation="same_day",
    )
    inv = _same_day_inv()
    st.active_investigation = inv.to_store()
    d = HermesDecisionEngine.decide(
        "¿En cuáles loterías?",
        state=st,
        investigation=inv,
        resolution={"follow_up_kind": "lotteries"},
    )
    assert d.turn_type == "attribute_of_last_event"
    assert d.requested_attribute == "lotteries"
    assert d.inherited_subjects == ["78", "02"]
    assert d.reuse_evidence is True
    assert d.requires_research is False


def test_natural_answer_lotteries_from_evidence():
    inv = _same_day_inv()
    d = HermesDecisionEngine.decide(
        "¿En cuáles loterías?",
        state=ConversationState(active_numbers=["78", "02"], active_relation="same_day"),
        investigation=inv,
    )
    text = NaturalResponseGenerator.answer_attribute_from_evidence(d, inv)
    assert text
    assert "78" in text and "02" in text
    assert "Real" in text or "Nacional" in text
    assert "same_day" not in text.lower()
    assert "No pude completar" not in text


def test_natural_answer_positions_from_evidence():
    inv = _same_day_inv()
    d = HermesDecisionEngine.decide(
        "¿Y en qué posiciones?",
        state=ConversationState(active_numbers=["78", "02"], active_relation="same_day"),
        investigation=inv,
    )
    text = NaturalResponseGenerator.answer_attribute_from_evidence(d, inv)
    assert text
    assert "1ra" in text.lower() or "posición" in text.lower()
    assert "78" in text and "02" in text


def test_state_manager_preserves_pair_after_research():
    st = ConversationState()
    mgr = InvestigationStateManager()
    d = HermesDecisionEngine.decide(
        "¿Cuándo fue la última vez que salió el 78 y el 02 el mismo día?",
        state=st,
        investigation=None,
    )
    inv = mgr.begin_or_continue(st, decision=d, message="test")
    assert inv is not None
    mgr.update_after_research(
        st,
        investigation=inv,
        summary={
            "numbers": ["78", "02"],
            "relation": "same_day",
            "total": 3,
            "items": [
                {
                    "date": "2026-07-19",
                    "lottery": "Real",
                    "appearances": [
                        {"number": "78", "lottery": "Real", "position": "1ro"},
                        {"number": "02", "lottery": "Nacional", "position": "3ro"},
                    ],
                }
            ],
            "last": {
                "date": "2026-07-19",
                "lottery": "Real",
                "appearances": [
                    {"number": "78", "lottery": "Real", "position": "1ro"},
                    {"number": "02", "lottery": "Nacional", "position": "3ro"},
                ],
            },
        },
        template="ok",
        tools=["lottery_get_number_occurrences"],
        intent="coincidences_only",
    )
    assert st.active_numbers == ["78", "02"]
    assert st.active_relation == "same_day"
    assert st.active_investigation.get("subjects") == ["78", "02"]


def test_remember_occurrence_does_not_collapse_same_day_pair():
    st = ConversationState(
        active_numbers=["78", "02"],
        active_pair=["78", "02"],
        active_relation="same_day",
    )
    st.remember_occurrence(lottery="Real", number="78", draw_date="2026-07-19", position=1)
    assert st.active_numbers == ["78", "02"]


def _single_inv(n: str = "57") -> ActiveInvestigationSession:
    return ActiveInvestigationSession(
        subjects=[n],
        relation=None,
        metric=None,
        topic=f"número {n}",
        status="active",
    )


def test_table_follow_up_attrs_detected():
    assert ContextualFollowUpResolver.detect_attribute("¿Cuáles son sus compañeros?") == "companions"
    assert ContextualFollowUpResolver.detect_attribute("¿Y su relación en la Tabla 1?") == "tabla1"
    assert ContextualFollowUpResolver.detect_attribute("Muéstrame la Tabla 2") == "tabla2"
    assert ContextualFollowUpResolver.detect_attribute("¿Cuáles son sus vecinos?") == "neighbors"
    assert ContextualFollowUpResolver.detect_attribute("¿Cuál es su código?") == "table_code"
    assert ContextualFollowUpResolver.detect_attribute("Compara sus vecinos") == "compare_neighbors"
    assert ContextualFollowUpResolver.detect_attribute("Compara sus compañeros") == "compare_companions"


def test_hermes_reuses_catalog_for_companions_without_repeating_number():
    inv = _single_inv("57")
    st = ConversationState(
        active_numbers=["57"],
        active_investigation=inv.to_store(),
    )
    d = HermesDecisionEngine.decide(
        "¿Cuáles son sus compañeros?",
        state=st,
        investigation=inv,
    )
    assert d.turn_type == "attribute_of_last_event"
    assert d.requested_attribute == "companions"
    assert d.inherited_subjects == ["57"]
    assert d.reuse_evidence is True
    assert d.requires_research is False


def test_natural_answer_companions_from_catalog():
    inv = _single_inv("57")
    d = HermesDecisionEngine.decide(
        "¿Cuáles son sus compañeros?",
        state=ConversationState(active_numbers=["57"]),
        investigation=inv,
    )
    text = NaturalResponseGenerator.answer_attribute_from_evidence(d, inv)
    assert text
    assert "57" in text
    assert "Tabla 1" in text or "compañeros" in text.lower() or "código" in text.lower()


def test_topic_switch_discards_prior_investigation():
    inv = _single_inv("57")
    st = ConversationState(
        active_numbers=["57"],
        active_investigation=inv.to_store(),
    )
    mgr = InvestigationStateManager()
    d = HermesDecisionEngine.decide(
        "Ahora analiza el 35",
        state=st,
        investigation=inv,
    )
    assert d.turn_type == "topic_switch"
    assert d.inherited_subjects == ["35"]
    new_inv = mgr.begin_or_continue(st, decision=d, message="Ahora analiza el 35")
    assert new_inv is not None
    assert new_inv.subjects == ["35"]
    assert st.active_numbers == ["35"]


def test_compare_creates_comparative_investigation():
    st = ConversationState()
    mgr = InvestigationStateManager()
    d = HermesDecisionEngine.decide(
        "Compara el 57 con el 35",
        state=st,
        investigation=None,
    )
    assert d.turn_type == "new_investigation"
    assert sorted(d.inherited_subjects[:2]) == ["35", "57"]
    assert d.inherited_relation == "compare"
    inv = mgr.begin_or_continue(st, decision=d, message="Compara el 57 con el 35")
    assert inv is not None
    assert sorted(inv.subjects[:2]) == ["35", "57"]
    assert inv.relation == "compare"


def test_close_investigation_clears_sticky():
    inv = _single_inv("57")
    st = ConversationState(
        active_numbers=["57"],
        active_investigation=inv.to_store(),
    )
    mgr = InvestigationStateManager()
    st2 = mgr.close(st)
    assert st2.active_numbers == []
    closed = ActiveInvestigationSession.from_store(st2.active_investigation)
    assert closed is not None
    assert closed.status == "closed"


def test_state_manager_tracks_tables_on_companions_ask():
    inv = _single_inv("57")
    st = ConversationState(
        active_numbers=["57"],
        active_investigation=inv.to_store(),
    )
    mgr = InvestigationStateManager()
    d = HermesDecisionEngine.decide(
        "¿Cuáles son sus compañeros?",
        state=st,
        investigation=inv,
    )
    out = mgr.begin_or_continue(st, decision=d, message="¿Cuáles son sus compañeros?")
    assert out is not None
    assert "1" in (out.time_window or {}).get("tables", [])
