"""v2.4.4 — automated regressions for the 32 conversational FAIL cases.

These encode the audit specification (origin rules), not hard-coded reply text.
"""

from __future__ import annotations

import re

import pytest

from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.evidence_engine import EvidenceEngine
from app.lottery.ai.analyst.historical_comparator import compare_numbers_steps
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.analyst.response_formatter import format_short_response
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.same_day_coincidence import (
    extract_all_numbers,
    is_same_day_coincidence_question,
)
from app.lottery.ai.turn_policy import (
    exclude_limit_from_subjects,
    extract_occurrence_limit,
    extract_subject_numbers,
    purpose_label_es,
    scrub_internal_jargon,
)
from app.services.lottery_aliases import is_ambiguous_nacional_dia
from app.services.lottery_permissions import (
    CONFIRMED_PRIORITY_SOURCE_IDS,
    UNRESOLVED_AMBIGUOUS_ALIASES,
)


# ---------------------------------------------------------------------------
# Extraction — never treat limit as subject (A.7, E.1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Ahora las últimas 4 del 35.", ["35"]),
        ("Busca las últimas 5 apariciones del 54.", ["54"]),
        ("¿Y las últimas 3 veces?", []),
        ("las últimas diez del 97", ["97"]),
        ("últimas cuatro del 22", ["22"]),
    ],
)
def test_subject_never_equals_limit_digit(text, expected):
    found = extract_subject_numbers(text)
    assert found == expected
    lim = extract_occurrence_limit(text)
    if lim and found:
        assert str(int(found[0])) != str(int(lim))
        assert found[0] != str(int(lim)).zfill(2)


def test_extract_all_numbers_strips_quantity():
    assert "04" not in extract_all_numbers("Ahora las últimas 4 del 35.")
    assert extract_all_numbers("Ahora las últimas 4 del 35.") == ["35"]
    assert "05" not in extract_all_numbers("Busca las últimas 5 apariciones del 54.")


def test_exclude_limit_helper():
    assert exclude_limit_from_subjects(["04", "35"], 4) == ["35"]
    assert exclude_limit_from_subjects(["05", "54"], 5) == ["54"]


# ---------------------------------------------------------------------------
# Classifier — last_n / previous / same_day / compare
# ---------------------------------------------------------------------------


def test_a7_last_n_of_35_not_04():
    q = QuestionClassifier.classify("Ahora las últimas 4 del 35.", ConversationState(), {})
    assert q is not None
    assert q.kind == "last_n_occurrences"
    assert q.params["numbers"] == ["35"]
    assert q.params["limit"] == 4


def test_e1_last_5_of_54_not_05():
    q = QuestionClassifier.classify(
        "Busca las últimas 5 apariciones del 54.", ConversationState(), {}
    )
    assert q is not None
    assert q.kind == "last_n_occurrences"
    assert q.params["numbers"] == ["54"]
    assert q.params["limit"] == 5


def test_a6_previous_two_keeps_97():
    st = ConversationState(
        active_numbers=["97"],
        last_analysis={"limit": 3, "items": [{}, {}, {}]},
        last_intent="last_n_occurrences",
    )
    q = QuestionClassifier.classify("Dame las dos anteriores a esas.", st, {"numbers": ["97"]})
    assert q is not None
    assert q.kind == "last_n_occurrences"
    assert q.params["numbers"] == ["97"]
    assert q.params.get("page_offset") == 3
    assert q.params.get("result_limit") == 2


def test_f3_otras_tres_is_last_n_not_position():
    st = ConversationState(active_numbers=["44"], last_analysis={"limit": 1}, last_intent="last_times")
    q = QuestionClassifier.classify("¿Y las otras tres?", st, {})
    assert q is not None
    assert q.kind == "last_n_occurrences"
    assert q.params["numbers"] == ["44"]
    assert q.params.get("result_limit") == 3 or q.params.get("limit") >= 3


def test_c1_same_day_not_complete_analysis():
    assert is_same_day_coincidence_question("¿Han salido el 55 y el 24 el mismo día?")
    q = QuestionClassifier.classify(
        "¿Han salido el 55 y el 24 el mismo día?", ConversationState(), {}
    )
    assert q is not None
    assert q.kind == "coincidences_only"
    assert q.params.get("relation") == "same_day"
    assert set(q.params.get("numbers") or []) >= {"55", "24"}


def test_d1_compare_two_numbers():
    q = QuestionClassifier.classify(
        "Compara el 54 con el 94 en todo el histórico.", ConversationState(), {}
    )
    assert q is not None
    assert q.kind == "compare_numbers"
    assert q.params["numbers"][:2] == ["54", "94"]


def test_b2_inherits_nacional_on_last_n():
    st = ConversationState(
        active_numbers=["35"],
        active_lotteries=["Nacional"],
        active_filters={"lottery_explicit": True, "position_explicit": True},
        active_position="1",
        last_intent="last_times",
    )
    q = QuestionClassifier.classify("¿Y las últimas 3?", st, {"numbers": ["35"], "limit": 3})
    assert q is not None
    assert q.kind == "last_n_occurrences"
    assert q.params.get("lottery_explicit") is True
    assert "Nacional" in (q.params.get("lotteries") or [])


def test_b3_all_positions_keeps_subject():
    st = ConversationState(
        active_numbers=["35"],
        active_lotteries=["Nacional"],
        active_filters={"lottery_explicit": True, "position_explicit": True},
        last_analysis={"limit": 3},
        last_intent="last_n_occurrences",
    )
    q = QuestionClassifier.classify("Ahora en todas las posiciones.", st, {"numbers": ["35"]})
    assert q is not None
    assert q.params.get("position_scope") == "all"
    assert q.kind in {"last_n_occurrences", "last_times"}


def test_b5_most_recent():
    st = ConversationState(active_numbers=["35"], last_intent="last_n_occurrences")
    q = QuestionClassifier.classify("¿Cuál fue la más reciente?", st, {})
    assert q is not None
    assert q.kind == "last_times"


def test_h4_correction_to_97():
    st = ConversationState(active_numbers=["22"], last_intent="last_times")
    q = QuestionClassifier.classify("No, me refiero al 97.", st, {})
    assert q is not None
    assert q.kind == "last_times"
    assert q.params["numbers"] == ["97"]


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


def test_planner_last_n_subject_35():
    q = QuestionClassifier.classify("Ahora las últimas 4 del 35.", ConversationState(), {})
    steps, meta = DynamicResearchPlanner.build(q, ConversationState())
    assert meta["subjects"] == ["35"]
    assert steps
    assert steps[0].params.get("number") == "35"
    assert steps[0].params.get("limit") == 4


def test_planner_same_day_uses_occurrences_not_complete():
    q = QuestionClassifier.classify(
        "¿Han salido el 55 y el 24 el mismo día?", ConversationState(), {}
    )
    steps, meta = DynamicResearchPlanner.build(q, ConversationState())
    assert steps
    assert not any("complete_analysis" in (s.purpose or "") for s in steps)
    assert any("same_day" in (s.purpose or "") or s.params.get("relation") == "same_day" for s in steps)
    assert meta.get("relation") == "same_day" or q.params.get("relation") == "same_day"


def test_compare_steps_both_subjects_first():
    steps = compare_numbers_steps(a="54", b="94", lotteries=["Nacional", "Real"])
    purposes = [s.purpose for s in steps[:4]]
    assert "compare_a_last" in purposes or "compare_a_occurrences" in purposes
    assert "compare_b_last" in purposes or "compare_b_occurrences" in purposes
    assert any("compare_a_lotteries" == p for p in purposes) or any(
        s.purpose == "compare_a_lotteries" for s in steps
    )
    assert any(s.purpose == "compare_b_lotteries" for s in steps)


def test_planner_last_times_passes_position():
    st = ConversationState(
        active_numbers=["88"],
        active_filters={"position_explicit": True},
        active_position="1",
    )
    q = QuestionClassifier.classify(
        "¿Cuándo salió por última vez el 88 en primera posición?",
        st,
        {"numbers": ["88"], "position_scope": 1, "position_explicit": True},
    )
    steps, meta = DynamicResearchPlanner.build(q, st)
    assert any(s.params.get("position") == 1 for s in steps) or meta.get("position") == 1


# ---------------------------------------------------------------------------
# Nacional alias
# ---------------------------------------------------------------------------


def test_nacional_not_ambiguous():
    assert "nacional" not in UNRESOLVED_AMBIGUOUS_ALIASES
    assert CONFIRMED_PRIORITY_SOURCE_IDS.get("nacional") == 4
    assert not is_ambiguous_nacional_dia("Nacional")
    assert is_ambiguous_nacional_dia("Nacional Día")


# ---------------------------------------------------------------------------
# Formatter / evidence
# ---------------------------------------------------------------------------


def test_scrub_removes_last_n_jargon():
    text = "Detalle\n- last_n_occurrences: 3 casos/registros consultados.\n- compare_a_lotteries: 223"
    out = scrub_internal_jargon(text)
    assert "last_n_occurrences" not in out
    assert "compare_a_lotteries" not in out


def test_purpose_label_human():
    label = purpose_label_es("last_n_occurrences")
    assert "_" not in label


def test_evidence_findings_no_snake_purpose():
    pkg = EvidenceEngine.assemble(
        kind="last_n_occurrences",
        tool_trace=[{"tool": "lottery_get_number_occurrences", "status": "success"}],
        evidence_bundle=[
            {
                "purpose": "last_n_occurrences",
                "tool": "lottery_get_number_occurrences",
                "summary": {
                    "semantics": "last_n_occurrences",
                    "number": "97",
                    "count": 3,
                    "total": 3,
                    "last_occurrence_date": "2026-07-18",
                    "lottery": "Nacional Noche",
                    "items": [
                        {"date": "2026-07-18", "lottery": "Nacional Noche", "position": "2do"},
                        {"date": "2026-07-15", "lottery": "Real", "position": "3ro"},
                        {"date": "2026-07-11", "lottery": "Nacional Noche", "position": "1ro"},
                    ],
                },
            }
        ],
        context={"numbers": ["97"]},
    )
    blob = " ".join(pkg.findings + pkg.timeline + pkg.comparisons)
    assert "last_n_occurrences" not in blob


def test_short_response_no_jargon():
    out = scrub_internal_jargon(
        format_short_response(
            "Las últimas 3 apariciones del 97 fueron:",
            facts={"number": "97"},
            research={"question_kind": "last_n_occurrences"},
            evidence_package={
                "case_count": 3,
                "timeline": ["Última ancla: 2026-07-18 (Nacional Noche)."],
                "findings": ["Número consultado: 97."],
            },
        )
    )
    assert "last_n_occurrences" not in out
    assert "97" in out


def test_frequency_nacional_2026_builds_steps():
    st = ConversationState(active_numbers=["01"])
    q = QuestionClassifier.classify(
        "¿Cuántas veces salió el 1 en Nacional en primera posición en 2026?",
        st,
        {
            "numbers": ["01"],
            "lotteries": ["Nacional"],
            "lottery_explicit": True,
            "year_filter": 2026,
            "position_scope": 1,
            "position_explicit": True,
        },
    )
    assert q is not None
    assert q.kind == "frequency_behavior"
    steps, _meta = DynamicResearchPlanner.build(q, st)
    assert steps
