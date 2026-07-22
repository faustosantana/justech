"""Fase 9 — RC staging stack contracts (sin Producción)."""

from pathlib import Path

from app.config import settings


ROOT = Path(__file__).resolve().parents[2]


def test_scheduler_defaults_safe_for_rc():
    assert settings.lottery_scheduler_enabled is False
    assert settings.lottery_scheduler_mode == "disabled"
    assert settings.lottery_sync_write_enabled is False
    assert settings.lottery_sync_automatic_write_enabled is False


def test_staging_compose_files_exist():
    assert (ROOT / "docker-compose.staging.yml").is_file()
    assert (ROOT / "docker-compose.staging-app.yml").is_file()


def test_staging_env_example_has_ports_and_flags():
    text = (ROOT / ".env.staging.example").read_text()
    assert "STAGING_API_PORT=8001" in text or "8001" in text
    assert "LOTTERY_SCHEDULER_MODE=disabled" in text
    assert "LOTTERY_SYNC_AUTOMATIC_WRITE_ENABLED=false" in text


def test_seed_users_use_valid_email_domains():
    text = (ROOT / "backend/scripts/seed_lottery_staging_users.py").read_text()
    assert "@example.com" in text
    assert "@example.local" not in text


def test_rc_scope_freeze_doc_exists():
    assert (ROOT / "docs/modules/lottery/RC_SCOPE_FREEZE.md").is_file()
    assert (ROOT / "docs/modules/lottery/PHASE_9_PRECHECK.md").is_file()


def test_nacional_dia_still_ambiguous_constant():
    from app.services.lottery_permissions import AMBIGUOUS_NACIONAL_DIA_CANDIDATES, UNRESOLVED_AMBIGUOUS_ALIASES

    ids = {c["source_id"] for c in AMBIGUOUS_NACIONAL_DIA_CANDIDATES}
    assert 20 in ids and 21 in ids
    assert "nacional dia" in UNRESOLVED_AMBIGUOUS_ALIASES or "nacional día" in UNRESOLVED_AMBIGUOUS_ALIASES
