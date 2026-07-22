"""Tests — identidad corporativa y finalización documental."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import settings
from app.services.corporate_identity_constants import COMPANY_STAMP_FILES, DEFAULT_SIGNATURE_FILE
from app.services.corporate_identity_service import CorporateIdentityService
from app.services.document_finalization_rules import requires_finalization
from app.services.pdf_signature_overlay import apply_signature_and_stamp, text_to_pdf_bytes


def identity_root() -> Path:
    return Path(settings.knowledge_source_path) / CorporateIdentityService.SUBFOLDER


@pytest.mark.parametrize(
    "filename",
    [
        "firma_fausto.png",
        "sello_justech.png",
        "sello_justoffice.png",
        "sello_plugsafe.png",
        "sello_omni.png",
    ],
)
def test_corporate_identity_files_exist_on_disk(filename):
    root = identity_root()
    if not root.is_dir():
        pytest.skip(f"Repositorio identidad no montado en {root}")
    if "firma" in filename:
        path = root / "FIRMAS" / filename
    else:
        path = root / "SELLOS" / filename
    assert path.is_file(), f"Falta {filename} en {path}"


def test_metadata_json_exists():
    meta = identity_root() / "metadata.json"
    if not identity_root().is_dir():
        pytest.skip("Repositorio identidad no montado")
    assert meta.is_file()


def test_company_stamp_mapping():
    assert COMPANY_STAMP_FILES["justech"] == "sello_justech.png"
    assert COMPANY_STAMP_FILES["just_office"] == "sello_justoffice.png"
    assert COMPANY_STAMP_FILES["mf_plug_safe"] == "sello_plugsafe.png"
    assert COMPANY_STAMP_FILES["omni_solutions"] == "sello_omni.png"
    assert DEFAULT_SIGNATURE_FILE == "firma_fausto.png"


def test_requires_finalization_keys():
    assert requires_finalization("sncc_f042")
    assert requires_finalization("oferta_economica")
    assert requires_finalization("carta_presentacion")
    assert not requires_finalization("rpe")


def test_text_to_pdf_bytes():
    pdf = text_to_pdf_bytes("Test", ["Linea 1", "Linea 2"])
    assert pdf.startswith(b"%PDF")


def test_apply_signature_and_stamp_produces_pdf():
    root = identity_root()
    if not root.is_dir():
        pytest.skip("Repositorio identidad no montado")
    base = text_to_pdf_bytes("SNCC F042", ["Campo: valor"])
    sig = root / "FIRMAS" / "firma_fausto.png"
    stamp = root / "SELLOS" / "sello_justech.png"
    if not sig.is_file() or not stamp.is_file():
        pytest.skip("Assets de identidad no disponibles")
    out = apply_signature_and_stamp(
        base,
        signature_path=sig,
        stamp_path=stamp,
        placement={
            "signature": {"position": "bottom_right", "width": 180, "margin": 36},
            "stamp": {"position": "bottom_left", "width": 150, "margin": 36},
        },
    )
    assert out.startswith(b"%PDF")
    assert len(out) > len(base)


def test_corporate_identity_service_file_status():
    root = identity_root()
    if not root.is_dir():
        pytest.skip("Repositorio identidad no montado")
    svc = CorporateIdentityService(None, uuid.uuid4())  # type: ignore[arg-type]
    path = svc._asset_path("signature", "firma_fausto.png")
    assert svc._file_status(path) == "disponible"


def test_stamp_filename_for_companies():
    svc = CorporateIdentityService(None, uuid.uuid4())  # type: ignore[arg-type]
    assert svc.stamp_filename_for_company("justech") == "sello_justech.png"
    assert svc.stamp_filename_for_company("just_office") == "sello_justoffice.png"


@pytest.mark.asyncio
async def test_assert_stamp_wrong_company_rejected():
    svc = CorporateIdentityService(None, uuid.uuid4())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="no permitido"):
        await svc.assert_stamp_allowed("justech", "sello_omni.png")


def test_document_finalization_question_matches():
    from app.services.document_finalization_question_service import DocumentFinalizationQuestionService

    assert DocumentFinalizationQuestionService.matches("¿Tenemos sello de Justech?")
    assert DocumentFinalizationQuestionService.matches("Genera los PDFs finales")
    assert not DocumentFinalizationQuestionService.matches("precio de laptops")


@pytest.mark.asyncio
async def test_corporate_identity_api_requires_auth():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/corporate-identity")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dgcp_finalization_preview_requires_auth():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/dgcp/opportunities/00000000-0000-0000-0000-000000000001/finalization/preview",
            json={"requirement_key": "sncc_f042"},
        )
    assert response.status_code == 401
