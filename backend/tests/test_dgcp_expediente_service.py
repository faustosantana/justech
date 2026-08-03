"""Focused unit tests for DGCP expediente packaging metrics."""

from __future__ import annotations

import json
import uuid
import zipfile
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_expediente_service import DGCPExpedienteService, EXPEDIENTE_FOLDERS


def _sample_opportunity(*, company: str = "just_office") -> DGCPOpportunity:
    return DGCPOpportunity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="PROC-EXP-001",
        institution="Ministerio Test",
        title="Adquisición equipos",
        amount=Decimal("250000"),
        deadline=date(2026, 12, 31),
        description="Proceso de prueba con requisitos legales.",
        full_info={},
        raw_payload={},
        company=company,
    )


class _NoopSource:
    @staticmethod
    def is_available() -> bool:
        return False


class _BytesSource:
    def __init__(self, mapping: dict[str, bytes]):
        self.mapping = mapping

    def is_available(self) -> bool:
        return True

    def read_bytes(self, relative_path: str) -> bytes:
        return self.mapping[relative_path]


@pytest.mark.asyncio
async def test_prepare_writes_expected_expediente_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "expediente_storage_path", str(tmp_path))

    service = DGCPExpedienteService(db=None, tenant_id=uuid.uuid4())
    service.source = _NoopSource()

    result = await service.prepare(
        _sample_opportunity(),
        checklist=[
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
        ],
        matches=[],
        bid_package={
            "preparation_pct": 5.9,
            "found_documents": 1,
            "pending_documents": 0,
            "expired_documents": 0,
        },
        user_input={"_final_validation": {"estado": "No listo"}},
        generated_forms=[],
        company_key="just_office",
    )

    base = tmp_path / str(service.tenant_id) / "PROC-EXP-001"
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
async def test_prepare_metrics_empty_expediente(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "expediente_storage_path", str(tmp_path))
    service = DGCPExpedienteService(db=None, tenant_id=uuid.uuid4())
    service.source = _NoopSource()

    result = await service.prepare(
        _sample_opportunity(),
        checklist=[
            {
                "requirement_key": "rpe",
                "requirement": "RPE vigente",
                "tipo": "legal",
                "mandatory": True,
                "status": "faltante",
            }
        ],
        matches=[],
        bid_package={"preparation_pct": 55},  # stale — must not win
        company_key="just_office",
    )
    assert result.copied_documents == 0
    assert result.preparation_pct == 0.0
    assert result.manifest["metrics"]["copied_documents"] == 0
    assert result.manifest["preparation_pct"] == 0.0


@pytest.mark.asyncio
async def test_prepare_metrics_with_documents_match_zip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "expediente_storage_path", str(tmp_path))
    tenant = uuid.uuid4()
    service = DGCPExpedienteService(db=None, tenant_id=tenant)
    service.source = _BytesSource({"docs/rpe.pdf": b"%PDF-1.4 rpe", "docs/dgii.pdf": b"%PDF-1.4 dgii"})

    result = await service.prepare(
        _sample_opportunity(),
        checklist=[
            {
                "requirement_key": "rpe",
                "requirement": "RPE vigente",
                "tipo": "legal",
                "mandatory": True,
                "status": "encontrado_vigente",
                "document_id": str(uuid.uuid4()),
            },
            {
                "requirement_key": "dgii",
                "requirement": "Certificación DGII",
                "tipo": "legal",
                "mandatory": True,
                "status": "encontrado_vigente",
                "document_id": str(uuid.uuid4()),
            },
            {
                "requirement_key": "tss",
                "requirement": "Certificación TSS",
                "tipo": "legal",
                "mandatory": True,
                "status": "faltante",
            },
        ],
        matches=[
            {
                "requirement_key": "rpe",
                "requirement_label": "RPE vigente",
                "status": "encontrado_vigente",
                "relative_path": "docs/rpe.pdf",
            },
            {
                "requirement_key": "dgii",
                "requirement_label": "Certificación DGII",
                "status": "encontrado_vigente",
                "relative_path": "docs/dgii.pdf",
            },
        ],
        bid_package={"preparation_pct": 0},
        company_key="just_office",
    )

    assert result.copied_documents == 2
    assert result.preparation_pct > 0
    assert result.manifest["preparation_pct"] == result.preparation_pct
    assert result.manifest["metrics"]["copied_documents"] == 2

    base = tmp_path / str(tenant) / "PROC-EXP-001"
    zip_bytes, _ = service.build_download_archive(str(base))
    zip_content = service.inventory_zip_content(zip_bytes)
    assert len(zip_content) == 2
    assert len(zip_content) == result.copied_documents


@pytest.mark.asyncio
async def test_prepare_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "expediente_storage_path", str(tmp_path))
    tenant = uuid.uuid4()
    service = DGCPExpedienteService(db=None, tenant_id=tenant)
    service.source = _BytesSource({"docs/rpe.pdf": b"%PDF-1.4 rpe"})
    opp = _sample_opportunity()
    kwargs = dict(
        checklist=[
            {
                "requirement_key": "rpe",
                "requirement": "RPE vigente",
                "tipo": "legal",
                "mandatory": True,
                "status": "encontrado_vigente",
                "document_id": str(uuid.uuid4()),
            }
        ],
        matches=[
            {
                "requirement_key": "rpe",
                "requirement_label": "RPE vigente",
                "status": "encontrado_vigente",
                "relative_path": "docs/rpe.pdf",
            }
        ],
        bid_package={"preparation_pct": 0},
        company_key="just_office",
    )
    first = await service.prepare(opp, **kwargs)
    second = await service.prepare(opp, **kwargs)
    assert first.copied_documents == second.copied_documents == 1
    assert first.preparation_pct == second.preparation_pct
    base = tmp_path / str(tenant) / "PROC-EXP-001"
    content = list((base / "01_Documentos_Legales").glob("*.pdf"))
    assert len(content) == 1
