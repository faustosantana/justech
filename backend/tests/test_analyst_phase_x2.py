"""Fase X.2 — Madurez analítica y UX conversacional (v2.3.3)."""

from __future__ import annotations

from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.analyst.response_formatter import (
    format_analyst_response,
    select_response_mode,
)
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt, get_motor_prompt
from app.lottery.ai.same_day_coincidence import (
    analyzing_label,
    coincidence_suggestions,
    format_coincidence_narrative,
    parse_same_day_coincidence,
    summarize_coincidences,
)
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent
from app.lottery.ai.understanding import understand


def test_motor_intact_phase_x2():
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


def test_engines_intact_phase_x2():
    from app.lottery.ai.analyst import (
        get_discovery_engine,
        get_knowledge_engine,
        get_research_engine,
    )

    assert get_motor_prompt().version == "v5"
    assert get_active_prompt().version == "v6"
    assert get_research_engine().VERSION == "2.0"
    assert get_discovery_engine().ENABLED is True
    assert get_knowledge_engine().version == "2.3.0"


def test_case1_same_day_extracts_both_all_positions():
    q = "¿Han salido alguna vez el 55 y el 24 el mismo día?"
    parsed = parse_same_day_coincidence(q)
    assert parsed is not None
    assert parsed["numbers"] == ["55", "24"]
    assert parsed["active_relation"] == "same_day"
    assert parsed["position_scope"] == "any_position"
    assert parsed["position"] is None
    assert parsed["preferred_position"] == 1

    r = resolve_intent(q, LotterySessionContext())
    assert r.kind == "tool"
    assert r.tool == LotteryToolName.GET_NUMBER_OCCURRENCES
    assert r.params.get("numbers") == ["55", "24"]
    assert r.params.get("relation") == "same_day"
    assert r.params.get("position") is None

    u, _ = understand(q, ConversationState())
    assert set(u.numbers) >= {"55", "24"}
    assert u.params.get("relation") == "same_day"


def test_case2_first_position_keeps_pair():
    state = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        position_scope="any_position",
        preferred_position=1,
    )
    u, st = understand("¿Y en primera posición?", state)
    assert set(u.numbers) >= {"55", "24"}
    assert u.params.get("position") == 1
    assert u.params.get("relation") == "same_day"
    assert st.active_relation == "same_day"
    assert "55" in st.active_numbers and "24" in st.active_numbers


def test_case3_any_position_restores_all():
    state = ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        position_scope="first_position",
        preferred_position=1,
    )
    u, st = understand("¿Y en cualquier posición?", state)
    assert u.params.get("position") is None
    assert u.params.get("position_scope") == "any_position"
    assert set(u.numbers) >= {"55", "24"}
    assert st.position_scope == "any_position"


def test_case4_last_coincidence_keeps_relation():
    ctx = LotterySessionContext(last_numbers=["55", "24"])
    r = resolve_intent("¿Cuál fue la última coincidencia?", ctx)
    assert r.kind == "tool"
    assert r.params.get("relation") == "same_day"
    assert r.params.get("numbers") == ["55", "24"]
    assert r.params.get("want_last_only") is True


def test_case5_full_analyze_report_mode():
    q = "Analiza completamente el 55 y el 24."
    mode = select_response_mode(
        text="Informe amplio",
        facts={},
        research={"question_kind": "open_investigation"},
        evidence_package={"case_count": 12},
        is_follow_up=False,
        force_structure=True,
        question=q,
    )
    assert mode == "report"
    r = resolve_intent(q, LotterySessionContext())
    # Complete analysis path OR same-day with report — either ok if not simple short
    assert r.kind == "tool"
    simple = select_response_mode(
        text="Sí. Coincidieron 3 veces.",
        facts={},
        research={"relation": "same_day"},
        evidence_package={"relation": "same_day", "case_count": 3},
        is_follow_up=False,
        force_structure=True,
        question="¿Han salido el 55 y el 24 el mismo día?",
    )
    assert simple == "short"


def test_case6_zero_first_but_positive_elsewhere():
    payload = {
        "total": 7,
        "items": [
            {
                "date": "2024-01-10",
                "appearances": [
                    {"number": "55", "lottery": "Leidsa", "position": 2, "position_label": "2"},
                    {"number": "24", "lottery": "Loteka", "position": 3, "position_label": "3"},
                ],
            }
        ]
        * 7,
    }
    summary = summarize_coincidences(
        payload, numbers=["55", "24"], preferred_position=1, position_filter=None
    )
    assert summary["total"] == 7
    assert summary["first_related"] == 0
    assert summary["other_only"] == 7
    text = format_coincidence_narrative(summary)
    assert "No aparecieron juntos en primera posición" in text or "otras posiciones" in text.lower()
    assert "7" in text
    assert "No encontré evidencia" not in text
    assert "no existe evidencia" not in text.lower()


def test_brain_stores_compound_relation():
    state = ConversationState()
    brain = ConversationBrain(state)
    understanding = UnderstandingResult(
        intent="cross_lottery_matches",
        numbers=["55", "24"],
        params={"relation": "same_day", "position_scope": "any_position"},
    )
    st = brain.apply_resolution(
        understanding=understanding,
        resolution={
            "numbers": ["55", "24"],
            "active_relation": "same_day",
            "relation": "same_day",
            "position_scope": "any_position",
            "preferred_position": 1,
        },
    )
    assert st.active_numbers == ["55", "24"]
    assert st.active_relation == "same_day"
    assert st.position_scope == "any_position"
    assert st.preferred_position == 1
    # remember_analysis must not collapse pair
    st2 = ConversationBrain(st).remember_analysis({"observed": 55, "primary": 7})
    assert len(st2.active_numbers) >= 2
    assert "55" in st2.active_numbers and "24" in st2.active_numbers


def test_narrative_no_technical_jargon():
    text = format_analyst_response(
        "Sí. El 55 y el 24 coincidieron el mismo día en 3 ocasiones.",
        facts={},
        research={"relation": "same_day"},
        question="¿Han salido el 55 y el 24 el mismo día?",
    )
    low = text.lower()
    assert "kind" not in low
    assert "payload" not in low
    assert "prompt maestro" not in low
    assert "no se recomienda apostar" not in low
    assert "hechos" not in low or "coincidieron" in low
    assert "limitaciones" not in low


def test_suggestions_and_analyzing_label_compound():
    sug = coincidence_suggestions(["55", "24"])
    assert any("coincidencia" in s.lower() or "posición" in s.lower() for s in sug)
    assert not any(s.lower().startswith("analiza el 55") for s in sug)
    assert "55 + 24" in analyzing_label(["55", "24"]) or "55 y 24" in analyzing_label(
        ["55", "24"], relation="same_day"
    )


def test_negative_zero_message_is_complete():
    summary = summarize_coincidences(
        {"total": 0, "items": [], "all_lotteries": True},
        numbers=["55", "24"],
        position_filter=None,
    )
    text = format_coincidence_narrative(summary)
    assert "todas las loterías" in text.lower()
    assert "todas las posiciones" in text.lower()
    assert "55" in text and "24" in text
