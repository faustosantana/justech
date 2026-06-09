"""Tests — cumplimiento real del expediente DGCP (Fase 7.3 fix)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_compliance_engine import COMPLIANT_STATUSES, DGCPComplianceEngine
from app.services.dgcp_requirements_extractor import DEFAULT_LICITACION_DOCS, ExtractedRequirement, ExtractionResult


def _opportunity() -> DGCPOpportunity:
    return DGCPOpportunity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="MINERD-DAF-CM-2026-0080",
        institution="MINERD",
        title="Adquisición equipos",
        amount=Decimal("500000"),
        deadline=date(2026, 12, 31),
        description="Se requiere RPE, DGII y registro mercantil.",
        full_info={},
        raw_payload={},
    )


def test_collect_all_requirements_includes_baseline_and_extracted():
    engine = DGCPComplianceEngine()
    extraction = ExtractionResult(
        mandatory_documents=[
            ExtractedRequirement(key="rpe", label="RPE vigente", tipo="legal"),
            ExtractedRequirement(key="certificacion_dgii", label="Certificación DGII", tipo="legal"),
            ExtractedRequirement(key="registro_mercantil", label="Registro Mercantil", tipo="legal"),
        ],
        sncc_forms=["SNCC.F.042", "SNCC.F.047"],
        guarantees=["Garantía de seriedad de oferta"],
        samples=["Muestras físicas solicitadas en pliego"],
    )
    all_reqs = engine.collect_all_requirements(extraction)
    keys = {r.key for r in all_reqs}
    assert "rpe" in keys
    assert "certificacion_tss" in keys
    assert "oferta_tecnica" in keys
    assert "oferta_economica" in keys
    assert "sncc_f042" in keys
    assert "sncc_f047" in keys
    assert any(k.startswith("garantia_") for k in keys)
    assert any(k.startswith("muestra_") for k in keys)
    assert len(all_reqs) >= 10


def test_preparation_not_100_when_only_three_legal_docs_found():
    engine = DGCPComplianceEngine()
    opp = _opportunity()
    requirements = engine.collect_all_requirements(
        ExtractionResult(
            mandatory_documents=[
                ExtractedRequirement(key="rpe", label="RPE vigente", tipo="legal"),
                ExtractedRequirement(key="certificacion_dgii", label="Certificación DGII", tipo="legal"),
                ExtractedRequirement(key="registro_mercantil", label="Registro Mercantil", tipo="legal"),
            ],
        )
    )
    matches = []
    for req in requirements:
        if req.key in ("rpe", "certificacion_dgii", "registro_mercantil"):
            matches.append({
                "requirement_key": req.key,
                "status": "encontrado",
                "vigency_status": "sin_fecha",
                "match_score": 90,
            })
        else:
            matches.append({"requirement_key": req.key, "status": "pendiente", "match_score": 0})

    checklist = engine.build_checklist(
        requirements,
        matches,
        sncc_form_map={"sncc_f042": "SNCC.F042", "sncc_f047": "SNCC.F047"},
    )
    bid = engine.build_bid_package(opp, checklist)

    assert bid.preparation_pct < 100
    assert bid.total_requirements >= len(DEFAULT_LICITACION_DOCS)
    assert bid.pending_documents + (bid.review_count or 0) > 0
    assert bid.compliant_count < bid.mandatory_requirements
    assert not engine.can_mark_ready_for_review(checklist)


def test_sin_fecha_no_counts_as_compliant():
    engine = DGCPComplianceEngine()
    status = engine.normalize_status(
        "encontrado_sin_fecha",
        vigency_status="sin_fecha",
        requirement_key="certificacion_tss",
    )
    assert status == "encontrado_sin_fecha"
    assert status not in COMPLIANT_STATUSES
    manual = engine.normalize_status("validado_manual")
    assert manual in COMPLIANT_STATUSES
    rpe = engine.normalize_status(
        "encontrado",
        vigency_status="sin_fecha",
        requirement_key="rpe",
    )
    assert rpe == "encontrado_vigente"


def test_vigente_counts_as_compliant():
    engine = DGCPComplianceEngine()
    status = engine.normalize_status("encontrado", vigency_status="vigente")
    assert status == "encontrado_vigente"
    assert status in COMPLIANT_STATUSES


def test_checklist_counts_reflect_all_statuses():
    engine = DGCPComplianceEngine()
    checklist = [
        {"mandatory": True, "status": "encontrado_vigente", "document_id": "doc-1"},
        {"mandatory": True, "status": "faltante"},
        {"mandatory": True, "status": "requiere_completado"},
        {"mandatory": True, "status": "encontrado_sin_fecha"},
    ]
    counts = engine.checklist_counts(checklist)
    assert counts["total"] == 4
    assert counts["compliant_count"] == 1
    assert counts["pending_count"] == 1
    assert counts["incomplete_count"] == 1
    assert counts["review_count"] == 1


def test_oferta_tecnica_without_document_is_faltante_not_compliant():
    engine = DGCPComplianceEngine()
    req = ExtractedRequirement(
        key="oferta_tecnica",
        label="Oferta técnica",
        tipo="tecnico",
        mandatory=True,
    )
    match = {
        "requirement_key": "oferta_tecnica",
        "status": "encontrado_vigente",
        "match_score": 85,
    }
    item = engine.build_checklist_item(req, match, sncc_form_map={})
    assert item["status"] == "faltante"
    assert item["status"] not in COMPLIANT_STATUSES

    prev = {"manual_validation": {"status": "validado_manual", "note": "QA stale"}}
    stale = engine.build_checklist_item(req, match, prev=prev, sncc_form_map={})
    assert stale["status"] == "faltante"


def test_validado_manual_without_document_not_counted_in_preparation():
    engine = DGCPComplianceEngine()
    opp = _opportunity()
    checklist = [
        {
            "mandatory": True,
            "status": "validado_manual",
            "requirement": "Oferta técnica",
            "requirement_key": "oferta_tecnica",
        },
        {"mandatory": True, "status": "faltante", "requirement": "Oferta económica"},
    ]
    bid = engine.build_bid_package(opp, checklist)
    assert bid.compliant_count == 0
    assert bid.preparation_pct < 100


def test_analysis_warning_when_no_pliego():
    engine = DGCPComplianceEngine()
    warnings = engine.build_analysis_warnings(
        [{"title": "[Corpus legal] RPE", "doc_role": "legal", "has_text": True, "source_type": "knowledge_copy"}],
        ExtractionResult(),
    )
    assert any("pliego" in w.lower() for w in warnings)


@pytest.mark.asyncio
async def test_analyze_endpoint_not_100_with_partial_docs():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@justech.do",
                "password": "JaiosAdmin2026!",
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        list_res = await client.get("/api/v1/dgcp/opportunities?limit=5", headers=headers)
        if not list_res.json().get("items"):
            pytest.skip("Sin oportunidades")

        opp_id = list_res.json()["items"][0]["id"]
        from tests.dgcp_test_helpers import analyze_with_interest

        analyze = await analyze_with_interest(client, opp_id, headers)
        assert analyze.status_code == 200, analyze.text
        body = analyze.json()
        bid = body["bid_package"]
        checklist = body["checklist"]

        assert checklist["total"] >= len(DEFAULT_LICITACION_DOCS)
        assert checklist["mandatory_total"] >= len(DEFAULT_LICITACION_DOCS)
        if checklist["compliant_count"] < checklist["mandatory_total"]:
            assert bid["preparation_pct"] < 100
        assert checklist["compliant_count"] <= checklist["mandatory_total"]
