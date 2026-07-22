"""Tests — validación documental expediente DGCP."""

from app.services.dgcp_expediente_validation_service import (
    IDENTITY_REQUIRED,
    REQUIRED_EXPEDIENTE_DOCS,
)
from app.services.dgcp_expediente_errors import ExpedienteIncompleteError


def test_required_expediente_docs():
    assert "dgii" in REQUIRED_EXPEDIENTE_DOCS
    assert "tss" in REQUIRED_EXPEDIENTE_DOCS
    assert "proveedor_estado" in REQUIRED_EXPEDIENTE_DOCS


def test_identity_required_labels():
    assert "Firma autorizada" in IDENTITY_REQUIRED


def test_incomplete_error_carries_validation():
    payload = {"status": "incompleto", "blocked": True, "missing_documents": ["tss"]}
    err = ExpedienteIncompleteError(payload)
    assert err.validation == payload
