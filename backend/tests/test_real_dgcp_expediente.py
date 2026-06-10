"""Tests — Real DGCP Expediente (Fase 3 / 3.5)."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from app.services.real_expediente_classifier import (
    REAL_EXPEDIENTE_FOLDERS,
    classify_requirement,
    compute_real_expediente_status,
    is_ready_for_upload,
)
from app.services.real_expediente_report_pdf import build_preparation_report_pdf
from app.services.real_dgcp_expediente_builder import RealDGCPExpedienteBuilder


def test_all_expediente_folders_defined():
    assert len(REAL_EXPEDIENTE_FOLDERS) == 8
    assert "08_Listo_Para_Subir" in REAL_EXPEDIENTE_FOLDERS
    assert "07_Revision" in REAL_EXPEDIENTE_FOLDERS


def test_classify_legal_and_economic():
    assert classify_requirement("certificacion_dgii", "legal") == "01_Documentos_Legales"
    assert classify_requirement("oferta_economica", "financiero") == "04_Oferta_Economica"
    assert classify_requirement("sncc_f042", "administrativo") == "02_Formularios"
    assert classify_requirement("carta_fabricante", "tecnico") == "06_Cartas_Fabricante"


def test_ready_for_upload_rejects_vencido_and_docx():
    ok, _ = is_ready_for_upload(
        requirement_key="certificacion_dgii",
        status="encontrado_vigente",
        filename="dgii.pdf",
    )
    assert ok is True

    ok, reason = is_ready_for_upload(
        requirement_key="certificacion_dgii",
        status="encontrado_vencido",
        filename="dgii.pdf",
    )
    assert ok is False
    assert "vencido" in reason.lower()

    ok, reason = is_ready_for_upload(
        requirement_key="sncc_f042",
        status="finalizado",
        filename="form.docx",
    )
    assert ok is False
    assert "pdf" in reason.lower()


def test_compute_status_rules():
    assert compute_real_expediente_status(missing_count=1, expired_count=0, review_count=0, ready_count=0, mandatory_total=5) == "generado_incompleto"
    assert compute_real_expediente_status(missing_count=0, expired_count=1, review_count=0, ready_count=3, mandatory_total=5) == "generado_con_observaciones"
    assert compute_real_expediente_status(missing_count=0, expired_count=0, review_count=0, ready_count=5, mandatory_total=5) == "listo_para_revision"


def test_report_pdf_bytes():
    manifest = {
        "process_code": "TEST-001",
        "company_name": "Justech SRL",
        "buyer": "MINERD",
        "generated_at": "2026-06-06T12:00:00Z",
        "generated_by": "user",
        "status": "generado_incompleto",
        "preparation_percentage": 75,
        "checklist_summary": {"total": 10, "compliant": 7},
        "requirements": [],
        "warnings": ["1 faltante"],
    }
    data = build_preparation_report_pdf(manifest)
    assert data[:4] == b"%PDF"


def test_zip_build_excludes_ds_store(tmp_path):
    base = tmp_path / "EXPEDIENTE"
    for folder in REAL_EXPEDIENTE_FOLDERS:
        (base / folder).mkdir(parents=True)
    (base / "01_Documentos_Legales" / "doc.pdf").write_bytes(b"%PDF-1.4")
    (base / ".DS_Store").write_bytes(b"bad")
    (base / "manifest.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (base / "reporte_preparacion.pdf").write_bytes(b"%PDF")

    zbytes = RealDGCPExpedienteBuilder._build_zip(base)
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        names = zf.namelist()
    assert not any(".DS_Store" in n for n in names)
    assert not any("__MACOSX" in n for n in names)
    assert any(n.endswith("manifest.json") for n in names)
    assert any("01_Documentos_Legales" in n for n in names)


def test_assistant_matches():
    from app.services.real_expediente_question_service import RealExpedienteQuestionService

    assert RealExpedienteQuestionService.matches("Genera el expediente real")
    assert RealExpedienteQuestionService.matches("¿Qué falta para el expediente?")
    assert RealExpedienteQuestionService.matches("Descarga el expediente")
    assert not RealExpedienteQuestionService.matches("precio de laptops")
    assert not RealExpedienteQuestionService.matches("¿Qué porcentaje del expediente está listo?")


def test_operational_stage_mapping():
    from app.services.dgcp_operational_stages import (
        expediente_status_for_real,
        operational_stage_for_real_status,
    )

    assert operational_stage_for_real_status("paquete_dgcp_preparado") == "PAQUETE_DGCP_PREPARADO"
    assert operational_stage_for_real_status("listo_para_subir") == "LISTA_PARA_PRESENTAR"
    assert expediente_status_for_real("paquete_dgcp_preparado") == "expediente_listo_para_presentar"
