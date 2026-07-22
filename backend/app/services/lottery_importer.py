"""Importador SQLite → PostgreSQL para el módulo lottery.

Uso vía CLI: backend/scripts/import_lottery_sqlite.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.lottery import (
    LotteryAlias,
    LotteryDraw,
    LotteryDrawNumber,
    LotteryImportError,
    LotteryImportRun,
    LotteryLottery,
)
from app.services.lottery_aliases import normalize_lottery_alias
from app.services.lottery_permissions import CONFIRMED_PRIORITY_SOURCE_IDS

# Aliases confirmados a sembrar (normalized → source_id). Sin Nacional Día.
CONFIRMED_ALIAS_SEEDS: dict[str, int] = {
    **CONFIRMED_PRIORITY_SOURCE_IDS,
    "quiniela real": 13,
    "new york 2.30": 16,
    "new york 2 30": 16,
    "quiniela loteka": 6,
    "quiniela leidsa": 5,
    "loteria nacional": 4,
    "lotería nacional": 4,
    "new york 10.30": 17,
    "new york 10 30": 17,
}

PRODUCTION_HOST_MARKERS = (
    "jaios.justech.do",
    "justech.do",
    "prod",
    "production",
    "rds.amazonaws.com",
)
PRODUCTION_DB_MARKERS = (
    "jaios_prod",
    "production",
    "prod_jaios",
)


class ProductionGuardError(RuntimeError):
    pass


class ImporterError(RuntimeError):
    pass


def assert_not_production_database(database_url: str) -> None:
    """Detiene import si la URL parece Producción."""
    parsed = urlparse(database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    ))
    host = (parsed.hostname or "").lower()
    db = (parsed.path or "").lstrip("/").lower()
    port = parsed.port

    reasons: list[str] = []
    for marker in PRODUCTION_HOST_MARKERS:
        if marker in host and "localhost" not in host and host not in ("127.0.0.1", "::1"):
            reasons.append(f"host contiene '{marker}'")
    for marker in PRODUCTION_DB_MARKERS:
        if marker in db:
            reasons.append(f"database contiene '{marker}'")
    if host not in ("localhost", "127.0.0.1", "::1", "") and "lottery" not in db and "dev" not in db:
        # Allow docker service names like 'postgres' only with explicit _dev / lottery in db name
        if host in ("postgres", "db"):
            if "dev" not in db and "lottery" not in db and db != "jaios":
                pass  # compose default jaios on local docker is gray area — require lottery_dev preferred
        elif "justech" in host or "amazonaws" in host:
            reasons.append(f"host remoto sospechoso: {host}")

    # Explicit allowlist for this phase's known local target
    allowed = (
        (host in ("localhost", "127.0.0.1") and port == 5433 and "lottery" in db)
        or (host in ("localhost", "127.0.0.1") and port == 5434 and "lottery_staging" in db)
        or (host in ("localhost", "127.0.0.1") and "lottery_dev" in db)
        or (host in ("localhost", "127.0.0.1") and "lottery_staging" in db)
        or (host in ("localhost", "127.0.0.1") and db.endswith("_dev"))
        or (host in ("localhost", "127.0.0.1") and db.endswith("_staging"))
    )
    if reasons and not allowed:
        raise ProductionGuardError(
            "Protección anti-Producción: " + "; ".join(reasons) + f" (db={db}, host={host})"
        )
    if not allowed and host not in ("localhost", "127.0.0.1", "::1"):
        raise ProductionGuardError(
            f"DATABASE_URL no está en la allowlist de desarrollo (host={host}, db={db}, port={port})"
        )


def open_sqlite_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def file_sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            data = fh.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    return re.sub(r"\s+", " ", text)


def slugify(name: str, source_id: int) -> str:
    base = normalize_name(name).replace(" ", "-")
    base = re.sub(r"[^a-z0-9\-]+", "", base)
    return f"{base or 'lottery'}-{source_id}"


def parse_time(value: Any) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_raw_payload(raw: Any) -> dict | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"raw": str(raw)}


def current_git_commit() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[3],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()[:64]
    except Exception:
        return None


@dataclass
class ImportMetrics:
    lotteries_read: int = 0
    lotteries_inserted: int = 0
    lotteries_updated: int = 0
    draws_read: int = 0
    draws_inserted: int = 0
    draws_updated: int = 0
    draws_skipped: int = 0
    numbers_read: int = 0
    numbers_inserted: int = 0
    numbers_updated: int = 0
    aliases_upserted: int = 0
    errors: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "lotteries_read": self.lotteries_read,
            "lotteries_inserted": self.lotteries_inserted,
            "lotteries_updated": self.lotteries_updated,
            "draws_read": self.draws_read,
            "draws_inserted": self.draws_inserted,
            "draws_updated": self.draws_updated,
            "draws_skipped": self.draws_skipped,
            "numbers_read": self.numbers_read,
            "numbers_inserted": self.numbers_inserted,
            "numbers_updated": self.numbers_updated,
            "aliases_upserted": self.aliases_upserted,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class SourceStats:
    lotteries: int
    draws: int
    numbers: int
    with_results: int
    min_date: str | None
    max_date: str | None
    leading_zeros: int
    loto_labels: int
    mas_labels: int
    multi_day: int
    null_time: int
    null_ref: int
    dup_ref: int
    file_size: int
    file_mtime: str
    sha256: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def collect_source_stats(sqlite_path: Path, *, compute_hash: bool = True) -> SourceStats:
    conn = open_sqlite_readonly(sqlite_path)
    try:
        lotteries = conn.execute("SELECT COUNT(*) FROM lotteries").fetchone()[0]
        draws = conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0]
        numbers = conn.execute("SELECT COUNT(*) FROM draw_numbers").fetchone()[0]
        with_results = conn.execute(
            "SELECT COUNT(DISTINCT lottery_id) FROM draws"
        ).fetchone()[0]
        row = conn.execute("SELECT MIN(draw_date), MAX(draw_date) FROM draws").fetchone()
        leading_zeros = conn.execute(
            "SELECT COUNT(*) FROM draw_numbers WHERE number_value GLOB '0*' AND length(number_value)=2"
        ).fetchone()[0]
        loto_labels = conn.execute(
            "SELECT COUNT(*) FROM draw_numbers WHERE lower(position_label) LIKE '%loto%'"
        ).fetchone()[0]
        mas_labels = conn.execute(
            "SELECT COUNT(*) FROM draw_numbers WHERE lower(position_label) LIKE '%más%' OR lower(position_label) LIKE '%mas%'"
        ).fetchone()[0]
        multi_day = conn.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT lottery_id, draw_date FROM draws
              GROUP BY lottery_id, draw_date HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        null_time = conn.execute(
            "SELECT COUNT(*) FROM draws WHERE draw_time IS NULL OR draw_time=''"
        ).fetchone()[0]
        null_ref = conn.execute(
            "SELECT COUNT(*) FROM draws WHERE source_reference IS NULL OR source_reference=''"
        ).fetchone()[0]
        dup_ref = conn.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT source_reference FROM draws
              WHERE source_reference IS NOT NULL AND source_reference != ''
              GROUP BY source_reference HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
    finally:
        conn.close()

    st = sqlite_path.stat()
    return SourceStats(
        lotteries=lotteries,
        draws=draws,
        numbers=numbers,
        with_results=with_results,
        min_date=str(row[0]) if row and row[0] else None,
        max_date=str(row[1]) if row and row[1] else None,
        leading_zeros=leading_zeros,
        loto_labels=loto_labels,
        mas_labels=mas_labels,
        multi_day=multi_day,
        null_time=null_time,
        null_ref=null_ref,
        dup_ref=dup_ref,
        file_size=st.st_size,
        file_mtime=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        sha256=file_sha256(sqlite_path) if compute_hash else "",
    )


class LotterySqliteImporter:
    def __init__(
        self,
        *,
        source: Path,
        database_url: str,
        batch_size: int = 1000,
        dry_run: bool = False,
        resume: bool = False,
        validate_only: bool = False,
        lottery_source_id: int | None = None,
        limit: int | None = None,
        reset_checkpoint: bool = False,
    ):
        self.source = source.resolve()
        self.database_url = database_url
        self.batch_size = max(1, batch_size)
        self.dry_run = dry_run
        self.resume = resume
        self.validate_only = validate_only
        self.lottery_source_id = lottery_source_id
        self.limit = limit
        self.reset_checkpoint = reset_checkpoint
        self.metrics = ImportMetrics()
        self.source_stats: SourceStats | None = None
        self.run_id: uuid.UUID | None = None

        if not self.source.is_file():
            raise ImporterError(f"Fuente no encontrada: {self.source}")

        assert_not_production_database(self.database_url)

        sync_url = self.database_url
        if sync_url.startswith("postgresql+asyncpg://"):
            sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        self.engine = create_engine(sync_url, future=True)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def run(self) -> dict[str, Any]:
        self.source_stats = collect_source_stats(self.source, compute_hash=True)
        report: dict[str, Any] = {
            "source": str(self.source),
            "source_stats": self.source_stats.as_dict(),
            "dry_run": self.dry_run,
            "validate_only": self.validate_only,
            "resume": self.resume,
            "batch_size": self.batch_size,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.validate_only:
            report["status"] = "validated_source_only"
            report["metrics"] = self.metrics.as_dict()
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            return report

        if self.dry_run:
            self._dry_run_scan()
            report["status"] = "dry_run_ok" if self.metrics.errors == 0 else "dry_run_failed"
            report["metrics"] = self.metrics.as_dict()
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            return report

        with self.Session() as session:
            run = self._start_run(session)
            self.run_id = run.id
            try:
                self._import_lotteries(session)
                self._seed_aliases(session)
                self._import_draws_and_numbers(session, run)
                self._refresh_lottery_aggregates(session)
                status = "completed" if self.metrics.errors == 0 else "completed_with_errors"
                run.status = status
                run.finished_at = datetime.now(timezone.utc)
                run.lotteries_count = self.metrics.lotteries_inserted + self.metrics.lotteries_updated
                run.draws_count = self.metrics.draws_inserted + self.metrics.draws_updated
                run.numbers_count = self.metrics.numbers_inserted + self.metrics.numbers_updated
                run.errors_count = self.metrics.errors
                run.summary = {
                    "metrics": self.metrics.as_dict(),
                    "source_stats": self.source_stats.as_dict(),
                }
                session.commit()
            except Exception as exc:
                session.rollback()
                with self.Session() as s2:
                    run2 = s2.get(LotteryImportRun, self.run_id)
                    if run2:
                        run2.status = "failed"
                        run2.finished_at = datetime.now(timezone.utc)
                        run2.errors_count = self.metrics.errors + 1
                        run2.summary = {"error": str(exc), "metrics": self.metrics.as_dict()}
                        s2.add(
                            LotteryImportError(
                                import_run_id=self.run_id,
                                stage="fatal",
                                message=str(exc),
                                context={},
                            )
                        )
                        s2.commit()
                raise

        report["status"] = "completed" if self.metrics.errors == 0 else "completed_with_errors"
        report["run_id"] = str(self.run_id)
        report["metrics"] = self.metrics.as_dict()
        report["postgres_stats"] = self._postgres_stats()
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        return report

    def _start_run(self, session: Session) -> LotteryImportRun:
        checkpoint: dict[str, Any] = {}
        if self.resume and not self.reset_checkpoint:
            prev = session.execute(
                select(LotteryImportRun)
                .where(LotteryImportRun.mode == "sqlite_import")
                .where(LotteryImportRun.dry_run.is_(False))
                .order_by(LotteryImportRun.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if prev and prev.checkpoint:
                checkpoint = dict(prev.checkpoint)

        if self.reset_checkpoint:
            checkpoint = {}

        run = LotteryImportRun(
            mode="sqlite_import",
            status="running",
            source_path=str(self.source),
            source_path_hash=self.source_stats.sha256 if self.source_stats else None,
            dry_run=False,
            resume=self.resume,
            batch_size=self.batch_size,
            git_commit=current_git_commit(),
            app_version="0.2.0-phase2",
            started_at=datetime.now(timezone.utc),
            checkpoint=checkpoint,
            summary={},
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run

    def _dry_run_scan(self) -> None:
        conn = open_sqlite_readonly(self.source)
        try:
            self.metrics.lotteries_read = conn.execute("SELECT COUNT(*) FROM lotteries").fetchone()[0]
            q = "SELECT COUNT(*) FROM draws"
            params: list[Any] = []
            if self.lottery_source_id is not None:
                q = """
                    SELECT COUNT(*) FROM draws d
                    JOIN lotteries l ON l.id = d.lottery_id
                    WHERE l.source_id = ?
                """
                params = [self.lottery_source_id]
            self.metrics.draws_read = conn.execute(q, params).fetchone()[0]
            if self.limit is not None:
                self.metrics.draws_read = min(self.metrics.draws_read, self.limit)
            # Validate sample rows
            sample = conn.execute(
                """
                SELECT d.*, l.source_id AS lottery_source_id
                FROM draws d JOIN lotteries l ON l.id = d.lottery_id
                LIMIT 50
                """
            ).fetchall()
            for row in sample:
                if not row["source_reference"]:
                    self.metrics.errors += 1
                    self.metrics.warnings.append("draw sin source_reference en muestra")
                try:
                    parse_date(row["draw_date"])
                except Exception as exc:
                    self.metrics.errors += 1
                    self.metrics.warnings.append(f"fecha inválida: {exc}")
            if self.source_stats and self.source_stats.dup_ref:
                self.metrics.errors += 1
                self.metrics.warnings.append("source_reference duplicados en SQLite")
            # Nacional Día must remain unresolved
            from app.services.lottery_aliases import describe_alias_resolution

            amb = describe_alias_resolution("Nacional Día")
            if amb.get("resolved"):
                self.metrics.errors += 1
                self.metrics.warnings.append("Nacional Día no debe resolverse")
        finally:
            conn.close()

    def _import_lotteries(self, session: Session) -> None:
        conn = open_sqlite_readonly(self.source)
        try:
            rows = conn.execute("SELECT * FROM lotteries ORDER BY source_id").fetchall()
        finally:
            conn.close()

        for row in rows:
            self.metrics.lotteries_read += 1
            source_id = int(row["source_id"])
            if self.lottery_source_id is not None and source_id != self.lottery_source_id:
                continue
            name = row["name"]
            normalized = normalize_name(name)
            slug = slugify(name, source_id)
            draw_count = 0
            first_d = last_d = None
            # Aggregates computed later; quick count from sqlite optional
            existing = session.execute(
                select(LotteryLottery).where(LotteryLottery.source_id == source_id)
            ).scalar_one_or_none()
            is_aggregate = source_id == 30
            values = {
                "name": name,
                "normalized_name": normalized,
                "slug": slug,
                "country": row["country"] or "DO",
                "timezone": "America/Santo_Domingo",
                "active": bool(row["active"]) and not is_aggregate,
                "is_loto": bool(row["is_loto"]),
                "is_aggregate": is_aggregate,
                "source_url": row["history_url"],
            }
            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
                self.metrics.lotteries_updated += 1
            else:
                session.add(
                    LotteryLottery(
                        source_id=source_id,
                        draw_count=draw_count,
                        first_draw_date=first_d,
                        last_draw_date=last_d,
                        **values,
                    )
                )
                self.metrics.lotteries_inserted += 1
        session.commit()

    def _seed_aliases(self, session: Session) -> None:
        by_source = {
            lot.source_id: lot
            for lot in session.execute(select(LotteryLottery)).scalars().all()
        }
        # Deduplicar por normalized_alias (p.ej. loteria/lotería real → misma clave)
        unique_aliases: dict[str, tuple[str, int]] = {}
        for alias, source_id in CONFIRMED_ALIAS_SEEDS.items():
            normalized = normalize_lottery_alias(alias)
            unique_aliases.setdefault(normalized, (alias, source_id))

        for normalized, (alias, source_id) in unique_aliases.items():
            lot = by_source.get(source_id)
            if not lot:
                continue
            existing = session.execute(
                select(LotteryAlias).where(LotteryAlias.normalized_alias == normalized)
            ).scalar_one_or_none()
            if existing:
                existing.lottery_id = lot.id
                existing.alias = alias
                existing.is_primary = normalized in ("real", "loteka", "leidsa", "nacional noche")
            else:
                session.add(
                    LotteryAlias(
                        lottery_id=lot.id,
                        alias=alias,
                        normalized_alias=normalized,
                        is_primary=normalized in ("real", "loteka", "leidsa", "nacional noche"),
                    )
                )
            self.metrics.aliases_upserted += 1
        session.commit()

    def _import_draws_and_numbers(self, session: Session, run: LotteryImportRun) -> None:
        lottery_map = {
            lot.source_id: lot.id
            for lot in session.execute(select(LotteryLottery)).scalars().all()
        }
        # Also map sqlite lottery.id → source_id
        conn = open_sqlite_readonly(self.source)
        try:
            sqlite_id_to_source = {
                int(r["id"]): int(r["source_id"])
                for r in conn.execute("SELECT id, source_id FROM lotteries").fetchall()
            }

            last_sqlite_draw_id = int(run.checkpoint.get("last_sqlite_draw_id") or 0)
            sql = """
                SELECT d.*, l.source_id AS lottery_source_id
                FROM draws d
                JOIN lotteries l ON l.id = d.lottery_id
                WHERE d.id > ?
            """
            params: list[Any] = [last_sqlite_draw_id]
            if self.lottery_source_id is not None:
                sql += " AND l.source_id = ?"
                params.append(self.lottery_source_id)
            sql += " ORDER BY d.id ASC"
            if self.limit is not None:
                sql += f" LIMIT {int(self.limit)}"

            cursor = conn.execute(sql, params)
            batch: list[sqlite3.Row] = []
            processed = 0
            while True:
                rows = cursor.fetchmany(self.batch_size)
                if not rows:
                    break
                batch = list(rows)
                try:
                    self._process_draw_batch(session, batch, lottery_map, sqlite_id_to_source, conn)
                    last_id = int(batch[-1]["id"])
                    run.checkpoint = {
                        **dict(run.checkpoint or {}),
                        "last_sqlite_draw_id": last_id,
                        "processed": processed + len(batch),
                    }
                    session.add(run)
                    session.commit()
                    processed += len(batch)
                    if processed % (self.batch_size * 10) == 0 or len(batch) < self.batch_size:
                        print(f"… imported draws checkpoint={last_id} processed={processed}", flush=True)
                except Exception as exc:
                    session.rollback()
                    self.metrics.errors += 1
                    session.add(
                        LotteryImportError(
                            import_run_id=run.id,
                            stage="draws_batch",
                            message=str(exc),
                            context={
                                "first_id": int(batch[0]["id"]) if batch else None,
                                "last_id": int(batch[-1]["id"]) if batch else None,
                            },
                        )
                    )
                    session.commit()
                    # No continuar tras fallo de lote (seguro)
                    raise
        finally:
            conn.close()

    def _process_draw_batch(
        self,
        session: Session,
        batch: list[sqlite3.Row],
        lottery_map: dict[int, uuid.UUID],
        sqlite_id_to_source: dict[int, int],
        sqlite_conn: sqlite3.Connection,
    ) -> None:
        refs = [r["source_reference"] for r in batch if r["source_reference"]]
        existing_by_ref: dict[tuple[uuid.UUID, str], LotteryDraw] = {}
        if refs:
            lottery_ids = {lottery_map[int(r["lottery_source_id"])] for r in batch if int(r["lottery_source_id"]) in lottery_map}
            found = session.execute(
                select(LotteryDraw).where(
                    LotteryDraw.lottery_id.in_(lottery_ids),
                    LotteryDraw.source_reference.in_(refs),
                )
            ).scalars().all()
            for d in found:
                if d.source_reference:
                    existing_by_ref[(d.lottery_id, d.source_reference)] = d

        sqlite_draw_ids = [int(r["id"]) for r in batch]
        numbers_by_sqlite_draw: dict[int, list[sqlite3.Row]] = {i: [] for i in sqlite_draw_ids}
        placeholders = ",".join("?" for _ in sqlite_draw_ids)
        for n in sqlite_conn.execute(
            f"SELECT * FROM draw_numbers WHERE draw_id IN ({placeholders}) ORDER BY draw_id, position, number_type",
            sqlite_draw_ids,
        ).fetchall():
            numbers_by_sqlite_draw[int(n["draw_id"])].append(n)

        pending_new: list[tuple[sqlite3.Row, LotteryDraw]] = []
        pending_existing: list[tuple[sqlite3.Row, LotteryDraw]] = []

        for row in batch:
            self.metrics.draws_read += 1
            source_id = int(row["lottery_source_id"])
            lottery_uuid = lottery_map.get(source_id)
            if not lottery_uuid:
                self.metrics.errors += 1
                continue

            ref = row["source_reference"]
            draw_date = parse_date(row["draw_date"])
            draw_time = parse_time(row["draw_time"])
            game_name = row["game_name"] or "quiniela"
            content_hash = row["content_hash"]
            source_url = row["source_url"]
            scraped_at = parse_datetime(row["scraped_at"])
            raw_payload = parse_raw_payload(row["raw_payload"])

            existing = existing_by_ref.get((lottery_uuid, ref)) if ref else None

            if existing:
                changed = False
                if existing.content_hash != content_hash:
                    session.add(
                        LotteryImportError(
                            import_run_id=self.run_id,
                            stage="draw_conflict",
                            message="content_hash distinto para mismo source_reference",
                            context={
                                "source_reference": ref,
                                "old": existing.content_hash,
                                "new": content_hash,
                            },
                        )
                    )
                    self.metrics.errors += 1
                    changed = True
                for attr, val in (
                    ("draw_date", draw_date),
                    ("draw_time", draw_time),
                    ("game_name", game_name),
                    ("content_hash", content_hash),
                    ("source_url", source_url),
                    ("scraped_at", scraped_at),
                    ("raw_payload", raw_payload),
                ):
                    if getattr(existing, attr) != val:
                        setattr(existing, attr, val)
                        changed = True
                if changed:
                    self.metrics.draws_updated += 1
                else:
                    self.metrics.draws_skipped += 1
                pending_existing.append((row, existing))
            else:
                draw = LotteryDraw(
                    lottery_id=lottery_uuid,
                    draw_date=draw_date,
                    draw_time=draw_time,
                    game_name=game_name,
                    source_reference=ref,
                    source_url=source_url,
                    content_hash=content_hash,
                    raw_payload=raw_payload,
                    scraped_at=scraped_at,
                )
                session.add(draw)
                pending_new.append((row, draw))
                self.metrics.draws_inserted += 1

        if pending_new:
            session.flush()
            for row, draw in pending_new:
                if draw.source_reference:
                    existing_by_ref[(draw.lottery_id, draw.source_reference)] = draw

        for row, draw in pending_new + pending_existing:
            nums = numbers_by_sqlite_draw.get(int(row["id"]), [])
            if not nums:
                continue
            is_new_draw = draw in {d for _, d in pending_new}
            existing_nums: dict[tuple[int, str], LotteryDrawNumber] = {}
            if not is_new_draw:
                existing_nums = {
                    (n.position, n.number_type): n
                    for n in session.execute(
                        select(LotteryDrawNumber).where(LotteryDrawNumber.draw_id == draw.id)
                    ).scalars().all()
                }
            for n in nums:
                self.metrics.numbers_read += 1
                pos = int(n["position"])
                ntype = n["number_type"] or "principal"
                payload = {
                    "position_label": n["position_label"],
                    "number_value": str(n["number_value"]),
                    "number_raw": str(n["number_raw"]),
                }
                existing_n = existing_nums.get((pos, ntype))
                if existing_n:
                    for k, v in payload.items():
                        setattr(existing_n, k, v)
                    self.metrics.numbers_updated += 1
                else:
                    session.add(
                        LotteryDrawNumber(
                            draw_id=draw.id,
                            position=pos,
                            number_type=ntype,
                            **payload,
                        )
                    )
                    self.metrics.numbers_inserted += 1

        session.flush()
    def _refresh_lottery_aggregates(self, session: Session) -> None:
        lots = session.execute(select(LotteryLottery)).scalars().all()
        for lot in lots:
            stats = session.execute(
                select(
                    func.count(LotteryDraw.id),
                    func.min(LotteryDraw.draw_date),
                    func.max(LotteryDraw.draw_date),
                ).where(LotteryDraw.lottery_id == lot.id)
            ).one()
            lot.draw_count = int(stats[0] or 0)
            lot.first_draw_date = stats[1]
            lot.last_draw_date = stats[2]
            if lot.source_id == 30:
                lot.is_aggregate = True
                lot.active = False
        session.commit()

    def _postgres_stats(self) -> dict[str, Any]:
        with self.Session() as session:
            lotteries = session.execute(select(func.count()).select_from(LotteryLottery)).scalar_one()
            draws = session.execute(select(func.count()).select_from(LotteryDraw)).scalar_one()
            numbers = session.execute(select(func.count()).select_from(LotteryDrawNumber)).scalar_one()
            with_results = session.execute(
                select(func.count(func.distinct(LotteryDraw.lottery_id)))
            ).scalar_one()
            min_max = session.execute(
                select(func.min(LotteryDraw.draw_date), func.max(LotteryDraw.draw_date))
            ).one()
            leading = session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM jaios.lottery_draw_numbers
                    WHERE number_value LIKE '0%' AND length(number_value) = 2
                    """
                )
            ).scalar_one()
            loto = session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM jaios.lottery_draw_numbers
                    WHERE lower(position_label) LIKE '%loto%'
                    """
                )
            ).scalar_one()
            mas = session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM jaios.lottery_draw_numbers
                    WHERE lower(position_label) LIKE '%más%'
                       OR (lower(position_label) LIKE '%mas%' AND lower(position_label) NOT LIKE '%loto%')
                    """
                )
            ).scalar_one()
            multi = session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM (
                      SELECT lottery_id, draw_date
                      FROM jaios.lottery_draws
                      GROUP BY lottery_id, draw_date
                      HAVING COUNT(*) > 1
                    ) t
                    """
                )
            ).scalar_one()
            return {
                "lotteries": int(lotteries),
                "draws": int(draws),
                "numbers": int(numbers),
                "with_results": int(with_results),
                "min_date": str(min_max[0]) if min_max[0] else None,
                "max_date": str(min_max[1]) if min_max[1] else None,
                "leading_zeros": int(leading),
                "loto_labels": int(loto),
                "mas_labels": int(mas),
                "multi_day": int(multi),
            }
