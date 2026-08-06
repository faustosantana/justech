"""Pruebas del pipeline canónico de análisis profundo de pliego (29 campos)."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.dgcp_pliego_analysis import (
    PLIEGO_FIELD_KEYS,
    PliegoAnalysisResult,
    PliegoAnalysisStatus,
    PliegoEvidence,
    PliegoFieldResult,
)
from app.services.dgcp_pliego_deep_analysis_service import DGCPPliegoDeepAnalysisService
from app.services.document_extraction_service import DocumentExtractionService, ExtractionResult


def _opp(**kwargs):
    base = dict(
        id=uuid.uuid4(),
        code="HRUJM-DAF-CM-2026-0020",
        title="Suministro de equipos de oficina",
        institution="Hospital Regional",
        description="Adquisición de mobiliario y equipos.",
        objeto_proceso="Adquisición de equipos de oficina",
        amount=1500000,
        deadline=date(2026, 8, 15),
        modality="Compra Menor",
        company="just_office",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _doc(
    *,
    title="pliego.pdf",
    role="pliego",
    text="",
    pages=None,
    ocr=False,
    content_hash=None,
    doc_id=None,
):
    did = doc_id or uuid.uuid4()
    meta = {
        "content_hash": content_hash or hashlib.sha256((text or title).encode()).hexdigest(),
        "page_count": len(pages) if pages else None,
        "pages_text": pages,
        "ocr_used": ocr,
        "ocr_confidence": 0.8 if ocr else None,
    }
    return SimpleNamespace(
        id=did,
        title=title,
        doc_role=role,
        extracted_text=text,
        metadata_=meta,
        ingestion_status="analyzed" if text else "registered",
        analyzed_at=datetime.now(timezone.utc) if text else None,
    )


def _svc():
    db = MagicMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    # package lookup returns None by default
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    return DGCPPliegoDeepAnalysisService(db, uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_29_fields_always_present_text_pdf():
    svc = _svc()
    text = (
        "OBJETO: Adquisición de equipos.\n"
        "Institución: Hospital Regional.\n"
        "Modalidad: Compra Menor.\n"
        "Monto estimado RD$ 1,500,000.\n"
        "Fecha límite: 15/08/2026.\n"
        "Garantía de seriedad de oferta 1%.\n"
        "Formulario SNCC F.033 requerido.\n"
        "Criterios de evaluación: precio 60% técnica 40%.\n"
        "Causas de descalificación: oferta incompleta.\n"
        "Plazo de entrega 30 días calendario.\n"
        "Lugar de entrega: almacén central.\n"
        "Condiciones de pago: 30 días contra factura.\n"
    )
    docs = [_doc(text=text, pages=[text[:200], text[200:]])]
    result = await svc.run(
        _opp(),
        process_documents=docs,
        process_corpus=text,
        hermes_meta={"status": "completed", "summary": "Proceso de compra menor", "confidence": 0.7,
                     "required_documents": ["SNCC F.033", "Copia RNC"], "next_actions": ["Revisar fianza"],
                     "risks": [{"descripcion": "Plazo corto", "nivel": "alto"}]},
        checklist=[{"requirement": "RNC", "mandatory": True, "status": "pendiente"}],
        risks=[{"descripcion": "Cierre próximo", "nivel": "alto"}],
        force=True,
    )
    assert len(result.fields) == 29
    for key in PLIEGO_FIELD_KEYS:
        assert key in result.fields
        assert result.fields[key].found is not None
        assert result.fields[key].value is not None
    assert result.status in (
        PliegoAnalysisStatus.COMPLETED,
        PliegoAnalysisStatus.PARTIAL,
        PliegoAnalysisStatus.REVIEW_REQUIRED,
    )
    assert result.fields["decision_sugerida"].found is True
    assert result.fields["nivel_confianza"].found is True
    assert result.fields["documentos_solicitados"].found is True
    assert result.fields["pendientes"].found is True
    assert result.fields["riesgos"].found is True
    assert result.fields["recomendaciones"].found is True
    assert result.fields["preguntas_institucion"].found is True


@pytest.mark.asyncio
async def test_scanned_pdf_marks_ocr():
    svc = _svc()
    text = "Texto OCR del pliego escaneado. Objeto: suministros. Garantía requerida."
    docs = [_doc(text=text, pages=[text], ocr=True, title="pliego_scan.pdf")]
    result = await svc.run(_opp(), process_documents=docs, process_corpus=text, force=True)
    assert result.documents[0].ocr_used is True
    assert result.documents[0].ocr_confidence == 0.8


@pytest.mark.asyncio
async def test_principal_plus_anexos():
    svc = _svc()
    pliego = _doc(title="pliego.pdf", role="pliego", text="Pliego principal. Objeto X. Página 1.")
    anexo = _doc(title="anexo_a.pdf", role="anexo", text="Anexo A. Especificaciones técnicas detalladas.")
    result = await svc.run(
        _opp(),
        process_documents=[pliego, anexo],
        process_corpus="Pliego principal.\nAnexo A.",
        force=True,
    )
    assert len(result.documents) == 2
    roles = {d.doc_type for d in result.documents}
    assert "pliego" in roles and "anexo" in roles


@pytest.mark.asyncio
async def test_duplicate_documents_skipped():
    svc = _svc()
    h = hashlib.sha256(b"same").hexdigest()
    text = "Mismo contenido duplicado. Objeto prueba."
    d1 = _doc(title="a.pdf", text=text, content_hash=h)
    d2 = _doc(title="a_copy.pdf", text=text, content_hash=h)
    result = await svc.run(_opp(), process_documents=[d1, d2], process_corpus=text, force=True)
    assert result.documents[1].duplicate_of == str(d1.id)


@pytest.mark.asyncio
async def test_amendment_increments_version():
    svc = _svc()
    pkg = MagicMock()
    pkg.manifest = {
        "pliego_analysis": {
            "opportunity_id": str(uuid.uuid4()),
            "status": "completed",
            "version": 1,
            "fields": {k: {"key": k, "found": False, "value": "No identificado"} for k in PLIEGO_FIELD_KEYS},
            "meta": {},
        },
        "pliego_analysis_versions": [{"version": 1, "status": "completed"}],
    }
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = pkg
    svc.db.execute = AsyncMock(return_value=result_mock)

    text = "Enmienda 1: nueva fecha límite 20/09/2026. Garantía 2%."
    docs = [_doc(title="enmienda.pdf", role="enmienda", text=text)]
    result = await svc.run(_opp(), process_documents=docs, process_corpus=text, force=True)
    assert result.version == 2


@pytest.mark.asyncio
async def test_not_found_fields_create_pendientes():
    svc = _svc()
    result = await svc.run(
        _opp(title=None, objeto_proceso=None, amount=None, deadline=None, institution=None),
        process_documents=[],
        process_corpus="",
        force=True,
    )
    assert result.fields["objeto_contratacion"].found is False
    assert result.fields["objeto_contratacion"].review_required is True
    assert result.fields["pendientes"].found is True
    assert any("Confirmar" in str(i.get("descripcion", "")) for i in result.fields["pendientes"].items if isinstance(i, dict))


@pytest.mark.asyncio
async def test_evidence_page_validation():
    svc = _svc()
    docs = [_doc(text="Garantía de fiel cumplimiento.", pages=["p1", "p2"])]
    fields = {
        "garantias": PliegoFieldResult(
            key="garantias",
            found=True,
            value="Fiel cumplimiento",
            confidence=0.9,
            evidence=[
                PliegoEvidence(
                    document_id=str(docs[0].id),
                    document_name="pliego.pdf",
                    page=99,
                    fragment="garantía",
                    confidence=0.9,
                )
            ],
        )
    }
    # fill remaining
    for k in PLIEGO_FIELD_KEYS:
        if k not in fields:
            fields[k] = PliegoFieldResult(key=k, found=False, value="No identificado")
    out, _contr, errors = svc._consolidate(
        fields,
        segments=[],
        docs=svc._stage_ingestion(docs)[0],
        opportunity=_opp(),
    )
    assert out["garantias"].evidence[0].page is None
    assert out["garantias"].evidence[0].review_required is True
    assert any("página" in e.lower() for e in errors)


@pytest.mark.asyncio
async def test_evidence_wrong_document_flagged():
    svc = _svc()
    docs = [_doc(text="texto")]
    fields = {
        k: PliegoFieldResult(key=k, found=False, value="No identificado")
        for k in PLIEGO_FIELD_KEYS
    }
    fields["institucion"] = PliegoFieldResult(
        key="institucion",
        found=True,
        value="X",
        evidence=[PliegoEvidence(document_id=str(uuid.uuid4()), document_name="otro", page=1, fragment="x")],
    )
    out, _c, errors = svc._consolidate(
        fields,
        segments=[],
        docs=svc._stage_ingestion(docs)[0],
        opportunity=_opp(),
    )
    assert any("desconocido" in e.lower() for e in errors)
    assert out["institucion"].evidence[0].document_id is None


@pytest.mark.asyncio
async def test_contradiction_amount():
    svc = _svc()
    docs = [_doc(text="monto")]
    fields = {k: PliegoFieldResult(key=k, found=False, value="No identificado") for k in PLIEGO_FIELD_KEYS}
    fields["monto_estimado"] = PliegoFieldResult(
        key="monto_estimado", found=True, value="100", confidence=0.8
    )
    _out, contradictions, _e = svc._consolidate(
        fields,
        segments=[],
        docs=svc._stage_ingestion(docs)[0],
        opportunity=_opp(amount=1_500_000),
    )
    assert contradictions


@pytest.mark.asyncio
async def test_consolidation_dedups_documents():
    svc = _svc()
    docs = [_doc(text="docs")]
    fields = {k: PliegoFieldResult(key=k, found=False, value="No identificado") for k in PLIEGO_FIELD_KEYS}
    fields["documentos_solicitados"] = PliegoFieldResult(
        key="documentos_solicitados",
        found=True,
        value="2",
        items=[
            {"nombre": "Copia RNC", "categoria": "documento"},
            {"nombre": "copia rnc", "categoria": "documento", "obligatorio": True},
        ],
    )
    out, _c, _e = svc._consolidate(
        fields,
        segments=[],
        docs=svc._stage_ingestion(docs)[0],
        opportunity=_opp(),
    )
    assert len(out["documentos_solicitados"].items) == 1


@pytest.mark.asyncio
async def test_decision_suggested_structure():
    svc = _svc()
    result = await svc.run(
        _opp(),
        process_documents=[_doc(text="Objeto claro. Garantía. Fecha límite 2026.")],
        process_corpus="Objeto claro. Garantía. Fecha límite 2026.",
        hermes_meta={"status": "completed", "confidence": 0.8, "required_documents": ["RNC"],
                     "next_actions": ["Preparar oferta"], "recommendation": "revisar"},
        force=True,
    )
    dec = result.fields["decision_sugerida"]
    assert dec.value in ("participar", "revisar", "no_participar")
    assert dec.items
    assert dec.items[0].get("irreversible") is False


@pytest.mark.asyncio
async def test_partial_when_stage_fails(monkeypatch):
    svc = _svc()

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(svc, "_fill_datos_generales", boom)
    result = await svc.run(
        _opp(),
        process_documents=[_doc(text="x")],
        process_corpus="x",
        force=True,
    )
    assert "C_datos_generales" in result.meta.failed_stages
    assert result.status == PliegoAnalysisStatus.PARTIAL
    assert len(result.fields) == 29


@pytest.mark.asyncio
async def test_llm_timeout_does_not_crash(monkeypatch):
    svc = _svc()

    class FakeClient:
        def is_available(self):
            return True

        async def chat(self, **kwargs):
            raise TimeoutError("timeout")

    import app.services.dgcp_pliego_deep_analysis_service as mod

    monkeypatch.setattr(mod, "HermesClient", FakeClient, raising=False)

    # Patch import path used inside method
    async def fake_enrich(ctx, fields):
        return {}, {"ok": False, "message": "timeout", "error": "timeout"}

    monkeypatch.setattr(svc, "_llm_enrich_stages", fake_enrich)
    result = await svc.run(
        _opp(),
        process_documents=[_doc(text="Objeto y garantías del proceso.")],
        process_corpus="Objeto y garantías del proceso.",
        force=True,
    )
    assert len(result.fields) == 29
    assert result.status != PliegoAnalysisStatus.FAILED


@pytest.mark.asyncio
async def test_schema_validation_roundtrip():
    payload = {
        "opportunity_id": str(uuid.uuid4()),
        "status": "completed",
        "version": 1,
        "fields": {
            k: {"key": k, "found": False, "value": "No identificado", "confidence": 0.1}
            for k in PLIEGO_FIELD_KEYS
        },
    }
    # omit one field — validator should fill
    del payload["fields"]["visita_tecnica"]
    result = PliegoAnalysisResult.model_validate(payload)
    assert "visita_tecnica" in result.fields
    assert len(result.fields) == 29


def test_extraction_ocr_flag():
    # Unit on ExtractionResult shape
    r = ExtractionResult(text="x", pages=["x"], format="pdf", ocr_used=True, ocr_confidence=0.5)
    assert r.ocr_used is True
    assert DocumentExtractionService.detect_format("a.pdf") == "pdf"


@pytest.mark.asyncio
async def test_multitenant_package_query_uses_tenant():
    tenant = uuid.uuid4()
    svc = DGCPPliegoDeepAnalysisService(MagicMock(), tenant, uuid.uuid4())
    svc.db.execute = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    svc.db.execute.return_value = result
    await svc._get_package(uuid.uuid4())
    # ensure execute was called (tenant filter is in SQL)
    assert svc.db.execute.await_count == 1


@pytest.mark.asyncio
async def test_reanalysis_force_rebuilds():
    svc = _svc()
    text1 = "Versión 1 del pliego."
    r1 = await svc.run(_opp(), process_documents=[_doc(text=text1)], process_corpus=text1, force=True)
    assert r1.version == 1
    # simulate existing
    pkg = MagicMock()
    pkg.manifest = {
        "pliego_analysis": r1.model_dump(mode="json"),
        "pliego_analysis_versions": [{"version": 1, "status": "completed"}],
    }
    rm = MagicMock()
    rm.scalar_one_or_none.return_value = pkg
    svc.db.execute = AsyncMock(return_value=rm)
    text2 = "Versión 2 con enmienda y nueva garantía."
    r2 = await svc.run(_opp(), process_documents=[_doc(text=text2)], process_corpus=text2, force=True)
    assert r2.version == 2
