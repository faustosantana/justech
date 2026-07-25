"""Resolución central del path SQLite de snapshot para sync (Pre-J11A / TD-001).

Ningún path absoluto de máquina debe vivir en callers. Prioridad:

1. Argumento explícito (`sqlite_path`)
2. Variable de entorno / Settings (`LOTTERY_SYNC_SQLITE_PATH`)
3. Error claro — sin fallback silencioso a rutas productivas o de laptop
"""

from __future__ import annotations

import os
from pathlib import Path

from app.config import settings


class LotterySyncSqliteConfigError(ValueError):
    """Configuración SQLite ausente o inválida."""


def _configured_path_str() -> str:
    raw = (getattr(settings, "lottery_sync_sqlite_path", None) or "").strip()
    if raw:
        return raw
    return (os.environ.get("LOTTERY_SYNC_SQLITE_PATH") or "").strip()


def resolve_sqlite_snapshot_path(
    explicit: Path | str | None = None,
    *,
    must_exist: bool = True,
    must_be_readable: bool = True,
) -> Path:
    """Devuelve un Path absoluto validado para el snapshot SQLite de sync.

    Raises:
        LotterySyncSqliteConfigError: si falta config o el path no es usable.
    """
    if explicit is not None and str(explicit).strip():
        path = Path(str(explicit)).expanduser()
    else:
        configured = _configured_path_str()
        if not configured:
            raise LotterySyncSqliteConfigError(
                "Falta la configuración obligatoria LOTTERY_SYNC_SQLITE_PATH "
                "(settings.lottery_sync_sqlite_path). No hay fallback a rutas locales."
            )
        path = Path(configured).expanduser()

    if not path.is_absolute():
        path = path.resolve()
    else:
        path = path.resolve(strict=False)

    if must_exist and not path.exists():
        raise LotterySyncSqliteConfigError(
            f"El path SQLite configurado no existe: {path}"
        )
    if must_exist and not path.is_file():
        raise LotterySyncSqliteConfigError(
            f"El path SQLite configurado no es un archivo: {path}"
        )
    if must_be_readable and path.exists() and not os.access(path, os.R_OK):
        raise LotterySyncSqliteConfigError(
            f"Sin permiso de lectura sobre el SQLite configurado: {path}"
        )
    return path
