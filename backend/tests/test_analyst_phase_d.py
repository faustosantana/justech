"""Fase D — Discovery Engine observational findings (no motor / ranking changes)."""

from __future__ import annotations

from app.lottery.ai.analyst.discovery_engine import (
    DiscoveryEngine,
    DiscoveryRequest,
    FindingValidator,
    get_discovery_engine,
)
from app.lottery.ai.analyst.discovery_store import get_discovery_store
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt, get_motor_prompt
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)


def test_motor_intact_phase_d():
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


def test_prompt_and_research_engine_intact_phase_d():
    from app.lottery.ai.analyst import get_research_engine

    assert get_motor_prompt().version == "v5"
    p = get_active_prompt()
    assert p.version == "v6"
    re = get_research_engine()
    assert re.ENABLED is True
    assert re.VERSION == "2.0"


def test_discovery_findings_published_and_classified():
    get_discovery_store().clear()
    eng = get_discovery_engine()
    assert isinstance(eng, DiscoveryEngine)
    assert eng.ENABLED is True
    result = eng.discover(
        DiscoveryRequest(
            kind="auto_discovery",
            context={
                "period": "2026",
                "investigation_id": "test-inv-1",
                "charts": [
                    {"label": "54", "value": 292},
                    {"label": "94", "value": 235},
                ],
                "lottery_counts": {
                    "Loteria Nacional": 112,
                    "Quiniela Loteka": 118,
                    "Gana Mas": 113,
                },
                "year_counts": {"2025": 200, "2026": 292},
                "position_counts": {"1": 83, "2": 70, "3": 55},
                "confirmation_stats": {"Cash4Life": 2, "Florida Dia": 1, "Anguila": 1},
                "equivalent_case_count": 24,
                "sequence_hits": [{"d": 1}, {"d": 2}, {"d": 3}, {"d": 4}, {"d": 5}, {"d": 6}, {"d": 7}, {"d": 8}],
                "repetition_hits": [{"n": 1}, {"n": 2}, {"n": 3}, {"n": 4}],
                "tools_used": ["lottery_get_number_occurrences"],
            },
        )
    )
    assert result.status == "ok"
    findings = result.payload["findings"]
    assert result.payload["finding_count"] >= 3
    kinds = {f["kind"] for f in findings}
    assert "frequency" in kinds or "lottery_changes" in kinds or "year_changes" in kinds
    for f in findings:
        assert f["level"] in {"Muy Alto", "Alto", "Medio", "Bajo"}
        assert f["status"] == "published"
        blob = f"{f['what']} {f['why']}".lower()
        assert "seguramente" not in blob
        assert "predice" not in blob
        assert "se observ" in blob or "se detect" in blob or "en la muestra" in blob or "en el período" in blob or "en el periodo" in blob
        assert f.get("evidence")
        assert f.get("limitations")


def test_validator_discards_insufficient_and_predictive():
    from app.lottery.ai.analyst.discovery_engine import DiscoveryFinding

    weak = DiscoveryFinding(
        kind="unique_cases",
        title="caso",
        level="Insuficiente",
        what="Se observó 1 caso",
        why="Se detectó rareza",
        evidence={"unique_case_count": 1},
        limitations=[],
        case_count=1,
    )
    ok, reason = FindingValidator.validate(weak)
    assert ok is False
    assert reason == "nivel_insuficiente"

    bad_lang = DiscoveryFinding(
        kind="frequency",
        title="x",
        level="Alto",
        what="Esto sucederá mañana seguramente",
        why="predice el futuro",
        evidence={"total": 30},
        limitations=[],
        case_count=30,
    )
    ok2, reason2 = FindingValidator.validate(bad_lang)
    assert ok2 is False
    assert reason2 == "lenguaje_predictivo"


def test_hypothesis_rejected():
    eng = get_discovery_engine()
    r = eng.discover(DiscoveryRequest(kind="hypothesis"))
    assert r.status == "rejected"
    assert r.payload["findings"] == []


def test_history_persists_published():
    store = get_discovery_store()
    store.clear()
    eng = DiscoveryEngine(store=store)
    eng.discover(
        DiscoveryRequest(
            kind="auto_discovery",
            context={
                "period": "hist",
                "charts": [{"label": "54", "value": 80}],
                "tools_used": ["t1"],
            },
        )
    )
    hist = eng.list_history(limit=20, status="published")
    assert len(hist) >= 1
    assert hist[0]["level"] in {"Muy Alto", "Alto", "Medio", "Bajo"}
