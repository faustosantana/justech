"""Fase E — Knowledge Engine verified investigation repository (no motor changes)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.lottery.ai.analyst.knowledge_engine import (
    KnowledgeEngine,
    KnowledgeSaveRequest,
    KnowledgeSearchQuery,
    get_knowledge_engine,
)
from app.lottery.ai.analyst.knowledge_store import KnowledgeStore
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt, get_motor_prompt
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)


def _fresh_engine(tmp: Path) -> KnowledgeEngine:
    store = KnowledgeStore(path=tmp / "knowledge.json")
    store.set_current_historical_version("history-v-test-1")
    return KnowledgeEngine(store=store)


def test_motor_intact_phase_e():
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


def test_prompt_research_discovery_intact_phase_e():
    from app.lottery.ai.analyst import get_discovery_engine, get_research_engine

    assert get_motor_prompt().version == "v5"
    p = get_active_prompt()
    assert p.version == "v6"
    re = get_research_engine()
    assert re.ENABLED is True
    assert re.VERSION == "2.0"
    disc = get_discovery_engine()
    assert disc.ENABLED is True
    assert getattr(disc, "VERSION", "2.2.0") == "2.2.0"


def test_reject_conclusions_only_and_insufficient_evidence():
    with tempfile.TemporaryDirectory() as td:
        eng = _fresh_engine(Path(td))
        bad = eng.save(
            KnowledgeSaveRequest(
                original_question="¿Qué pasa con 54?",
                executive_summary="Solo una conclusión",
                full_investigation="",
                evidences=[],
                finished_ok=True,
            )
        )
        assert bad["saved"] is False
        assert any("evidencia" in r.lower() for r in bad["reasons"])

        discarded = eng.save(
            KnowledgeSaveRequest(
                original_question="x",
                executive_summary="y",
                full_investigation="z",
                evidences=[{"n": 1}],
                discarded=True,
            )
        )
        assert discarded["saved"] is False


def test_save_search_favorites_collections_related_citations():
    with tempfile.TemporaryDirectory() as td:
        eng = _fresh_engine(Path(td))
        r1 = eng.save(
            KnowledgeSaveRequest(
                title="Ocurrencias del 54",
                original_question="¿Cuántas veces salió el 54?",
                executive_summary="El 54 aparece con evidencia histórica.",
                full_investigation="Investigación completa del 54 con conteos y posiciones.",
                evidences=[{"source": "sql", "count": 3467, "number": "54"}],
                tools_used=["lottery_get_number_occurrences"],
                evidence_level="Alto",
                confidence="Alta",
                tags=["Confirmaciones"],
                numbers=["54"],
                years=[2026],
                historical_version="history-v-test-1",
            )
        )
        assert r1["saved"] is True
        id1 = r1["investigation"]["id"]

        r2 = eng.save(
            KnowledgeSaveRequest(
                title="Comparación 54 vs 94",
                original_question="Compara 54 vs 94 en 2026",
                executive_summary="Comparación con evidencia.",
                full_investigation="54 vs 94 durante 2026 con conteos.",
                evidences=[{"source": "sql", "a": 292, "b": 235}],
                tools_used=["lottery_compare"],
                tags=["Comparaciones"],
                numbers=["54", "94"],
                pairs=[["54", "94"]],
                years=[2026],
                cited_ids=[id1],
                historical_version="history-v-test-1",
            )
        )
        assert r2["saved"] is True
        id2 = r2["investigation"]["id"]
        assert id1 in r2["investigation"]["cited_ids"]
        assert "[CITA]" in r2["investigation"]["full_investigation"] or id1 in r2["investigation"]["cited_ids"]

        # Ensure cite annotation present
        cited = eng.cite(id2, id1)
        assert cited is not None
        assert "[CITA]" in cited["full_investigation"]

        search = eng.search(KnowledgeSearchQuery(number="54", year=2026))
        assert search["count"] >= 2

        pair_search = eng.search(KnowledgeSearchQuery(pair=["54", "94"]))
        assert pair_search["count"] >= 1

        kw = eng.search(KnowledgeSearchQuery(keyword="comparación"))
        assert kw["count"] >= 1

        fav = eng.set_favorite(id1, True)
        pin = eng.set_pinned(id1, True)
        assert fav["favorite"] is True
        assert pin["pinned"] is True

        cols = eng.list_collections()
        names = {c["name"] for c in cols}
        assert "Confirmaciones" in names
        assert "Comparaciones" in names

        chain = eng.related_chain(id1)
        assert chain["found"] is True
        assert any(x["id"] == id2 for x in chain["related"]) or id2 in (eng.get(id1) or {}).get("related_ids", [])


def test_obsolescence_on_historical_version_change():
    with tempfile.TemporaryDirectory() as td:
        eng = _fresh_engine(Path(td))
        saved = eng.save(
            KnowledgeSaveRequest(
                title="54 histórico",
                original_question="54",
                executive_summary="Resumen con evidencia",
                full_investigation="Cuerpo completo",
                evidences=[{"ok": True}],
                numbers=["54"],
                historical_version="history-v-test-1",
            )
        )
        assert saved["saved"] is True
        iid = saved["investigation"]["id"]
        eng.set_historical_version("history-v-test-2")
        got = eng.get(iid)
        assert got is not None
        assert got["obsolete"] is True
        assert "versión anterior del histórico" in (got.get("obsolescence_banner") or got.get("obsolete_reason") or "")


def test_export_stub_not_generating():
    with tempfile.TemporaryDirectory() as td:
        eng = _fresh_engine(Path(td))
        saved = eng.save(
            KnowledgeSaveRequest(
                title="export",
                original_question="q",
                executive_summary="s",
                full_investigation="f",
                evidences=[{"e": 1}],
            )
        )
        plan = eng.export_plan(saved["investigation"]["id"], "pdf")
        assert plan["implemented"] is False
        assert plan["accepted"] is True
        assert "markdown" in plan["supported_planned"]


def test_version_fields_present():
    with tempfile.TemporaryDirectory() as td:
        eng = _fresh_engine(Path(td))
        saved = eng.save(
            KnowledgeSaveRequest(
                title="versiones",
                original_question="q",
                executive_summary="s",
                full_investigation="full",
                evidences=[{"e": 1}],
                historical_version="history-v-test-1",
            )
        )
        inv = saved["investigation"]
        assert inv["motor_version"]
        assert inv["historical_version"] == "history-v-test-1"
        assert inv["prompt_maestro_version"] == "v5"
        assert inv["research_engine_version"] == "2.0"
        assert inv["discovery_engine_version"] == "2.2.0"
        assert inv["knowledge_engine_version"] == "2.3.0"
        assert inv["author"] == "Analista IA"


def test_singleton_status():
    st = get_knowledge_engine().status()
    assert st["enabled"] is True
    assert st["version"] == "2.3.0"
    assert st["not_ml"] is True
    assert st["export_generation_implemented"] is False
