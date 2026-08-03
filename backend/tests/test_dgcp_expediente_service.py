"""Focused unit tests for DGCP expediente packaging."""

from __future__ import annotations

import json
import uuid
import zipfile
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_bid_package_service import EXPEDIENTE_TRACKING_STATUSES
from app.services.dgcp_expediente_service import DGCPExpedienteService, EXPEDIENTE_FOLDERS


def _sample_opportunity() -> DGCPOpportunity:
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
        company="just_office",
    )


class _NoopSource:
    @staticmethod
    def is_available() -> bool:
        return False


def test_expediente_tracking_accepts_preparing_status():
    assert "preparing" in EXPEDIENTE_TRACKING_STATUSES


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
