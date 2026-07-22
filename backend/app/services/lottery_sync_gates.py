"""Gates de escritura sync — staging local o allowlist de configuración (docker postgres/jaios)."""

from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.services.lottery_sync_service import SyncEnvironmentGuardError


STAGING_DB_NAME = "jaios_lottery_staging"
STAGING_PORT = 5434
STAGING_ENV = "staging"

_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "postgres", "db"})


def parse_db_url(database_url: str):
    from urllib.parse import urlparse

    parsed = urlparse(
        database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://"
        )
    )
    return parsed


def assert_sync_write_target_allowed(database_url: str) -> str:
    """Permite staging (:5434/jaios_lottery_staging) o allowlist de settings (prod docker)."""
    parsed = parse_db_url(database_url)
    host = (parsed.hostname or "").lower()
    db = (parsed.path or "").lstrip("/").lower()
    port = parsed.port or 5432

    if host not in _ALLOWED_HOSTS:
        raise SyncEnvironmentGuardError(f"Host no autorizado para escritura sync: {host}")

    if port == STAGING_PORT and db == STAGING_DB_NAME:
        return "staging"

    allowed_db = (settings.lottery_sync_allowed_database or "").strip().lower()
    allowed_port = int(settings.lottery_sync_allowed_port or 5432)
    if port == allowed_port and db == allowed_db:
        return "allowlist"

    raise SyncEnvironmentGuardError(
        f"Database/puerto no permitidos para escritura sync (db={db}, port={port}; "
        f"staging={STAGING_DB_NAME}:{STAGING_PORT} o allowlist={allowed_db}:{allowed_port})"
    )


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
    """Bloquea escritura salvo target allowlist/staging con confirmaciones."""
    if not write:
        return

    target = assert_sync_write_target_allowed(database_url)

    if via_scheduler:
        if not backup_path:
            raise SyncEnvironmentGuardError("Backup pre-run obligatorio")
        bp = Path(backup_path)
        if not bp.exists() or bp.stat().st_size < 1000:
            raise SyncEnvironmentGuardError(f"Backup inválido o ausente: {bp}")
        return

    if not yes:
        raise SyncEnvironmentGuardError("Escritura requiere --yes")

    if target == "staging":
        if (environment or "").strip().lower() != STAGING_ENV:
            raise SyncEnvironmentGuardError("--environment debe ser exactamente 'staging'")
        if (confirm_database or "").strip() != STAGING_DB_NAME:
            raise SyncEnvironmentGuardError(
                f"--confirm-database debe ser exactamente '{STAGING_DB_NAME}'"
            )
    else:
        # Allowlist (p.ej. docker postgres/jaios): environment production|allowlist
        env = (environment or "").strip().lower()
        if env not in ("production", "allowlist", "prod"):
            raise SyncEnvironmentGuardError(
                "--environment debe ser 'production' o 'allowlist' para escritura en allowlist"
            )
        expected = (settings.lottery_sync_allowed_database or "").strip()
        if (confirm_database or "").strip() != expected:
            raise SyncEnvironmentGuardError(
                f"--confirm-database debe ser exactamente '{expected}'"
            )

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
