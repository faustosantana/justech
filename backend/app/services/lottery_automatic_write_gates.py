"""Gates de escritura automática del scheduler (staging o allowlist configurada)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.lottery_sync_gates import STAGING_ENV, assert_sync_write_target_allowed
from app.services.lottery_sync_service import SyncEnvironmentGuardError


def assert_automatic_write_gates(
    *,
    database_url: str,
    mode: str,
    dry_run_report: Any,
    backup_path: str | Path | None,
    circuit_allow_write: bool,
    write_enabled_since: datetime | None = None,
) -> None:
    """Todas las condiciones deben cumplirse antes de guarded_write automático."""
    assert_sync_write_target_allowed(database_url)

    if (mode or "").strip().lower() != "guarded_write":
        raise SyncEnvironmentGuardError("Modo automático debe ser guarded_write")
    if not settings.lottery_scheduler_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SCHEDULER_ENABLED debe ser true")
    if (settings.lottery_scheduler_mode or "").lower() != "guarded_write":
        raise SyncEnvironmentGuardError("LOTTERY_SCHEDULER_MODE debe ser guarded_write")
    if not settings.lottery_sync_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SYNC_ENABLED debe ser true")
    if not settings.lottery_sync_write_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SYNC_WRITE_ENABLED debe ser true")
    if not settings.lottery_sync_automatic_write_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SYNC_AUTOMATIC_WRITE_ENABLED debe ser true")
    if settings.lottery_scraping_enabled:
        raise SyncEnvironmentGuardError("LOTTERY_SCRAPING_ENABLED debe permanecer false")
    if not circuit_allow_write:
        raise SyncEnvironmentGuardError("Circuit breaker bloquea escritura")
    if settings.lottery_sync_require_dry_run and dry_run_report is None:
        raise SyncEnvironmentGuardError("Dry-run obligatorio antes de escritura automática")

    if not backup_path:
        raise SyncEnvironmentGuardError("Backup pre-run obligatorio para guarded_write")
    bp = Path(backup_path)
    if not bp.exists() or bp.stat().st_size < 1000:
        raise SyncEnvironmentGuardError(f"Backup inválido: {bp}")
    age_h = (datetime.now(timezone.utc).timestamp() - bp.stat().st_mtime) / 3600
    if age_h > settings.lottery_sync_backup_max_age_hours:
        raise SyncEnvironmentGuardError(
            f"Backup demasiado antiguo ({age_h:.1f}h > {settings.lottery_sync_backup_max_age_hours}h)"
        )

    if write_enabled_since:
        minutes = (datetime.now(timezone.utc) - write_enabled_since).total_seconds() / 60
        if minutes > settings.lottery_sync_write_flag_max_minutes:
            raise SyncEnvironmentGuardError(
                f"Write flags habilitados demasiado tiempo ({minutes:.0f}m)"
            )

    new_n = int(getattr(dry_run_report, "records_new", 0) or 0)
    changed = int(getattr(dry_run_report, "records_changed", 0) or 0)
    conflicts = int(getattr(dry_run_report, "records_conflicted", 0) or 0)
    invalid = int(getattr(dry_run_report, "records_invalid", 0) or 0)
    ambiguous = int(getattr(dry_run_report, "records_ambiguous", 0) or 0)

    if new_n > settings.lottery_sync_max_new_per_run:
        raise SyncEnvironmentGuardError(f"NEW {new_n} excede máximo {settings.lottery_sync_max_new_per_run}")
    if changed > settings.lottery_sync_max_changed_per_run:
        raise SyncEnvironmentGuardError(f"CHANGED {changed} bloquea escritura automática")
    if conflicts > settings.lottery_sync_max_conflicts_per_run:
        raise SyncEnvironmentGuardError(f"CONFLICTS {conflicts} bloquean escritura automática")
    if invalid > settings.lottery_sync_max_invalid_per_run:
        raise SyncEnvironmentGuardError(f"INVALID {invalid} excede límite")
    _ = ambiguous
    _ = STAGING_ENV


def compute_lookback_range(*, max_draw_date, lookback_days: int | None = None, today=None):
    """Rango incremental: lookback desde última fecha o hoy."""
    from datetime import date, timedelta

    from zoneinfo import ZoneInfo

    lookback = lookback_days if lookback_days is not None else settings.lottery_sync_lookback_days
    max_range = settings.lottery_sync_max_range_days
    if today is None:
        today = datetime.now(ZoneInfo(settings.lottery_sync_timezone)).date()
    if isinstance(today, datetime):
        today = today.date()
    end = today
    if max_draw_date:
        start = max_draw_date - timedelta(days=lookback)
    else:
        start = end - timedelta(days=lookback)
    if (end - start).days > max_range:
        start = end - timedelta(days=max_range)
    return start, end
