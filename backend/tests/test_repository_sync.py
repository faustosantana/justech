"""Tests — motor de sincronización de repositorios."""

from app.services.repository_sync_service import FOLDER_DEFAULTS, RepositorySyncService


def test_folder_defaults_include_justech_paths():
    keys = {k for k, _, _, _ in FOLDER_DEFAULTS}
    assert "00_DATOS_EMPRESAS" in keys
    assert "01_DOCUMENTOS_LEGALES" in keys
    assert "03_PROVEEDORES_ENTRADAS" in keys
    path_map = {k: p for k, _, _, p in FOLDER_DEFAULTS}
    assert path_map["00_DATOS_EMPRESAS"].startswith("Justech-AI/")


def test_content_hash_stable():
    h1 = RepositorySyncService.content_hash("file.xlsx", 1024, None)
    h2 = RepositorySyncService.content_hash("file.xlsx", 1024, None)
    assert h1 == h2
    assert len(h1) == 64


def test_type_for_key():
    assert RepositorySyncService._type_for_key("00_DATOS_EMPRESAS") == "company_data"
    assert RepositorySyncService._type_for_key("UNKNOWN") == "general"
