"""Regression tests — cert-200 root causes (no per-question hardcoding)."""

from __future__ import annotations

from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.domain_classifier import PREDICTION_MSG, classify_domain
from app.lottery.ai.turn_policy import (
    exclude_limit_from_subjects,
    extract_occurrence_limit,
    extract_subject_numbers,
)


# ---------------------------------------------------------------------------
# R1 — limit digit must never become the ball subject
# ---------------------------------------------------------------------------


def test_r1_ultimas_n_does_not_become_ball_03():
    text = "¿Y las últimas 3?"
    assert extract_occurrence_limit(text) == 3
    assert extract_subject_numbers(text) == []
    assert exclude_limit_from_subjects(["03"], 3) == []


def test_r1_el_07_ultima_vez_is_last_occurrence_not_limit_7():
    text = "Cambio rápido: el 07 última vez."
    assert extract_occurrence_limit(text) is None
    assert extract_subject_numbers(text) == ["07"]
    res = IntentResolver.resolve(text, ConversationState())
    assert res.get("follow_up_kind") == "last_occurrence"
    assert res.get("numbers") == ["07"]
    assert res.get("limit") in (None, 0) or res.get("follow_up_kind") != "last_n_occurrences"
    q = QuestionClassifier.classify(text, ConversationState(), res)
    assert q is not None
    assert q.kind == "last_times"
    assert q.params.get("numbers") == ["07"]


# ---------------------------------------------------------------------------
# R2 — Spanish number words as subjects
# ---------------------------------------------------------------------------


def test_r2_veintidos_extracts_22():
    text = "Dime la más reciente del veintidós."
    assert extract_subject_numbers(text) == ["22"]
    res = IntentResolver.resolve(text, ConversationState(active_numbers=["14"]))
    assert res.get("numbers") == ["22"]
    q = QuestionClassifier.classify(text, ConversationState(active_numbers=["14"]), res)
    assert q is not None
    assert q.kind == "last_times"
    assert q.params.get("numbers") == ["22"]


# ---------------------------------------------------------------------------
# R3 — «Última del N» / «cuándo apareció» → last_times research
# ---------------------------------------------------------------------------


def test_r3_ultima_del_classifies_last_times():
    for text in (
        "Última del 55.",
        "¿Cuándo apareció el 24?",
        "Última del 14 sin filtros.",
        "Última del 88 en primera posición.",
    ):
        res = IntentResolver.resolve(text, ConversationState())
        assert res.get("follow_up_kind") == "last_occurrence", text
        q = QuestionClassifier.classify(text, ConversationState(), res)
        assert q is not None and q.kind == "last_times", text


# ---------------------------------------------------------------------------
# R4 — subject resume / bare statement / return / lottery-only refine
# ---------------------------------------------------------------------------


def test_r4_vuelve_retoma_and_bare_subject_research():
    cases = [
        ("Vuelve al 22.", "22"),
        ("Retoma el 35.", "35"),
        ("Retoma el primer número, el 22.", "22"),
        ("El 44.", "44"),
        ("Ok, el 35 en Leidsa.", "35"),
        ("El 22.", "22"),
    ]
    for text, ball in cases:
        res = IntentResolver.resolve(text, ConversationState(active_numbers=["97"]))
        assert res.get("follow_up_kind") == "last_occurrence", text
        assert ball in (res.get("numbers") or []), text
        q = QuestionClassifier.classify(
            text, ConversationState(active_numbers=["97"]), res
        )
        assert q is not None and q.kind == "last_times", text
        assert ball in (q.params.get("numbers") or []), text


def test_r4_en_nacional_replays_last_with_filter():
    st = ConversationState(
        active_numbers=["44"],
        last_intent="last_times",
    )
    res = IntentResolver.resolve("En Nacional.", st)
    assert res.get("lottery_explicit") is True
    assert res.get("follow_up_kind") == "last_occurrence"
    q = QuestionClassifier.classify("En Nacional.", st, res)
    assert q is not None
    assert q.kind == "last_times"


def test_r4_y_el_subject_switch():
    st = ConversationState(active_numbers=["22"], last_intent="last_times")
    res = IntentResolver.resolve("¿Y el 35?", st)
    assert res.get("follow_up_kind") == "last_occurrence"
    assert res.get("numbers") == ["35"]
    assert res.get("clear_compare") is True
    q = QuestionClassifier.classify("¿Y el 35?", st, res)
    assert q is not None and q.kind == "last_times"
    assert q.params.get("numbers") == ["35"]


# ---------------------------------------------------------------------------
# R5 — sticky lottery cleared on subject/pair switch
# ---------------------------------------------------------------------------


def test_r5_subject_switch_clears_sticky_lottery():
    st = ConversationState(
        active_numbers=["07"],
        active_lotteries=["Nacional"],
        active_filters={"lottery_explicit": True, "lottery": "Nacional"},
    )
    brain = ConversationBrain(st)
    understanding = UnderstandingResult(
        intent="same_day_coincidence",
        numbers=["55", "24"],
        lotteries=[],
        confidence=0.9,
        source="rules",
    )
    resolution = {
        "numbers": ["55", "24"],
        "raw_message": "Cambio a pareja 55 y 24 mismo día.",
        "follow_up_kind": "last_occurrence",
        "inherit_active_number": False,
        "lottery_explicit": False,
    }
    out = brain.apply_resolution(understanding=understanding, resolution=resolution)
    assert out.active_numbers[:2] == ["55", "24"]
    assert not (out.active_filters or {}).get("lottery_explicit")
    assert out.active_lotteries == []


# ---------------------------------------------------------------------------
# R6 — refuse wording must not contain «garantiz*» (cert evaluator)
# ---------------------------------------------------------------------------


def test_r6_prediction_refuse_avoids_garantiz():
    d = classify_domain("Garantiza que mañana sale el 54.")
    assert d.classification == "prediction_request"
    assert d.refuse_message
    assert "garantiz" not in d.refuse_message.lower()
    assert "garantiz" not in PREDICTION_MSG.lower()
