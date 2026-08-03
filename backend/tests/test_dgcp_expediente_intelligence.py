"""Tests — DGCP Expediente Intelligence (Fase 7.3)."""

from __future__ import annotations

import json
import uuid
import zipfile
from datetime import date
from decimal import Decimal
from io import BytesIO

from tests.dgcp_test_helpers import analyze_with_interest

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_expediente_service import DGCPExpedienteService, EXPEDIENTE_FOLDERS
from app.services.dgcp_requirements_extractor import DGCPRequirementsExtractor


class _FakeProcessDoc:
    def __init__(self, title: str, doc_role: str = "pliego") -> None:
        self.id = uuid.uuid4()
        self.title = title
        self.doc_role = doc_role


def _sample_opportunity() -> DGCPOpportunity:
    return DGCPOpportunity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="LPN-2024-EXP",
        institution="Ministerio Test",
        title="Adquisición equipos",
        amount=Decimal("250000"),
        deadline=date(2026, 12, 31),
        description="Proceso de prueba con requisitos legales.",
        full_info={},
        raw_payload={},
    )


def test_extractor_evidence_from_process_corpus():
    opp = _sample_opportunity()
    corpus = (
        "Pliego de Condiciones — Documentación Legal. "
        "El oferente deberá presentar certificación vigente de la TSS. "
        "Se requiere visita técnica obligatoria. "
        "Criterios de evaluación: 70% técnico, 30% económico."
    )
    docs = [_FakeProcessDoc("Pliego de Condiciones.pdf", "pliego")]
    result = DGCPRequirementsExtractor().extract(
        opp,
        process_corpus=corpus,
        process_documents=docs,
    )
    tss = next((d for d in result.mandatory_documents if d.key == "certificacion_tss"), None)
    assert tss is not None
    assert tss.evidence
    assert "Pliego" in tss.evidence[0].documento_origen
    assert tss.evidence[0].confianza == "alta"

    visita = next((r for r in result.technical if r.key == "visita_tecnica"), None)
    assert visita is not None


async def _auth_headers() -> dict[str, str] | None:
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
            return None
        return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_dgcp_expediente_api_flow():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if list_res.status_code != 200 or not list_res.json()["items"]:
            pytest.skip("Sin oportunidades DGCP")
        opp_id = list_res.json()["items"][0]["id"]

        analyze = await analyze_with_interest(client, opp_id, headers)
        assert analyze.status_code == 200, analyze.text
        body = analyze.json()
        assert "process_documents" in body
        assert "alerts" in body

        proc_docs = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/process-documents",
            headers=headers,
        )
        assert proc_docs.status_code == 200

        alerts = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/alerts",
            headers=headers,
        )
        assert alerts.status_code == 200
        assert alerts.json()["total"] >= 0

        autofill = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/forms/autofill-preview",
            headers=headers,
            json={"form_type": "SNCC.F042", "company": "justech"},
        )
        assert autofill.status_code == 200
        assert autofill.json()["generate_enabled"] is True
        assert any(f.get("source") for f in autofill.json()["fields"])

        licitar = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/actions",
            headers=headers,
            json={"action": "licitar", "notes": "Interés QA — habilitar expediente"},
        )
        assert licitar.status_code == 200, licitar.text

        prepare = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/prepare?company_key=just_office",
            headers=headers,
        )
        assert prepare.status_code == 200, prepare.text
        manifest = prepare.json()["manifest"]
        assert manifest.get("opportunity_code")
        assert manifest.get("preparation_pct") is not None
        assert manifest.get("company_key") == "just_office"
        assert "00_Informacion_General" in (manifest.get("sections") or [])
        assert "12_Revision" in (manifest.get("sections") or [])

        status = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/status",
            headers=headers,
        )
        assert status.status_code == 200
        assert status.json()["can_download"] is True

        download = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/download",
            headers=headers,
        )
        assert download.status_code == 200
        assert download.headers.get("content-type", "").startswith("application/zip")
        assert "filename*=UTF-8''" in download.headers.get("content-disposition", "")

        user_input = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/user-input",
            headers=headers,
            json={"fabricante": "Dell", "monto": "RD$250,000"},
        )
        assert user_input.status_code == 200


@pytest.mark.asyncio
async def test_prepare_writes_expected_expediente_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "expediente_storage_path", str(tmp_path))

    service = DGCPExpedienteService(db=None, tenant_id=uuid.uuid4())

    class _NoopSource:
        @staticmethod
        def is_available() -> bool:
            return False

    service.source = _NoopSource()
    opp = _sample_opportunity()
    opp.code = "PROC-EXP-001"
    opp.company = "just_office"
    checklist = [
        {
            "id": str(uuid.uuid4()),
            "requirement_key": "rpe",
            "requirement": "RPE vigente",
            "tipo": "legal",
            "mandatory": True,
            "status": "cumple",
            "document_title": "rpe_e2e.pdf",
            "ai_validation": {"cumple": True, "observaciones": "Documento alineado."},
        },
        {
            "id": str(uuid.uuid4()),
            "requirement_key": "sncc_f033",
            "requirement": "SNCC F.033",
            "tipo": "administrativo",
            "mandatory": True,
            "status": "requiere_completado",
            "document_title": "sncc_f033_e2e.pdf",
        },
    ]
    result = await service.prepare(
        opp,
        checklist=checklist,
        matches=[],
        bid_package={"preparation_pct": 5.9, "found_documents": 1, "pending_documents": 0, "expired_documents": 0},
        user_input={"_final_validation": {"estado": "No listo"}},
        generated_forms=[],
        company_key="just_office",
    )

    base = tmp_path / str(service.tenant_id) / opp.code
    assert result.manifest["company_key"] == "just_office"
    assert result.manifest["sections"] == list(EXPEDIENTE_FOLDERS)
    for folder in EXPEDIENTE_FOLDERS:
        assert (base / folder).is_dir()
    assert (base / "00_Informacion_General" / "indice_expediente.json").is_file()
    assert (base / "00_Informacion_General" / "indice_expediente.md").is_file()
    assert (base / "12_Revision" / "validaciones_ia.json").is_file()
    assert (
        (base / "12_Revision" / "reporte_estado_expediente.pdf").is_file()
        or (base / "12_Revision" / "reporte_estado_expediente.txt").is_file()
    )

    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["company_key"] == "just_office"
    assert manifest["index"]["total"] == 2

    archive_bytes, filename = service.build_download_archive(str(base))
    assert filename == "expediente_PROC-EXP-001.zip"
    with zipfile.ZipFile(BytesIO(archive_bytes)) as zf:
        names = set(zf.namelist())
    assert "manifest.json" in names
    assert "00_Informacion_General/indice_expediente.json" in names
    assert "00_Informacion_General/indice_expediente.md" in names
    assert "12_Revision/validaciones_ia.json" in names


@pytest.mark.asyncio
async def test_assistant_live_input_updates_expediente():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if not list_res.json().get("items"):
            pytest.skip("Sin oportunidades")
        opp_id = list_res.json()["items"][0]["id"]

        await analyze_with_interest(client, opp_id, headers)

        response = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": "El fabricante es Dell y el monto será RD$250,000",
                "current_module": "/dgcp",
                "record_type": "dgcp",
                "current_record_id": opp_id,
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["query_type"] == "dgcp_requirements_query"
        assert "dell" in body["answer"].lower() or "actualicé" in body["answer"].lower()
