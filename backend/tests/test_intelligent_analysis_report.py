"""Intelligent report assembler — presentation only, no ranking changes."""

from __future__ import annotations

from app.lottery.numeric_relations.analysis_engine.intelligent_report import (
    assemble_intelligent_analysis_report,
)


def _sample_35_14_54() -> dict:
    return {
        "observed_numbers": [35],
        "analysis_date": "2026-06-23",
        "positions": ["first"],
        "primary_signal": {
            "number": 54,
            "classification": "FUERTE_T1_T2_MISMO_DIA",
            "table1_sources": [35],
            "table2_confirmers": [14],
            "same_day_cross_support": True,
            "reason": "technical should not leak",
        },
        "alternatives": [
            {"number": 6, "classification": "FAMILIA_T1"},
            {"number": 11, "classification": "ALTERNATIVA"},
        ],
        "ranked_candidates": [
            {"number": 54, "classification": "FUERTE_T1_T2_MISMO_DIA"},
            {"number": 6, "classification": "FAMILIA_T1"},
            {"number": 7, "classification": "VECINO_T2_DIRECTO"},
        ],
        "same_day_cross": [
            {
                "observed_x": 35,
                "companion_c": 54,
                "confirmer_y": 14,
                "lottery_x": "Lotería Nacional",
                "lottery_y": "Quiniela Loteka",
                "position_x": "primera",
                "position_y": "primera",
            }
        ],
        "historical_evidence": {
            "period_label": "Todo el histórico",
            "metrics": {
                # Engine may report equivalents as evaluable when exact_cases=0 (level-2).
                "exact_cases": 0,
                "evaluable_cases": 120,
                "structural_cases": 120,
                "exact_hits": 96,
                "t1_family_hits": 24,
                "t2_neighbor_hits": 0,
                "d1_hits": 21,
                "d3_hits": 53,
                "d7_hits": 96,
                "recent_cases": [
                    {
                        "date": "2025-06-23",
                        "observed": [35, 14],
                        "candidate": 54,
                        "result": "Candidato exacto",
                        "result_number": 54,
                        "window": "d2",
                    }
                ],
            },
            "evidence_card": {
                "table1_support": True,
                "table2_support": True,
                "same_day_cross_support": True,
                "independent_routes": 6,
                "independent_lotteries": 3,
                "exact_historical_cases": 120,
                "exact_hits": 96,
                "t1_family_hits": 24,
                "t2_neighbor_hits": 0,
                "d1_hits": 21,
                "d3_hits": 53,
                "d7_hits": 96,
            },
            "rival_card": {
                "candidate_number": 7,
                "table1_support": False,
                "table2_support": True,
                "same_day_cross_support": False,
                "exact_historical_cases": 0,
                "independent_routes": 1,
                "independent_lotteries": 1,
            },
            "narrative": {
                "comparison": "El 54 supera al 07 porque posee respaldo de Tabla 1.",
                "warning": "El histórico no garantiza repetición.",
            },
        },
        "explanation": {"summary": "summary", "warning": "warn"},
        "evidence_summary": {"independent_paths": 6},
    }


def test_report_35_14_54_primary_and_metrics():
    report = assemble_intelligent_analysis_report(
        _sample_35_14_54(),
        origin_lottery="Lotería Nacional",
        origin_position="first",
        manual_confirmer=14,
    )
    assert report["primary_candidate"] == 54
    assert report["evidence_level_label"] == "Muy alta"
    assert report["historical_metrics"]["exact_cases"] == 120
    assert report["historical_metrics"]["exact_hits"] == 96
    assert report["historical_metrics"]["t1_family_hits"] == 24
    assert report["historical_metrics"]["d1_hits"] == 21
    assert report["historical_metrics"]["d3_hits"] == 53
    assert report["historical_metrics"]["d7_hits"] == 96
    assert report["historical_sample_quality"]["label"] == "Muestra histórica amplia"
    assert "80" not in (report["brief_conclusion"] or "")
    assert "probabilidad" not in (report["brief_conclusion"] or "").lower()
    assert "FUERTE_" not in str(report)
    assert "primary_signal" not in str(report)
    assert report["candidate_comparison"][0]["number"] == 54
    assert report["candidate_comparison"][0]["table1_support"] is True
    rival = next(c for c in report["candidate_comparison"] if c["number"] == 7)
    assert rival["table1_support"] is False
    assert any(s["title"] == "Selección final" for s in report["reasoning_timeline"])
    assert report["confirmer"]["number"] == 14
    assert "Quiniela Loteka" in (report["confirmer"]["lottery"] or "")


def test_report_does_not_change_when_ranking_fields_present():
    raw = _sample_35_14_54()
    raw["alternatives"] = [
        {"number": 7, "classification": "VECINO_T2_DIRECTO"},
        {"number": 11, "classification": "ALTERNATIVA"},
    ]
    raw["ranked_candidates"] = [
        {"number": 54, "total_score": 999},
        {"number": 7, "total_score": 1},
    ]
    report = assemble_intelligent_analysis_report(raw, origin_lottery="Lotería Nacional")
    assert report["primary_candidate"] == 54
    assert report["alternatives"][0] == 7
    assert "120 casos" in (report["comparison_explanation"] or "")
    assert any(s["title"] == "Revisión histórica" for s in report["reasoning_timeline"])
