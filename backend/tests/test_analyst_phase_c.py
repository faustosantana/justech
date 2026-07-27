"""Fase C — Analyst Experience (response presentation only; motor untouched)."""

from __future__ import annotations

from app.lottery.ai.analyst.response_formatter import (
    format_analyst_response,
    format_delta_response,
    format_professional_response,
    format_short_response,
    render_bar,
    render_ranking_bars,
    select_response_mode,
)
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)


def test_motor_intact_phase_c():
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


def test_prompt_maestro_intact_phase_c():
    p = get_active_prompt()
    assert p.version == "v5"


def test_ascii_bars():
    block = render_bar("54", 3467, max_value=3467)
    assert "54" in block
    assert "█" in block
    assert "3467" in block
    ranking = render_ranking_bars([("54", 3467), ("94", 2137), ("Loteka", 118)])
    assert "94" in ranking
    assert ranking.index("54") < ranking.index("94")


def test_professional_structure_separates_layers():
    text = format_professional_response(
        "Cash4Life confirmó primero el destino 54.",
        facts={"primary": 54, "observed": 35, "confirmer": 14},
        research={
            "question_kind": "which_lottery_confirms_first",
            "steps_completed": ["confirm_lottery_scan", "confirm_combinations"],
            "confidence": "Media",
        },
        evidence_package={
            "case_count": 4,
            "criterion": "primera aparición del destino en ≤3 días",
            "period": "6 casos Nacional+Loteka",
            "tools_used": ["lottery_get_number_occurrences"],
            "evidence_level": "Media",
            "findings": ["Cash4Life primero en 2 de 4 casos con hit"],
            "comparisons": ["Cash4Life 2; otras 1"],
            "related_suggestions": ["¿Filtro solo quinielas RD?"],
            "limitations": [],
        },
        mode="report",
    )
    for header in (
        "Resumen Ejecutivo",
        "Hallazgos Principales",
        "HECHOS",
        "ANÁLISIS",
        "OBSERVACIONES",
        "Evidencias",
        "Limitaciones",
        "Próximas investigaciones sugeridas",
    ):
        assert header in text
    assert "cuántas" in text.lower() or "caso" in text.lower()
    assert "no significa" in text.lower() or "No significa" in text
    assert "INFORME DE INVESTIGACIÓN" in text
    # Facts vs analysis markers present and ordered
    assert text.index("HECHOS") < text.index("ANÁLISIS") < text.index("OBSERVACIONES")


def test_adaptive_modes():
    short = select_response_mode(
        text="El 54 salió 10 veces.",
        facts={"observed": 54},
        research={},
        evidence_package={},
        is_follow_up=False,
        force_structure=False,
    )
    assert short == "short"

    report = select_response_mode(
        text="Comparación amplia",
        facts={},
        research={
            "question_kind": "compare_numbers",
            "steps_completed": ["a", "b", "c", "d", "e", "f", "g"],
        },
        evidence_package={"case_count": 80, "comparisons": ["x", "y"]},
        is_follow_up=False,
        force_structure=True,
    )
    assert report == "report"

    delta = select_response_mode(
        text="solo 2026",
        facts={},
        research={"question_kind": "filtered_follow_up"},
        evidence_package={"case_count": 10},
        is_follow_up=True,
        force_structure=True,
    )
    assert delta == "delta"


def test_follow_up_delta_does_not_repeat_full_report_title():
    text = format_analyst_response(
        "En 2026 el 54 tuvo 292 apariciones frente a 235 del 94.",
        facts={"observed": 54, "charts": [{"label": "54", "value": 292}, {"label": "94", "value": 235}]},
        research={
            "question_kind": "compare_numbers",
            "confidence": "Media",
            "evidence_package": {
                "case_count": 292,
                "criterion": "conteo 2026",
                "period": "2026",
                "tools_used": ["lottery_get_number_occurrences"],
                "evidence_level": "Media",
                "findings": ["54: 292", "94: 235"],
            },
        },
        question="Ahora solo durante 2026. ¿Cuál de los dos tuvo mayor evidencia?",
        conversation_context={"has_prior_research": True},
    )
    assert "solo lo nuevo" in text.lower() or "Actualización" in text or "Sobre tu pregunta" in text
    assert "INFORME DE INVESTIGACIÓN" not in text
    assert "█" in text
    assert "Similitudes" in text or "Evidencias" in text


def test_comparisons_have_three_parts():
    text = format_professional_response(
        "El 54 supera al 94 en volumen 2026.",
        facts={"observed": 54, "compare_with": 94, "charts": [{"label": "54", "value": 292}, {"label": "94", "value": 235}]},
        research={"question_kind": "compare_numbers", "research_meta": {"subjects": ["54", "94"]}},
        evidence_package={
            "case_count": 527,
            "criterion": "apariciones 2026",
            "period": "2026",
            "tools_used": ["lottery_get_number_occurrences"],
            "evidence_level": "Alta",
            "comparisons": ["54 tiene más apariciones que 94 en 2026"],
            "findings": ["54: 292", "94: 235"],
        },
        mode="full",
    )
    assert "Similitudes" in text
    assert "Diferencias" in text
    assert "Conclusiones" in text


def test_short_response_is_compact():
    text = format_short_response(
        "El 54 apareció 683 veces en primera posición.",
        facts={"observed": 54},
        evidence_package={"case_count": 683, "evidence_level": "Media", "criterion": "posición=1"},
    )
    assert "Resumen Ejecutivo" in text
    assert "HECHOS" in text
    assert "INFORME DE INVESTIGACIÓN" not in text
