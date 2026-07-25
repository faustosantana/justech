"""Pre-J11A — configuración SQLite tipada; sin paths de laptop hardcodeados."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import pytest

from app.config import get_settings, settings
from app.lottery.sync_sqlite_config import (
    LotterySyncSqliteConfigError,
    resolve_sqlite_snapshot_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
HARDCODED_ABS_RE = re.compile(
    r"/Users/faustosantana/Projects/(?:lottery-history-scraper|jaios-lottery)/"
)


@pytest.fixture(autouse=True)
def _clear_settings(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("LOTTERY_SYNC_SQLITE_PATH", raising=False)
    monkeypatch.setattr(settings, "lottery_sync_sqlite_path", "")
    yield
    get_settings.cache_clear()


def test_resolve_explicit_path(tmp_path: Path):
    db = tmp_path / "snap.db"
    db.write_bytes(b"SQLite format 3\x00")
    got = resolve_sqlite_snapshot_path(db)
    assert got == db.resolve()


def test_resolve_from_settings(tmp_path: Path, monkeypatch):
    db = tmp_path / "env.db"
    db.write_bytes(b"SQLite format 3\x00")
    monkeypatch.setattr(settings, "lottery_sync_sqlite_path", str(db))
    got = resolve_sqlite_snapshot_path()
    assert got == db.resolve()


def test_resolve_from_env(tmp_path: Path, monkeypatch):
    db = tmp_path / "e.db"
    db.write_bytes(b"SQLite format 3\x00")
    monkeypatch.setenv("LOTTERY_SYNC_SQLITE_PATH", str(db))
    # settings empty; env fallback inside resolver
    monkeypatch.setattr(settings, "lottery_sync_sqlite_path", "")
    got = resolve_sqlite_snapshot_path()
    assert got == db.resolve()


def test_missing_config_raises():
    with pytest.raises(LotterySyncSqliteConfigError, match="LOTTERY_SYNC_SQLITE_PATH"):
        resolve_sqlite_snapshot_path()


def test_nonexistent_path_raises(tmp_path: Path):
    missing = tmp_path / "missing.db"
    with pytest.raises(LotterySyncSqliteConfigError, match="no existe"):
        resolve_sqlite_snapshot_path(missing)


def test_unreadable_path_raises(tmp_path: Path):
    db = tmp_path / "locked.db"
    db.write_bytes(b"SQLite format 3\x00")
    db.chmod(0)
    try:
        with pytest.raises(LotterySyncSqliteConfigError, match="permiso"):
            resolve_sqlite_snapshot_path(db)
    finally:
        db.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_must_exist_false_allows_missing(tmp_path: Path):
    missing = tmp_path / "future.db"
    got = resolve_sqlite_snapshot_path(missing, must_exist=False, must_be_readable=False)
    assert got == missing.resolve()


def test_no_hardcoded_laptop_sqlite_in_runtime_code():
    """Regresión: callers de sync no deben embeber paths absolutos de máquina."""
    targets = [
        REPO_ROOT / "backend/app/api/v1/lottery.py",
        REPO_ROOT / "backend/app/services/lottery_sync_service.py",
        REPO_ROOT / "backend/app/services/lottery_sync_writer.py",
        REPO_ROOT / "backend/app/lottery/sync_sqlite_config.py",
    ]
    offenders: list[str] = []
    for path in targets:
        text = path.read_text(encoding="utf-8")
        if HARDCODED_ABS_RE.search(text) or "/Users/faustosantana/Projects/lottery-history-scraper" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"paths hardcodeados: {offenders}"


def test_isolation_uses_temp_db(tmp_path: Path, monkeypatch):
    """Las pruebas usan DB temporal — no producción."""
    db = tmp_path / "test_only.db"
    db.write_bytes(b"SQLite format 3\x00")
    monkeypatch.setenv("LOTTERY_SYNC_SQLITE_PATH", str(db))
    monkeypatch.setattr(settings, "lottery_sync_sqlite_path", str(db))
    assert "jaios" not in str(resolve_sqlite_snapshot_path()).lower() or "test" in str(db)
    assert resolve_sqlite_snapshot_path().parent == tmp_path
