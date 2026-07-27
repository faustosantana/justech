"""Data integrity for last-occurrence — no stale pair/lottery leakage."""

from __future__ import annotations

from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.evidence_engine import EvidenceEngine
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier
from app.lottery.ai.analyst.response_formatter import format_analyst_response
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.nlp_stability import is_complete_standalone
from app.services.lottery_ai_contracts import LotteryToolName


def _stale_same_day_state() -> ConversationState:
    return ConversationState(
        active_numbers=["55", "24"],
        active_pair=["55", "24"],
        active_relation="same_day",
        active_lotteries=["Lotería Nacional"],
        last_analysis={
            "observed": "55",
            "confirmer": "24",
            "lottery": "Lotería Nacional",
            "date": "2024-01-15",
        },
        current_primary_candidate=54,
    )


def test_last_occurrence_does_not_reuse_stale_pair_for_22_35_97():
    st = _stale_same_day_state()
    planned_numbers: list[str] = []
    for q, expected in (
        ("¿Cuándo salió por última vez el 22?", "22"),
        ("¿Cuándo salió por última vez el 35?", "35"),
        ("¿Cuándo salió por última vez el 97?", "97"),
    ):
        resolution = IntentResolver.resolve(q, st)
        assert resolution.get("numbers") == [expected]
        assert resolution.get("follow_up_kind") == "last_occurrence"
        assert resolution.get("use_active_pair") is False

        brain = ConversationBrain(st)
        st = brain.apply_resolution(
            understanding=UnderstandingResult(
                intent="last_occurrence",
                numbers=[expected],
                confidence=0.9,
            ),
            resolution=resolution,
        )
        assert st.active_numbers == [expected]
        assert not st.active_pair

        rq = QuestionClassifier.classify(q, st, resolution)
        assert rq is not None and rq.kind == "last_times"
        assert rq.params.get("numbers") == [expected]

        steps, meta = DynamicResearchPlanner.build(rq, st)
        assert meta.get("subjects") == [expected]
        nums = [
            str(s.params.get("number") or s.params.get("observed_number"))
            for s in steps
            if s.params.get("number") is not None or s.params.get("observed_number") is not None
        ]
        assert nums, f"no number params for {q}"
        assert all(n == expected for n in nums), (q, nums)
        assert LotteryToolName.RUN_COMPLETE_ANALYSIS.value not in [s.tool for s in steps]
        assert any(
            s.tool
            in {
                LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                LotteryToolName.GET_LAST_OCCURRENCE.value,
            }
            for s in steps
        )
        planned_numbers.append(expected)

    assert planned_numbers == ["22", "35", "97"]
    assert len(set(planned_numbers)) == 3


def test_standalone_ultima_vez_is_complete():
    assert is_complete_standalone("¿Cuándo salió por última vez el 22?")
    assert is_complete_standalone("Cuándo salió por última vez el 97")


def test_evidence_count_not_zero_with_last_date():
    pkg = EvidenceEngine.assemble(
        kind="last_times",
        tool_trace=[{"tool": "lottery_get_last_occurrence", "status": "success"}],
        evidence_bundle=[
            {
                "purpose": "last_occurrence",
                "tool": "lottery_get_last_occurrence",
                "summary": {
                    "semantics": "last_occurrence",
                    "number": "22",
                    "lottery": "Loteka",
                    "last_occurrence_date": "2025-03-01",
                    "position": "1",
                    "total": 12,
                    "count": 12,
                    "found": True,
                },
            }
        ],
    )
    d = pkg.to_dict()
    assert d["case_count"] and int(d["case_count"]) > 0
    assert any("2025-03-01" in t for t in (d.get("timeline") or []))

    text = format_analyst_response(
        "La última aparición del 22 fue el 2025-03-01 en Loteka.",
        facts={
            "observed": "22",
            "lottery": "Loteka",
            "last_occurrence_date": "2025-03-01",
            "total": 12,
        },
        research={
            "question_kind": "last_times",
            "evidence_package": d,
            "evidence": [
                {
                    "summary": {
                        "number": "22",
                        "lottery": "Loteka",
                        "last_occurrence_date": "2025-03-01",
                        "count": 12,
                    }
                }
            ],
        },
    )
    assert "22" in text
    assert "55" not in text
    assert "Loteka" in text
    assert "Cantidad de casos/registros: 0" not in text
    assert "Registros consultados: 0" not in text
    # Positive count must appear when evidence has total>0
    assert "12" in text


def test_evidence_zero_without_date_omits_fake_zero_display_when_unknown():
    pkg = EvidenceEngine.assemble(
        kind="last_times",
        tool_trace=[{"tool": "x", "status": "success"}],
        evidence_bundle=[
            {
                "purpose": "noop",
                "tool": "x",
                "summary": {"semantics": "empty"},
            }
        ],
    )
    d = pkg.to_dict()
    # Unknown count should not invent a contradictory date
    assert not d.get("timeline")
    text = format_analyst_response(
        "Sin apariciones en el alcance consultado.",
        facts={"observed": "22"},
        research={"question_kind": "last_times", "evidence_package": d},
    )
    assert "Cantidad de casos/registros: 0" not in text or "última" not in text.lower()


def test_formatter_lottery_matches_facts_not_stale_nacional():
    from app.lottery.ai.analyst.response_formatter import _hechos_block

    facts = {
        "observed": "35",
        "lottery": "Loteka",
        "last_occurrence_date": "2024-11-02",
        "total": 4,
    }
    pkg = {
        "case_count": 4,
        "timeline": ["Última ancla: 2024-11-02 (Loteka)."],
        "findings": ["Número consultado: 35."],
        "tools_used": ["lottery_compare_number_across_lotteries"],
        "evidence_level": "Media",
    }
    block = _hechos_block(facts, pkg, {"question_kind": "last_times"}, compact=False) or ""
    assert "Número observado: 35" in block
    assert "Lotería activa: Loteka" in block
    assert "Número observado: 55" not in block
    assert "Lotería Nacional" not in block
    assert "Cantidad de casos/registros: 0" not in block
    assert "Cantidad de casos/registros: 4" in block

    text = format_analyst_response(
        "La última aparición del 35 en Loteka fue el 2024-11-02.",
        facts=facts,
        research={"question_kind": "last_times", "evidence_package": pkg},
    )
    assert "35" in text and "Loteka" in text
    assert "55" not in text
    assert "Cantidad de casos/registros: 0" not in text
