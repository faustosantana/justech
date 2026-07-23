"""Lottery sync gate backup manager — persistent dumps for guarded_write.

Directory (host + container mount):
  /var/jaios/backups/lottery-sync-gates/

Creates pg_dump custom-format backups, validates age/size/checksum/DB name,
rotates old files, and exposes status for Admin Sync (no secrets).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

from app.config import settings
from app.services.lottery_sync_service import SyncEnvironmentGuardError

logger = logging.getLogger(__name__)

STABLE_NAME = "pre_lottery_sync.dump"
META_NAME = "pre_lottery_sync.meta.json"
MIN_BYTES = 1000


@dataclass
class GateBackupStatus:
    ok: bool
    path: str | None
    created_at: str | None
    age_hours: float | None
    max_age_hours: float
    expires_at: str | None
    size_bytes: int | None
    checksum_sha256_12: str | None
    database_name: str | None
    expected_database: str
    last_validated_at: str | None
    next_refresh_at: str | None
    alert: str | None
    retention_keep: int
    auto_refresh: bool


def gate_dir() -> Path:
    return Path(settings.lottery_sync_gate_backup_dir or "/var/jaios/backups/lottery-sync-gates")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_db_url(database_url: str) -> dict[str, str | int]:
    raw = (database_url or "").replace("postgresql+asyncpg://", "postgresql://")
    u = urlparse(raw)
    return {
        "host": u.hostname or "postgres",
        "port": int(u.port or 5432),
        "user": unquote(u.username or "jaios"),
        "password": unquote(u.password or ""),
        "database": (u.path or "/jaios").lstrip("/") or "jaios",
    }


def _sha256_file(path: Path, limit_bytes: int | None = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        remaining = limit_bytes
        while True:
            chunk = f.read(1024 * 1024 if remaining is None else min(1024 * 1024, remaining))
            if not chunk:
                break
            h.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
                if remaining <= 0:
                    break
    return h.hexdigest()


def _meta_path(directory: Path | None = None) -> Path:
    return (directory or gate_dir()) / META_NAME


def _stable_path(directory: Path | None = None) -> Path:
    return (directory or gate_dir()) / STABLE_NAME


def _write_meta(meta: dict, directory: Path | None = None) -> None:
    path = _meta_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _read_meta(directory: Path | None = None) -> dict:
    path = _meta_path(directory)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def list_timestamped_dumps(directory: Path | None = None) -> list[Path]:
    d = directory or gate_dir()
    if not d.exists():
        return []
    return sorted(d.glob("pre_lottery_sync_*.dump"), key=lambda p: p.stat().st_mtime)


def latest_gate_dump(directory: Path | None = None) -> Path | None:
    d = directory or gate_dir()
    stable = _stable_path(d)
    if stable.exists() and stable.stat().st_size >= MIN_BYTES:
        return stable
    stamped = list_timestamped_dumps(d)
    for p in reversed(stamped):
        if p.stat().st_size >= MIN_BYTES:
            return p
    # compat with previous ops path
    for compat in (
        Path("/tmp/pre_lottery_sync.dump"),
        Path("/var/jaios/lottery-sync-gate/pre_lottery_sync.dump"),
    ):
        if compat.exists() and compat.stat().st_size >= MIN_BYTES:
            return compat
    return None


def validate_gate_dump(
    path: Path,
    *,
    database_url: str,
    run_started_at: datetime | None = None,
) -> dict:
    """Validate dump; raises SyncEnvironmentGuardError on failure."""
    if not path.exists():
        raise SyncEnvironmentGuardError(f"Backup gate ausente: {path}")
    size = path.stat().st_size
    if size < MIN_BYTES:
        raise SyncEnvironmentGuardError(f"Backup gate inválido (tamaño {size} < {MIN_BYTES}): {path}")

    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_h = (_now() - mtime).total_seconds() / 3600
    max_age = float(settings.lottery_sync_backup_max_age_hours or 24)
    if age_h > max_age:
        raise SyncEnvironmentGuardError(
            f"Backup gate vencido ({age_h:.1f}h > {max_age}h): {path}"
        )

    if run_started_at is not None:
        started = run_started_at if run_started_at.tzinfo else run_started_at.replace(tzinfo=timezone.utc)
        if mtime > started:
            raise SyncEnvironmentGuardError(
                "Backup gate creado después del inicio de la corrida — rechazado"
            )

    expected_db = (settings.lottery_sync_allowed_database or "jaios").strip().lower()
    meta = _read_meta(path.parent if path.parent == gate_dir() else gate_dir())
    db_name = str(meta.get("database_name") or "").strip().lower()
    if db_name and db_name != expected_db:
        raise SyncEnvironmentGuardError(
            f"Backup gate pertenece a otra base ({db_name} != {expected_db})"
        )
    # If meta missing, infer from settings only when path is under gate dir
    if not db_name:
        parsed = _parse_db_url(database_url)
        db_name = str(parsed["database"]).lower()
        if db_name != expected_db:
            raise SyncEnvironmentGuardError(
                f"DATABASE_URL no coincide con allowlist ({db_name} != {expected_db})"
            )

    checksum = _sha256_file(path)
    stored = str(meta.get("checksum_sha256") or "")
    if stored and stored != checksum and path.name == STABLE_NAME:
        raise SyncEnvironmentGuardError("Checksum del backup gate no coincide con metadata")

    return {
        "path": str(path),
        "created_at": mtime.isoformat(),
        "age_hours": round(age_h, 3),
        "size_bytes": size,
        "checksum_sha256": checksum,
        "database_name": db_name or expected_db,
        "validated_at": _now().isoformat(),
    }


def prune_old_gates(*, keep: int | None = None, directory: Path | None = None) -> list[str]:
    d = directory or gate_dir()
    keep_n = int(keep if keep is not None else getattr(settings, "lottery_sync_gate_backup_keep", 7) or 7)
    stamped = list_timestamped_dumps(d)
    removed: list[str] = []
    for old in stamped[:-keep_n] if keep_n > 0 else stamped:
        try:
            old.unlink(missing_ok=True)
            removed.append(str(old))
        except OSError as exc:
            logger.warning("no se pudo rotar %s: %s", old, exc)
    return removed


def create_gate_dump(*, database_url: str, directory: Path | None = None) -> Path:
    """Create a fresh custom-format pg_dump under the gate directory."""
    d = directory or gate_dir()
    d.mkdir(parents=True, exist_ok=True)
    parsed = _parse_db_url(database_url)
    expected_db = (settings.lottery_sync_allowed_database or "jaios").strip().lower()
    if str(parsed["database"]).lower() != expected_db:
        raise SyncEnvironmentGuardError(
            f"No se crea gate dump: db={parsed['database']} != allowlist {expected_db}"
        )

    ts = _now().strftime("%Y%m%d_%H%M%S")
    stamped = d / f"pre_lottery_sync_{ts}.dump"
    tmp = d / f".pre_lottery_sync_{ts}.partial"

    env = os.environ.copy()
    if parsed["password"]:
        env["PGPASSWORD"] = str(parsed["password"])

    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        raise SyncEnvironmentGuardError(
            "pg_dump no está disponible en la imagen — no se puede auto-refrescar el backup gate"
        )

    cmd = [
        pg_dump,
        "-Fc",
        "-h",
        str(parsed["host"]),
        "-p",
        str(parsed["port"]),
        "-U",
        str(parsed["user"]),
        "-d",
        str(parsed["database"]),
        "-f",
        str(tmp),
    ]
    logger.info("creando backup gate en %s", stamped)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise SyncEnvironmentGuardError(
            f"pg_dump falló ({proc.returncode}): {(proc.stderr or proc.stdout or '')[:400]}"
        )
    if not tmp.exists() or tmp.stat().st_size < MIN_BYTES:
        tmp.unlink(missing_ok=True)
        raise SyncEnvironmentGuardError("pg_dump produjo un dump inválido")

    tmp.replace(stamped)
    stable = _stable_path(d)
    # copy to stable name (atomic replace)
    stable_tmp = d / f".{STABLE_NAME}.partial"
    shutil.copy2(stamped, stable_tmp)
    stable_tmp.replace(stable)

    checksum = _sha256_file(stable)
    meta = {
        "path": str(stable),
        "stamped_path": str(stamped),
        "created_at": _now().isoformat(),
        "size_bytes": stable.stat().st_size,
        "checksum_sha256": checksum,
        "database_name": str(parsed["database"]).lower(),
        "host": str(parsed["host"]),
        "port": int(parsed["port"]),
    }
    _write_meta(meta, d)
    prune_old_gates(directory=d)
    return stable


def ensure_fresh_gate_backup(
    *,
    database_url: str,
    run_started_at: datetime | None = None,
    force_refresh: bool = False,
) -> Path:
    """Return a validated dump path; auto-create when enabled and stale/missing."""
    auto = bool(getattr(settings, "lottery_sync_gate_backup_auto_refresh", True))
    path = latest_gate_dump()
    needs = force_refresh or path is None
    if path is not None and not force_refresh:
        try:
            validate_gate_dump(path, database_url=database_url, run_started_at=run_started_at)
            return path
        except SyncEnvironmentGuardError as exc:
            logger.warning("gate dump inválido/vencido: %s", exc)
            needs = True

    if needs:
        if not auto and not force_refresh:
            raise SyncEnvironmentGuardError(
                "Backup gate ausente o vencido y auto-refresh deshabilitado"
            )
        # Create BEFORE validating run_started_at constraint: creation must happen
        # prior to tick start. Callers should invoke ensure at tick start.
        path = create_gate_dump(database_url=database_url)
        # Do not pass run_started_at on freshly created dump in the same tick —
        # the dump is intentionally created at the beginning of the write window.
        validate_gate_dump(path, database_url=database_url, run_started_at=None)
        return path

    assert path is not None
    return path


def gate_backup_status(*, database_url: str | None = None) -> GateBackupStatus:
    """Status payload for Admin Sync / observability (no secrets)."""
    max_age = float(settings.lottery_sync_backup_max_age_hours or 24)
    expected = (settings.lottery_sync_allowed_database or "jaios").strip().lower()
    keep = int(getattr(settings, "lottery_sync_gate_backup_keep", 7) or 7)
    auto = bool(getattr(settings, "lottery_sync_gate_backup_auto_refresh", True))
    path = latest_gate_dump()
    url = database_url or settings.database_url
    if path is None:
        return GateBackupStatus(
            ok=False,
            path=None,
            created_at=None,
            age_hours=None,
            max_age_hours=max_age,
            expires_at=None,
            size_bytes=None,
            checksum_sha256_12=None,
            database_name=None,
            expected_database=expected,
            last_validated_at=None,
            next_refresh_at=None,
            alert="dump_ausente",
            retention_keep=keep,
            auto_refresh=auto,
        )
    try:
        info = validate_gate_dump(path, database_url=url, run_started_at=None)
        age = float(info["age_hours"])
        alert = None
        if age >= max_age * 0.75:
            alert = "dump_proximo_a_vencer"
        created = datetime.fromisoformat(info["created_at"])
        expires = created.timestamp() + max_age * 3600
        next_refresh = created.timestamp() + (max_age * 0.5 * 3600)
        return GateBackupStatus(
            ok=True,
            path=info["path"],
            created_at=info["created_at"],
            age_hours=age,
            max_age_hours=max_age,
            expires_at=datetime.fromtimestamp(expires, tz=timezone.utc).isoformat(),
            size_bytes=info["size_bytes"],
            checksum_sha256_12=str(info["checksum_sha256"])[:12],
            database_name=info["database_name"],
            expected_database=expected,
            last_validated_at=info["validated_at"],
            next_refresh_at=datetime.fromtimestamp(next_refresh, tz=timezone.utc).isoformat(),
            alert=alert,
            retention_keep=keep,
            auto_refresh=auto,
        )
    except SyncEnvironmentGuardError as exc:
        msg = str(exc).lower()
        alert = "dump_vencido" if "vencido" in msg else "dump_invalido"
        if "checksum" in msg:
            alert = "checksum_invalido"
        if "ausente" in msg:
            alert = "dump_ausente"
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age = (_now() - mtime).total_seconds() / 3600
        return GateBackupStatus(
            ok=False,
            path=str(path),
            created_at=mtime.isoformat(),
            age_hours=round(age, 3),
            max_age_hours=max_age,
            expires_at=None,
            size_bytes=path.stat().st_size,
            checksum_sha256_12=_sha256_file(path)[:12],
            database_name=_read_meta().get("database_name"),
            expected_database=expected,
            last_validated_at=_now().isoformat(),
            next_refresh_at=_now().isoformat(),
            alert=alert,
            retention_keep=keep,
            auto_refresh=auto,
        )


def gate_backup_status_dict(**kwargs) -> dict:
    return asdict(gate_backup_status(**kwargs))
