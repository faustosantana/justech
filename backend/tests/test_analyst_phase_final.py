"""Fase Final 2.4.0 — Analista IA humano (continuidad, interpretación, autoverificación)."""

from __future__ import annotations

from app.lottery.ai.analyst.response_formatter import (
    format_analyst_response,
    self_verify_response,
)
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.nlp_stability import classify_nlp
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt
from app.lottery.ai.same_day_coincidence import (
    format_coincidence_narrative,
    summarize_coincidences,
)
from app.lottery.ai.understanding import understand
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent


def test_motor_intact_phase_final():
    for nums, expect in (([35, 14], 54), ([39, 58], 94)):
        r = run_complete_analysis(
            {
                "numbers": [nums[0]],
                "same_day_confirmers": nums[1:],
                "mode": "socio",
                "derivation_depth": 0,
                "create_signals": False,
            },
            persist=False,
        )
        assert r.primary_signal["number"] == expect


def test_engines_prompt_intact_phase_final():
    from app.lottery.ai.analyst import (
        get_discovery_engine,
        get_knowledge_engine,
        get_research_engine,
    )

    assert get_active_prompt().version == "v5"
    assert get_research_engine().VERSION == "2.0"
    assert get_discovery_engine().ENABLED is True
    assert get_knowledge_engine().version == "2.3.0"


def test_case1_greeting_natural():
    q = "Hola, ¿cómo estás?"
    nlp = classify_nlp(q)
    assert nlp.intent == "GREETING"
    assert nlp.run_tools is False
    u, _ = understand(q, ConversationState(active_numbers=["55", "24"], active_relation="same_day"))
    assert u.intent == "greeting"
    assert u.needs_clarification is False
    assert u.tool is None
    r = resolve_intent(q, LotterySessionContext(last_numbers=["55", "24"]))
    assert r.kind == "chat"


def test_case2_count_54_all_history():
    q = "¿Cuántas veces salió el 54?"
    r = resolve_intent(q, LotterySessionContext())
    assert r.kind == "tool"
    assert r.kind != "clarify"
    u, _ = understand(q, ConversationState())
    assert u.needs_clarification is False or "lottery" not in (u.missing_slots or [])


def test_case3_same_day_all_positions():
    q = "¿Han salido el 55 y el 24 el mismo día?"
    r = resolve_intent(q, LotterySessionContext())
    assert r.tool == LotteryToolName.GET_NUMBER_OCCURRENCES
    assert r.params.get("numbers") == ["55", "24"]
    assert r.params.get("relation") == "same_day"
    assert r.params.get("position") is None
    u, _ = understand(q, ConversationState())
    assert set(u.numbers) >= {"55", "24"}


def test_case4_nacional_keeps_pair():
    st = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        position_scope="any_position",
    )
    u, s = understand("¿Y en Nacional?", st)
    assert set(u.numbers) >= {"55", "24"}
    assert u.params.get("relation") == "same_day"
    assert "Nacional" in (u.lotteries or u.params.get("lotteries") or [])
    assert s.active_relation == "same_day"


def test_case5_primera_keeps_lottery():
    st = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        active_lotteries=["Nacional"],
        position_scope="any_position",
    )
    u, s = understand("¿Y en primera posición?", st)
    assert u.params.get("position") == 1
    assert u.params.get("relation") == "same_day"
    assert set(u.numbers) >= {"55", "24"}
    lots = u.params.get("lotteries") or u.lotteries or s.active_lotteries
    assert "Nacional" in lots


def test_case6_restore_all_positions():
    st = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        active_lotteries=["Nacional"],
        position_scope="first_position",
    )
    u, s = understand("Ahora vuelve a todas las posiciones.", st)
    assert u.params.get("position") is None
    assert u.params.get("position_scope") == "any_position"
    assert set(u.numbers) >= {"55", "24"}
    assert s.position_scope == "any_position"


def test_case7_compare_keeps_investigation():
    st = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
    )
    u, s = understand("Compáralo con el 94.", st)
    assert u.params.get("compare_with") == "94"
    assert "55" in u.numbers or u.params.get("number") == "55"
    assert u.params.get("preserve_relation") == "same_day" or s.active_relation == "same_day"
    assert "55" in (s.active_numbers or u.params.get("active_numbers") or [])


def test_case8_after_coincidences():
    st = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        last_analysis={"last_coincidence_date": "2024-06-01"},
    )
    u, _ = understand("¿Qué pasó después de esas coincidencias?", st)
    assert u.params.get("after_coincidences") is True
    assert set(u.numbers) >= {"55", "24"}
    assert u.params.get("date") == "2024-06-01" or u.params.get("base_date") == "2024-06-01"


def test_case9_zero_first_positive_elsewhere():
    payload = {
        "total": 5,
        "items": [
            {
                "date": "2023-05-01",
                "appearances": [
                    {"number": "55", "lottery": "Leidsa", "position": 2},
                    {"number": "24", "lottery": "Loteka", "position": 3},
                ],
            }
        ]
        * 5,
    }
    summary = summarize_coincidences(payload, numbers=["55", "24"], position_filter=None)
    text = format_coincidence_narrative(summary)
    assert summary["first_related"] == 0
    assert "primera posición" in text.lower() or "otras posiciones" in text.lower()
    assert "no encontré evidencia" not in text.lower()
    verified = self_verify_response(
        "No encontré coincidencias.",
        question="¿Han salido juntos?",
        facts={"other_only": 5, "total": 5},
        research={"evidence_package": {"other_only": 5, "case_count": 5}},
    )
    assert "otras posiciones" in verified.lower() or "5" in verified


def test_case10_small_sample_prudence():
    summary = summarize_coincidences(
        {
            "total": 3,
            "items": [
                {
                    "date": f"2024-01-0{i}",
                    "appearances": [
                        {"number": "55", "lottery": "Leidsa", "position": 1},
                        {"number": "24", "lottery": "Loteka", "position": 1},
                    ],
                }
                for i in range(1, 4)
            ],
        },
        numbers=["55", "24"],
    )
    text = format_coincidence_narrative(summary)
    assert "pequeña" in text.lower() or "regla general" in text.lower()


def test_narrative_no_jargon_and_self_verify():
    text = format_analyst_response(
        "Sí. El 55 y el 24 coincidieron el mismo día en 4 ocasiones.",
        research={"relation": "same_day", "numbers": ["55", "24"]},
        question="¿Han salido el 55 y el 24 el mismo día?",
        conversation_context={"active_numbers": ["55", "24"]},
    )
    low = text.lower()
    assert "payload" not in low
    assert "kind" not in low
    assert "prompt maestro" not in low
    assert "herramientas autorizadas" not in low


# ---------------------------------------------------------------------------
# Human evaluation battery (offline rubric against deterministic narratives)
# ---------------------------------------------------------------------------

_HUMAN_CASES = [
    {
        "id": "H1",
        "question": "Hola, ¿cómo estás?",
        "answer": "Hola, estoy muy bien. ¿Qué te gustaría investigar hoy?",
        "expect": {
            "answers_question": True,
            "no_tools": True,
            "no_jargon": True,
            "natural": True,
        },
    },
    {
        "id": "H2",
        "question": "¿Han salido el 55 y el 24 el mismo día?",
        "answer": format_coincidence_narrative(
            summarize_coincidences(
                {
                    "total": 7,
                    "items": [
                        {
                            "date": "2024-03-10",
                            "appearances": [
                                {"number": "55", "lottery": "Leidsa", "position": 1},
                                {"number": "24", "lottery": "Loteka", "position": 2},
                            ],
                        }
                    ]
                    * 7,
                },
                numbers=["55", "24"],
            )
        ),
        "expect": {
            "answers_question": True,
            "both_numbers": True,
            "all_positions_mentioned": True,
            "has_last": True,
            "no_jargon": True,
            "interprets": True,
        },
    },
    {
        "id": "H3",
        "question": "No hay en primera pero sí en otras",
        "answer": format_coincidence_narrative(
            summarize_coincidences(
                {
                    "total": 4,
                    "items": [
                        {
                            "date": "2022-01-01",
                            "appearances": [
                                {"number": "55", "lottery": "Real", "position": 2},
                                {"number": "24", "lottery": "Real", "position": 3},
                            ],
                        }
                    ]
                    * 4,
                },
                numbers=["55", "24"],
            )
        ),
        "expect": {
            "not_false_negative": True,
            "mentions_other_positions": True,
            "prudence": True,
            "no_jargon": True,
        },
    },
]


def _score_human_case(case: dict) -> dict[str, bool]:
    q = case["question"].lower()
    a = case["answer"]
    low = a.lower()
    exp = case["expect"]
    scores: dict[str, bool] = {}
    if exp.get("answers_question"):
        scores["answers_question"] = bool(a.strip())
    if exp.get("no_tools"):
        scores["no_tools"] = "tool" not in low and "payload" not in low
    if exp.get("no_jargon"):
        scores["no_jargon"] = not any(
            x in low for x in ("payload", "kind consulta", "prompt maestro", "trace", "engine")
        )
    if exp.get("natural"):
        scores["natural"] = "hola" in low or "investig" in low
    if exp.get("both_numbers"):
        scores["both_numbers"] = "55" in a and "24" in a
    if exp.get("all_positions_mentioned"):
        scores["all_positions_mentioned"] = "posiciones" in low or "primera" in low
    if exp.get("has_last"):
        scores["has_last"] = "reciente" in low or "2024" in a or "última" in low or "ultima" in low
    if exp.get("interprets"):
        scores["interprets"] = "interpret" in low or "observ" in low or "conviene" in low
    if exp.get("not_false_negative"):
        scores["not_false_negative"] = "no encontré evidencia" not in low and (
            "coincid" in low or "4" in a
        )
    if exp.get("mentions_other_positions"):
        scores["mentions_other_positions"] = "otras posiciones" in low or "primera posición" in low
    if exp.get("prudence"):
        scores["prudence"] = "pequeña" in low or "regla general" in low or "muestra" in low
    # coverage / continuity proxies
    scores["coverage"] = scores.get("answers_question", True) and scores.get("no_jargon", True)
    scores["clarity"] = len(a) < 2500 and "\n" in a or len(a) < 400
    return scores


def test_human_evaluation_battery():
    all_scores: list[dict[str, bool]] = []
    for case in _HUMAN_CASES:
        scores = _score_human_case(case)
        all_scores.append(scores)
        for k, ok in scores.items():
            assert ok, f"{case['id']} failed criterion {k}: {scores}"

    # Aggregate targets from fase final rubric
    keys = sorted({k for s in all_scores for k in s})
    for key in keys:
        vals = [s[key] for s in all_scores if key in s]
        rate = sum(1 for v in vals if v) / max(len(vals), 1)
        # factual / jargon / coverage must be perfect on this battery
        if key in {"no_jargon", "answers_question", "both_numbers", "not_false_negative", "coverage"}:
            assert rate == 1.0, f"{key} rate {rate}"
        else:
            assert rate >= 0.95, f"{key} rate {rate}"
