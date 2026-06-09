"""Tests — DocumentValidityAnalyzer (Fase 7.3 QA)."""

from datetime import date, timedelta

from app.services.document_validity_analyzer import DocumentValidityAnalyzer


def test_extracts_expiry_from_spanish_text():
    future = (date.today() + timedelta(days=90)).strftime("%d/%m/%Y")
    text = f"Certificación DGII. Válida hasta {future}."
    result = DocumentValidityAnalyzer().analyze_document(
        "certificacion_dgii",
        text=text,
        title="DGII Justech.pdf",
    )
    assert result.expiration_date is not None
    assert result.requirement_status == "encontrado_vigente"
    assert result.text_analyzed is True


def test_empty_text_is_sin_analizar():
    result = DocumentValidityAnalyzer().analyze_document(
        "certificacion_tss",
        text="",
        title="TSS.pdf",
    )
    assert result.requirement_status == "encontrado_sin_analizar"
    assert result.validity_status == "requiere_revision"


def test_rpe_without_date_is_vigente_when_read():
    result = DocumentValidityAnalyzer().analyze_document(
        "rpe",
        text="Registro de Proveedores del Estado activo.",
        title="RPE.pdf",
    )
    assert result.requirement_status == "encontrado_vigente"
    assert result.vigency_status == "no_aplica_vigencia"


def test_expired_date_marks_vencido():
    past = (date.today() - timedelta(days=10)).strftime("%d/%m/%Y")
    text = f"Registro Mercantil. Fecha de vencimiento: {past}"
    result = DocumentValidityAnalyzer().analyze_document(
        "registro_mercantil",
        text=text,
    )
    assert result.requirement_status == "encontrado_vencido"
