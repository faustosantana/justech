"""Tests — extracción de vigencia desde texto interno (Fase 7.3)."""

from datetime import date, timedelta

from app.services.document_vigency_extractor import DocumentVigencyExtractor, VIGENCY_REQUIREMENT_KEYS


def test_only_specific_requirements_require_vigency():
    assert DocumentVigencyExtractor.requires_vigency_check("certificacion_tss")
    assert DocumentVigencyExtractor.requires_vigency_check("certificacion_dgii")
    assert not DocumentVigencyExtractor.requires_vigency_check("rpe")
    assert not DocumentVigencyExtractor.requires_vigency_check("sncc_f042")


def test_extract_valid_until_from_document_text():
    future = (date.today() + timedelta(days=120)).strftime("%d/%m/%Y")
    text = f"Certificación de cumplimiento TSS. Válida hasta {future}."
    result = DocumentVigencyExtractor().extract_from_text(text, title="TSS Justech.pdf")
    assert result.expiration_date is not None
    assert result.validity_status == "vigente"
    assert result.text_analyzed is True


def test_missing_date_requires_validation_not_vigente():
    text = "Certificación DGII — obligaciones al día. Sin fecha visible en el cuerpo."
    extractor = DocumentVigencyExtractor()
    status, valid_until, vigency_status, note = extractor.resolve_requirement_match(
        "certificacion_dgii",
        text=text,
        title="DGII.pdf",
    )
    assert status == "encontrado_sin_fecha"
    assert valid_until is None
    assert "no verificada" in (note or "").lower()


def test_rpe_found_without_vigency_check():
    extractor = DocumentVigencyExtractor()
    status, _, vigency_status, _ = extractor.resolve_requirement_match(
        "rpe",
        text="Registro de Proveedores del Estado vigente.",
        title="RPE.pdf",
    )
    assert status == "encontrado_vigente"
    assert vigency_status == "no_aplica_vigencia"


def test_expired_date_in_text():
    past = (date.today() - timedelta(days=30)).strftime("%d/%m/%Y")
    text = f"Registro Mercantil. Fecha de vencimiento: {past}"
    status, _, vigency_status, _ = DocumentVigencyExtractor().resolve_requirement_match(
        "registro_mercantil",
        text=text,
    )
    assert status == "encontrado_vencido"
    assert vigency_status == "vencido"


def test_vigency_keys_set():
    assert "certificacion_mipyme" in VIGENCY_REQUIREMENT_KEYS
