"""Gates de escritura sync — solo staging jaios_lottery_staging @ :5434."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from app.config import settings
from app.services.lottery_importer import assert_not_production_database
from app.services.lottery_sync_service import SyncEnvironmentGuardError


STAGING_DB_NAME = "jaios_lottery_staging"
STAGING_PORT = 5434
STAGING_ENV = "staging"


def parse_db_url(database_url: str):
    parsed = urlparse(
        database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://"
        )
    )
    return parsed


def assert_write_gates(
    *,
    database_url: str,
    environment: str | None,
    confirm_database: str | None,
    write: bool,
    yes: bool,
    backup_path: str | Path | None,
    via_scheduler: bool = False,
) -> None:
    """Bloquea escritura salvo staging explícito con todas las confirmaciones."""
    assert_not_production_database(database_url)
    if not write:
        return

    if via_scheduler:
        # Path automático: confirmaciones CLI no aplican; usa assert_automatic_write_gates.
        parsed = parse_db_url(database_url)
        host = (parsed.hostname or "").lower()
        db = (parsed.path or "").lstrip("/").lower()
        port = parsed.port
        if host not in ("localhost", "127.0.0.1", "::1"):
            raise SyncEnvironmentGuardError(f"Host no autorizado para escritura: {host}")
        if port != STAGING_PORT:
            raise SyncEnvironmentGuardError(f"Puerto debe ser {STAGING_PORT}, recibido {port}")
        if db != STAGING_DB_NAME:
            raise SyncEnvironmentGuardError(f"Database debe ser {STAGING_DB_NAME}, recibido {db}")
        if not backup_path:
            raise SyncEnvironmentGuardError("Backup pre-run obligatorio")
        bp = Path(backup_path)
        if not bp.exists() or bp.stat().st_size < 1000:
            raise SyncEnvironmentGuardError(f"Backup inválido o ausente: {bp}")
        return

    if not yes:
        raise SyncEnvironmentGuardError("Escritura requiere --yes")
    if (environment or "").strip().lower() != STAGING_ENV:
        raise SyncEnvironmentGuardError("--environment debe ser exactamente 'staging'")
    if (confirm_database or "").strip() != STAGING_DB_NAME:
        raise SyncEnvironmentGuardError(
            f"--confirm-database debe ser exactamente '{STAGING_DB_NAME}'"
        )

    parsed = parse_db_url(database_url)
    host = (parsed.hostname or "").lower()
    db = (parsed.path or "").lstrip("/").lower()
    port = parsed.port

    if host not in ("localhost", "127.0.0.1", "::1"):
        raise SyncEnvironmentGuardError(f"Host no autorizado para escritura: {host}")
    if port != STAGING_PORT:
        raise SyncEnvironmentGuardError(f"Puerto debe ser {STAGING_PORT}, recibido {port}")
    if db != STAGING_DB_NAME:
        raise SyncEnvironmentGuardError(f"Database debe ser {STAGING_DB_NAME}, recibido {db}")

    if not settings.lottery_sync_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SYNC_ENABLED debe ser true temporalmente")
    if not settings.lottery_sync_write_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SYNC_WRITE_ENABLED debe ser true temporalmente")
    if settings.lottery_scheduler_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SCHEDULER_ENABLED debe permanecer false para CLI manual")
    if settings.lottery_scraping_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SCRAPING_ENABLED debe permanecer false")

    if not backup_path:
        raise SyncEnvironmentGuardError("Backup pre-run obligatorio (--backup-path)")
    bp = Path(backup_path)
    if not bp.exists() or bp.stat().st_size < 1000:
        raise SyncEnvironmentGuardError(f"Backup inválido o ausente: {bp}")
