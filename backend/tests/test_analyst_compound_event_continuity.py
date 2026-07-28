"""Regression — compound event continuity + concrete position labels."""

from __future__ import annotations

from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.same_day_coincidence import (
    build_same_day_follow_up_params,
    format_coincidence_list,
    is_event_list_follow_up,
)
from app.lottery.ai.turn_policy import canonicalize_position_scope, position_label_es


def _same_day_state(**kwargs) -> ConversationState:
    base = dict(
        active_numbers=["35", "14"],
        active_pair=["35", "14"],
        active_relation="same_day",
        last_intent="coincidences_only",
        active_filters={"relation": "same_day"},
        last_analysis={"type": "same_day", "numbers": ["35", "14"], "total": 3},
    )
    base.update(kwargs)
    return ConversationState(**base)


def test_esas_ultimas_3_veces_keeps_compound_coincidence_event():
    st = _same_day_state()
    msg = "¿Cuáles fueron esas últimas 3 veces?"
    assert is_event_list_follow_up(msg)
    fu = build_same_day_follow_up_params(msg, active_numbers=["35", "14"])
    assert fu is not None
    assert fu["relation"] == "same_day"
    assert fu["numbers"] == ["35", "14"]
    assert fu.get("list_mode") is True
    assert int(fu.get("limit") or 0) == 3

    res = IntentResolver.resolve(msg, st)
    q = QuestionClassifier.classify(msg, st, res)
    assert q is not None
    assert q.kind == "coincidences_only"
    assert q.params.get("numbers") == ["35", "14"]
    assert q.params.get("relation") == "same_day"
    assert q.params.get("list_mode") is True
    assert int(q.params.get("limit") or 0) == 3


def test_y_esas_fechas_inherits_same_day_pair():
    st = _same_day_state()
    msg = "¿Y esas fechas?"
    q = QuestionClassifier.classify(msg, st, IntentResolver.resolve(msg, st))
    assert q is not None
    assert q.kind == "coincidences_only"
    assert q.params.get("numbers") == ["35", "14"]


def test_muestrame_las_anteriores_inherits_same_day_pair():
    st = _same_day_state()
    msg = "Muéstrame las anteriores."
    q = QuestionClassifier.classify(msg, st, IntentResolver.resolve(msg, st))
    assert q is not None
    assert q.kind == "coincidences_only"
    assert len(q.params.get("numbers") or []) == 2


def test_never_collapse_pair_to_single_on_deictic_last_n():
    st = _same_day_state()
    for msg in (
        "¿Cuáles fueron esas últimas 3 veces?",
        "esas 3",
        "Dame las anteriores.",
        "esa coincidencia",
    ):
        q = QuestionClassifier.classify(msg, st, IntentResolver.resolve(msg, st))
        assert q is not None, msg
        assert q.kind == "coincidences_only", msg
        assert q.params.get("numbers") == ["35", "14"], msg


def test_position_label_concrete_ordinals_not_todas():
    for raw, expect in (
        ("1ro", "1ra"),
        ("1ra", "1ra"),
        ("2da", "2da"),
        ("3ra", "3ra"),
        (1, "1ra"),
        (2, "2da"),
        (3, "3ra"),
        ("1", "1ra"),
    ):
        label = position_label_es(raw)
        assert "todas las posiciones" not in label.lower(), (raw, label)
        assert expect in label.lower() or expect.replace("ra", "") in label.lower()
        assert canonicalize_position_scope(raw) in (1, 2, 3)


def test_position_none_is_not_filter_scope_wording():
    assert position_label_es(None) == "posición no indicada"
    assert "todas" in position_label_es(None, as_filter_scope=True).lower()


def test_coincidence_list_shows_per_number_positions():
    text = format_coincidence_list(
        {
            "numbers": ["35", "14"],
            "items": [
                {
                    "date": "2026-07-21",
                    "lottery": "Real",
                    "appearances": [
                        {"number": "35", "position": "1ro", "lottery": "Real"},
                        {"number": "14", "position": "3ra", "lottery": "Real"},
                    ],
                },
                {
                    "date": "2026-06-01",
                    "lottery": "Leidsa",
                    "appearances": [
                        {"number": "35", "position": 2},
                        {"number": "14", "position": 1},
                    ],
                },
            ],
        },
        limit=3,
    )
    assert "todas las posiciones" not in text.lower()
    assert "2026-07-21" in text
    assert "Real" in text
    assert "35" in text and "14" in text
    assert "1ra" in text.lower() or "1ra posición" in text.lower()
    assert "3ra" in text.lower() or "3ra posición" in text.lower()


def test_single_subject_last_n_still_works_without_same_day():
    st = ConversationState(active_numbers=["35"], last_intent="last_n_occurrences")
    msg = "Dame las últimas 3."
    q = QuestionClassifier.classify(msg, st, IntentResolver.resolve(msg, st))
    assert q is not None
    assert q.kind == "last_n_occurrences"
    assert q.params.get("numbers") == ["35"]
