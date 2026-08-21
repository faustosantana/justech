"""Tests — perfiles 360° e identidad histórica DGCP."""

from __future__ import annotations

from app.services.dgcp_historical_identity import (
    identity_confidence,
    institution_stable_key,
    normalize_party_name,
    parse_institution_key,
    parse_supplier_key,
    supplier_stable_key,
)
from app.services.dgcp_historical_similarity_engine import is_valid_award_status


def test_normalize_supplier_name_variants():
    a = normalize_party_name("ABC, S.R.L.")
    b = normalize_party_name("ABC SRL.")
    c = normalize_party_name("ABC SRL")
    assert a == b == c == "abc srl"


def test_supplier_key_prefers_rnc_then_rpe():
    assert supplier_stable_key(rpe="56446", name="X", rnc="1-31-12345-6").startswith("rnc-")
    assert supplier_stable_key(rpe="56446", name="X", rnc=None) == "rpe-56446"
    key = supplier_stable_key(rpe=None, name="Soluciones Empresariales SRL", rnc=None)
    assert key.startswith("name-")
    parsed = parse_supplier_key(key)
    assert parsed["kind"] == "name"
    assert identity_confidence("rpe") == "alta"
    assert identity_confidence("name") == "sugerida"


def test_institution_key_prefers_code():
    assert institution_stable_key(code="1234", name="MINERD") == "code-1234"
    key = institution_stable_key(code=None, name="Ministerio de Educación")
    assert key.startswith("name-")
    parsed = parse_institution_key(key)
    assert parsed["kind"] == "name"


def test_cancelled_not_valid_purchase_status():
    assert is_valid_award_status("Cancelada") is False
    assert is_valid_award_status("Confirmada y enviada") is True
