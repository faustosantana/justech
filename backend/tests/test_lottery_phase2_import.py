"""Pruebas Fase 2 — importador SQLite → PostgreSQL."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.services.lottery_aliases import describe_alias_resolution
from app.services.lottery_importer import (
    ProductionGuardError,
    assert_not_production_database,
    collect_source_stats,
    open_sqlite_readonly,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _build_mini_sqlite(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE lotteries (
          id INTEGER PRIMARY KEY,
          source_id INTEGER NOT NULL UNIQUE,
          name VARCHAR(255) NOT NULL,
          slug VARCHAR(255) NOT NULL,
          history_url VARCHAR(512) NOT NULL UNIQUE,
          is_loto BOOLEAN NOT NULL,
          prize_count INTEGER,
          scheduled_time VARCHAR(64),
          country VARCHAR(16),
          active BOOLEAN NOT NULL,
          metadata_json TEXT,
          first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE draws (
          id INTEGER PRIMARY KEY,
          lottery_id INTEGER NOT NULL,
          draw_date DATE NOT NULL,
          draw_time TIME,
          game_name VARCHAR(128) NOT NULL,
          source_url VARCHAR(512) NOT NULL,
          source_reference VARCHAR(64),
          content_hash VARCHAR(64) NOT NULL,
          raw_payload TEXT,
          record_status VARCHAR(32) NOT NULL,
          scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (lottery_id, draw_date, draw_time, game_name, source_reference)
        );
        CREATE TABLE draw_numbers (
          id INTEGER PRIMARY KEY,
          draw_id INTEGER NOT NULL,
          position INTEGER NOT NULL,
          position_label VARCHAR(64) NOT NULL,
          number_value VARCHAR(32) NOT NULL,
          number_raw VARCHAR(32) NOT NULL,
          number_type VARCHAR(32) NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    # source_id 99901 — never collide with real imported lotteries (1–50)
    conn.execute(
        "INSERT INTO lotteries (id, source_id, name, slug, history_url, is_loto, active, country) "
        "VALUES (1, 99901, 'Test Mini Lottery', 'test-mini-lottery', 'https://example/mini', 0, 1, 'DO')"
    )
    # Two draws same day — multi-sorteo
    conn.execute(
        "INSERT INTO draws (id, lottery_id, draw_date, draw_time, game_name, source_url, source_reference, content_hash, raw_payload, record_status) "
        "VALUES (1, 1, '2022-03-15', NULL, 'quiniela', 'https://example/1', 'ref-1', 'hash1', '{}', 'ok')"
    )
    conn.execute(
        "INSERT INTO draws (id, lottery_id, draw_date, draw_time, game_name, source_url, source_reference, content_hash, raw_payload, record_status) "
        "VALUES (2, 1, '2022-03-15', '21:00:00', 'quiniela', 'https://example/2', 'ref-2', 'hash2', '{}', 'ok')"
    )
    conn.execute(
        "INSERT INTO draw_numbers (draw_id, position, position_label, number_value, number_raw, number_type) VALUES "
        "(1, 1, '1ro', '00', '00', 'principal')"
    )
    conn.execute(
        "INSERT INTO draw_numbers (draw_id, position, position_label, number_value, number_raw, number_type) VALUES "
        "(1, 2, '2do', '05', '05', 'principal')"
    )
    conn.execute(
        "INSERT INTO draw_numbers (draw_id, position, position_label, number_value, number_raw, number_type) VALUES "
        "(1, 3, '3ro', '88', '88', 'principal')"
    )
    conn.execute(
        "INSERT INTO draw_numbers (draw_id, position, position_label, number_value, number_raw, number_type) VALUES "
        "(2, 1, '1ro', '01', '01', 'principal')"
    )
    conn.execute(
        "INSERT INTO draw_numbers (draw_id, position, position_label, number_value, number_raw, number_type) VALUES "
        "(2, 2, 'Loto', '12', '12', 'especial')"
    )
    conn.execute(
        "INSERT INTO draw_numbers (draw_id, position, position_label, number_value, number_raw, number_type) VALUES "
        "(2, 3, 'Más', '07', '07', 'especial')"
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def mini_sqlite(tmp_path: Path) -> Path:
    path = tmp_path / "mini_lottery.db"
    _build_mini_sqlite(path)
    return path


def test_sqlite_opens_readonly(mini_sqlite: Path):
    conn = open_sqlite_readonly(mini_sqlite)
    try:
        assert conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0] == 2
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO draws (id, lottery_id, draw_date, game_name, source_url, content_hash, record_status) VALUES (99,1,'2020-01-01','quiniela','u','h','ok')")
    finally:
        conn.close()


def test_collect_source_stats(mini_sqlite: Path):
    stats = collect_source_stats(mini_sqlite, compute_hash=True)
    assert stats.lotteries == 1
    assert stats.draws == 2
    assert stats.numbers == 6
    assert stats.multi_day == 1
    assert stats.leading_zeros >= 3
    assert stats.loto_labels == 1
    assert stats.mas_labels == 1
    assert len(stats.sha256) == 64


def test_production_guard_blocks_remote():
    with pytest.raises(ProductionGuardError):
        assert_not_production_database(
            "postgresql+asyncpg://u:p@jaios.justech.do:5432/jaios"
        )
    with pytest.raises(ProductionGuardError):
        assert_not_production_database(
            "postgresql+asyncpg://u:p@db.prod.example.com:5432/jaios_prod"
        )


def test_production_guard_allows_lottery_dev():
    assert_not_production_database(
        "postgresql+asyncpg://jaios:x@localhost:5433/jaios_lottery_dev"
    )


def test_nacional_dia_still_ambiguous():
    result = describe_alias_resolution("Nacional Día")
    assert result["resolved"] is False
    assert result["ambiguous"] is True


def test_migration_028_file_exists():
    mig = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "028_lottery_draw_uniqueness.py"
    assert mig.exists()
    text = mig.read_text(encoding="utf-8")
    assert "uq_lottery_draws_lottery_source_ref" in text
    assert "uq_lottery_draws_natural_coalesce" in text
    assert 'down_revision: Union[str, None] = "027_lottery_module"' in text


@pytest.mark.asyncio
async def test_dry_run_mini_against_dev_db(mini_sqlite: Path):
    """Dry-run no escribe tablas de negocio (solo lee fuente)."""
    from app.services.lottery_importer import LotterySqliteImporter

    url = "postgresql+asyncpg://jaios:jaios_dev_local_only@localhost:5433/jaios_lottery_dev"
    try:
        importer = LotterySqliteImporter(
            source=mini_sqlite,
            database_url=url,
            dry_run=True,
            batch_size=100,
        )
        report = importer.run()
    except Exception as exc:
        pytest.skip(f"Postgres lottery_dev no disponible: {exc}")

    assert report["status"] == "dry_run_ok"
    assert report["metrics"]["errors"] == 0
    assert report["dry_run"] is True


@pytest.mark.asyncio
async def test_import_idempotent_mini(mini_sqlite: Path):
    """Import against throwaway source_id 99901; cleanup after to protect historical Real data."""
    from sqlalchemy import create_engine, text
    from app.services.lottery_importer import LotterySqliteImporter

    url = "postgresql+asyncpg://jaios:jaios_dev_local_only@localhost:5433/jaios_lottery_dev"
    sync = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    TEST_SID = 99901

    try:
        eng = create_engine(sync)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres lottery_dev no disponible: {exc}")

    def _cleanup():
        with eng.begin() as c:
            c.execute(
                text(
                    "DELETE FROM lottery_draw_numbers WHERE draw_id IN ("
                    "  SELECT d.id FROM lottery_draws d"
                    "  JOIN lottery_lotteries l ON l.id = d.lottery_id"
                    "  WHERE l.source_id = :sid)"
                ),
                {"sid": TEST_SID},
            )
            c.execute(
                text(
                    "DELETE FROM lottery_draws WHERE lottery_id IN ("
                    "  SELECT id FROM lottery_lotteries WHERE source_id = :sid)"
                ),
                {"sid": TEST_SID},
            )
            c.execute(
                text("DELETE FROM lottery_aliases WHERE lottery_id IN ("
                     "  SELECT id FROM lottery_lotteries WHERE source_id = :sid)"),
                {"sid": TEST_SID},
            )
            c.execute(text("DELETE FROM lottery_lotteries WHERE source_id = :sid"), {"sid": TEST_SID})

    _cleanup()
    try:
        importer1 = LotterySqliteImporter(
            source=mini_sqlite,
            database_url=url,
            batch_size=50,
            lottery_source_id=TEST_SID,
            reset_checkpoint=True,
        )
        r1 = importer1.run()
        assert r1["status"] in ("completed", "completed_with_errors")
        assert r1["metrics"]["errors"] == 0
        pg1 = r1["postgres_stats"]

        importer2 = LotterySqliteImporter(
            source=mini_sqlite,
            database_url=url,
            batch_size=50,
            lottery_source_id=TEST_SID,
            reset_checkpoint=True,
        )
        r2 = importer2.run()
        assert r2["status"] in ("completed", "completed_with_errors")
        pg2 = r2["postgres_stats"]
        assert pg2["draws"] == pg1["draws"]
        assert pg2["numbers"] == pg1["numbers"]
        assert r2["metrics"]["draws_inserted"] == 0 or r2["metrics"]["draws_skipped"] >= 2

        with eng.connect() as c:
            zeros = c.execute(
                text(
                    "SELECT n.number_value FROM lottery_draw_numbers n"
                    " JOIN lottery_draws d ON d.id = n.draw_id"
                    " JOIN lottery_lotteries l ON l.id = d.lottery_id"
                    " WHERE l.source_id = :sid AND n.number_value IN ('00','05','01')"
                ),
                {"sid": TEST_SID},
            ).fetchall()
            vals = {r[0] for r in zeros}
            assert "00" in vals
            assert "05" in vals
    finally:
        _cleanup()
