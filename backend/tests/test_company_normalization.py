"""Tests — normalización de empresas."""

from app.services.company_normalization_service import (
    CANONICAL_COMPANIES,
    COMPANY_KEYS,
    company_folder,
    normalize_company_key,
)


def test_four_canonical_companies():
    assert len(CANONICAL_COMPANIES) == 4
    assert len(COMPANY_KEYS) == 4


def test_normalize_aliases():
    assert normalize_company_key("JUSTECH") == "justech"
    assert normalize_company_key("plug_safe") == "mf_plug_safe"
    assert normalize_company_key("PLUG SAFE") == "mf_plug_safe"
    assert normalize_company_key("omni") == "omni_solutions"
    assert normalize_company_key("just_office") == "just_office"


def test_company_folder_names():
    assert company_folder("justech") == "JUSTECH"
    assert company_folder("mf_plug_safe") == "PLUG_SAFE"
    assert company_folder("omni_solutions") == "OMNI"


def test_labels_match_requirement():
    labels = {c["key"]: c["label"] for c in CANONICAL_COMPANIES}
    assert labels["justech"] == "Justech SRL"
    assert labels["just_office"] == "Just Office SRL"
    assert "Plug" in labels["mf_plug_safe"]
    assert labels["omni_solutions"] == "Omni Solutions SRL"
