"""v2.4.3 — context policy, last_n follow-ups, no stale/jargon leaks."""

from __future__ import annotations

from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.analyst.response_formatter import format_analyst_response
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.turn_policy import (
    classify_turn_type,
    extract_occurrence_limit,
    extract_subject_numbers,
    filters_label_es,
    position_label_es,
    scrub_internal_jargon,
)
from app.services.lottery_ai_contracts import LotteryToolName


def test_ultimas_3_does_not_become_third_position_or_number_03():
    st = ConversationState(active_numbers=["97"], last_intent="last_occurrence")
    q = "¿Y las últimas 3 veces?"
    res = IntentResolver.resolve(q, st)
    assert res.get("follow_up_kind") == "last_n_occurrences"
    assert res.get("limit") == 3
    assert res.get("position_scope") not in {"third_position", 3, "3"}
    assert res.get("numbers") == ["97"]
    assert "03" not in (res.get("numbers") or [])

    rq = QuestionClassifier.classify(q, st, res)
    assert rq is not None
    assert rq.kind == "last_n_occurrences"
    assert rq.params.get("limit") == 3
    assert rq.params.get("numbers") == ["97"]

    steps, meta = DynamicResearchPlanner.build(rq, st)
    assert meta.get("subjects") == ["97"]
    assert meta.get("limit") == 3
    assert steps
    assert steps[0].tool == LotteryToolName.GET_NUMBER_OCCURRENCES.value
    assert steps[0].params.get("mode") == "last_n"
    assert steps[0].params.get("number") == "97"
    assert steps[0].params.get("limit") == 3


def test_new_query_replaces_stale_pair_55_24():
    st = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        active_lotteries=["Lotería Nacional"],
    )
    q = "¿Cuándo salió por última vez el 97?"
    res = IntentResolver.resolve(q, st)
    assert res.get("numbers") == ["97"]
    st = ConversationBrain(st).apply_resolution(
        understanding=UnderstandingResult(intent="last_occurrence", numbers=["97"], confidence=0.9),
        resolution=res,
    )
    assert st.active_numbers == ["97"]
    assert not st.active_pair
    rq = QuestionClassifier.classify(q, st, res)
    steps, meta = DynamicResearchPlanner.build(rq, st)
    assert meta.get("subjects") == ["97"]
    nums = [s.params.get("number") for s in steps if s.params.get("number")]
    assert nums and all(n == "97" for n in nums)


def test_limit_from_words_cinco():
    assert extract_occurrence_limit("Dame las últimas cinco.") == 5
    assert extract_occurrence_limit("las últimas 10 apariciones") == 10
    assert extract_subject_numbers("¿Y las últimas 3 veces?") == []
    assert extract_subject_numbers("Ahora las últimas 3 del 35.") == ["35"]


def test_explicit_subject_change_35():
    st = ConversationState(active_numbers=["97"], last_intent="last_occurrence")
    q = "Ahora las últimas 3 del 35."
    res = IntentResolver.resolve(q, st)
    assert res.get("limit") == 3
    assert res.get("numbers") == ["35"]
    rq = QuestionClassifier.classify(q, st, res)
    assert rq.kind == "last_n_occurrences"
    assert rq.params.get("numbers") == ["35"]


def test_found_lottery_not_inherited_as_filter():
    """After last occurrence lands on Nacional Noche, follow-up stays all lotteries."""
    st = ConversationState(
        active_numbers=["97"],
        last_intent="last_occurrence",
        last_analysis={"observed": "97", "lottery": "Nacional Noche", "date": "2026-07-18", "position": 2},
        active_lotteries=[],  # result must not have been copied into filters
    )
    q = "¿Y las últimas 3 veces?"
    res = IntentResolver.resolve(q, st)
    rq = QuestionClassifier.classify(q, st, res)
    assert rq.params.get("lottery_explicit") is False
    steps, _ = DynamicResearchPlanner.build(rq, st)
    assert "lotteries" in steps[0].params
    assert len(steps[0].params["lotteries"]) >= 5


def test_explicit_nacional_is_inherited():
    st = ConversationState(
        active_numbers=["97"],
        active_lotteries=["Nacional"],
        active_filters={"lottery_explicit": True, "lottery": "Nacional"},
        last_intent="last_occurrence",
    )
    q = "¿Y las últimas 3?"
    res = IntentResolver.resolve(q, st)
    # No new lottery named — classifier keeps named_lots empty from resolution;
    # brain/state still has explicit filter for orchestrator.
    assert res.get("numbers") == ["97"]
    assert res.get("limit") == 3


def test_position_labels_never_internal():
    assert "third_position" not in position_label_es("third_position")
    assert "tercera" in position_label_es("third_position")
    label = filters_label_es(lottery_scope="all", position_scope="all")
    assert "third_position" not in label
    assert "Todas las loterías" in label
    scrubbed = scrub_internal_jargon(
        "No encontré suficiente evidencia con las herramientas disponibles. metric=last_occurrence_and_count_across_lotteries third_position"
    )
    assert "herramientas disponibles" not in scrubbed.lower() or "histórico" in scrubbed.lower()
    assert "third_position" not in scrubbed
    assert "last_occurrence_and_count_across_lotteries" not in scrubbed


def test_formatter_no_zero_count_with_date():
    text = format_analyst_response(
        "La última aparición del 97 fue el 2026-07-18.",
        facts={"observed": "97", "lottery": "Nacional Noche", "last_occurrence_date": "2026-07-18", "total": 12},
        research={
            "question_kind": "last_times",
            "evidence_package": {
                "case_count": 12,
                "timeline": ["Última ancla: 2026-07-18 (Nacional Noche)."],
                "findings": ["Número consultado: 97."],
            },
        },
    )
    assert "97" in text
    assert "55" not in text
    assert "Cantidad de casos/registros: 0" not in text
    assert "third_position" not in text


def test_turn_types():
    assert classify_turn_type("Hola") == "greeting"
    assert classify_turn_type("¿Cuándo salió el 97?") == "new_query"
    assert classify_turn_type("¿Y las últimas 3 veces?", has_active_subject=True) == "follow_up"
    assert classify_turn_type("Compáralo con el 35", has_active_subject=True) == "comparison"


def test_sequence_subjects_22_35_97():
    st = ConversationState(
        active_pair=["55", "24"],
        active_numbers=["55", "24"],
        active_relation="same_day",
    )
    planned = []
    for q, exp in (
        ("¿Cuándo salió por última vez el 22?", "22"),
        ("¿Cuándo salió por última vez el 35?", "35"),
        ("¿Y el 97 cuándo salió?", "97"),
    ):
        res = IntentResolver.resolve(q, st)
        st = ConversationBrain(st).apply_resolution(
            understanding=UnderstandingResult(intent="last_occurrence", numbers=[exp], confidence=0.9),
            resolution=res,
        )
        rq = QuestionClassifier.classify(q, st, res)
        steps, meta = DynamicResearchPlanner.build(rq, st)
        assert meta.get("subjects") == [exp]
        planned.append(exp)
    # follow last 3 on 97
    q = "¿Y las últimas 3 veces?"
    res = IntentResolver.resolve(q, st)
    assert res.get("numbers") == ["97"]
    assert res.get("limit") == 3
    rq = QuestionClassifier.classify(q, st, res)
    assert rq.kind == "last_n_occurrences"
    steps, meta = DynamicResearchPlanner.build(rq, st)
    assert meta.get("subjects") == ["97"]
    assert meta.get("limit") == 3
    assert planned == ["22", "35", "97"]
