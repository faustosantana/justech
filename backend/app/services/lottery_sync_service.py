"""Motor de sincronización — dry-run por defecto, sin scheduler."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.lottery import LotteryDraw, LotteryLottery, LotterySyncRun
from app.services.lottery_importer import ProductionGuardError, assert_not_production_database, open_sqlite_readonly


class SyncEnvironmentGuardError(RuntimeError):
    pass


def assert_sync_environment_safe(database_url: str, *, allow_write: bool = False) -> None:
    """Bloquea sync hacia Producción; escritura solo con allow_write explícito y DB staging."""
    assert_not_production_database(database_url)
    parsed = urlparse(
        database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://"
        )
    )
    host = (parsed.hostname or "").lower()
    db = (parsed.path or "").lstrip("/").lower()
    port = parsed.port
    if host not in ("localhost", "127.0.0.1", "::1"):
        raise SyncEnvironmentGuardError(f"Sync solo permitido en localhost (host={host})")
    if allow_write:
        # Phase 8+: escritura automática/manual solo staging :5434
        if db != "jaios_lottery_staging" or port != 5434:
            raise SyncEnvironmentGuardError(
                f"Escritura sync solo jaios_lottery_staging:5434 (db={db} port={port})"
            )
    if settings.lottery_scraping_enabled and allow_write:
        raise SyncEnvironmentGuardError("LOTTERY_SCRAPING_ENABLED no autoriza escritura automática")


@dataclass
class SyncCandidate:
    source_id: int
    lottery_name: str
    draw_date: str
    source_reference: str | None
    numbers: list[str]
    classification: str = "unknown"
    detail: str = ""


@dataclass
class SyncDryRunReport:
    source: str
    dry_run: bool = True
    wrote_to_database: bool = False
    records_fetched: int = 0
    records_new: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    conflicts: int = 0
    errors: int = 0
    classifications: dict[str, int] = field(default_factory=dict)
    sample: list[dict[str, Any]] = field(default_factory=list)
    run_id: uuid.UUID | None = None
    status: str = "completed"
    error_message: str | None = None


class SyncSourceAdapter(Protocol):
    name: str

    def fetch_candidates(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        lottery_source_id: int | None,
        limit: int,
    ) -> list[SyncCandidate]:
        ...


class SqliteSnapshotAdapter:
    """Fuente local de solo lectura (histórico SQLite del scraper)."""

    name = "sqlite"

    def __init__(self, path: Path):
        self.path = path

    def fetch_candidates(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        lottery_source_id: int | None,
        limit: int,
    ) -> list[SyncCandidate]:
        if not self.path.exists():
            raise FileNotFoundError(f"Fuente SQLite no encontrada: {self.path}")
        conn = open_sqlite_readonly(self.path)
        try:
            sql = """
                SELECT l.source_id, l.name, d.draw_date, d.source_reference,
                       GROUP_CONCAT(n.number_value, ',') AS nums
                FROM draws d
                JOIN lotteries l ON l.id = d.lottery_id
                LEFT JOIN draw_numbers n ON n.draw_id = d.id
                WHERE 1=1
            """
            params: list[Any] = []
            if lottery_source_id is not None:
                sql += " AND l.source_id = ?"
                params.append(lottery_source_id)
            if from_date:
                sql += " AND d.draw_date >= ?"
                params.append(from_date.isoformat())
            if to_date:
                sql += " AND d.draw_date <= ?"
                params.append(to_date.isoformat())
            sql += " GROUP BY d.id ORDER BY d.draw_date DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            out: list[SyncCandidate] = []
            for r in rows:
                nums = [x for x in (r["nums"] or "").split(",") if x != ""]
                out.append(
                    SyncCandidate(
                        source_id=int(r["source_id"]),
                        lottery_name=str(r["name"]),
                        draw_date=str(r["draw_date"])[:10],
                        source_reference=str(r["source_reference"]) if r["source_reference"] else None,
                        numbers=nums,
                    )
                )
            return out
        finally:
            conn.close()


class ElBoletoApiAdapter:
    """Adapter HTTP de solo lectura hacia API pública auditada.

    En Fase 6 se usa preferentemente en dry-run. Si la red falla, el caller
    debe documentarlo — no inventar resultados.
    """

    name = "api"

    def __init__(self, base_url: str | None = None, user_agent: str | None = None):
        self.base_url = (base_url or settings.lottery_sync_api_base_url).rstrip("/")
        self.user_agent = user_agent or settings.lottery_sync_user_agent

    def fetch_candidates(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        lottery_source_id: int | None,
        limit: int,
    ) -> list[SyncCandidate]:
        import time
        import urllib.error
        import urllib.request
        from datetime import timedelta

        from app.services.lottery_permissions import CONFIRMED_PRIORITY_SOURCE_IDS

        end = to_date or date.today()
        start = from_date or end
        if start > end:
            start, end = end, start
        dates: list[date] = []
        cur = start
        while cur <= end:
            dates.append(cur)
            cur += timedelta(days=1)
            if len(dates) > settings.lottery_sync_max_range_days:
                break

        lottery_ids = (
            [lottery_source_id]
            if lottery_source_id is not None
            else sorted(set(CONFIRMED_PRIORITY_SOURCE_IDS.values()))
        )

        out: list[SyncCandidate] = []
        for lid in lottery_ids:
            for d in dates:
                if len(out) >= limit:
                    return out
                fecha = d.isoformat()
                url = f"{self.base_url}/sorteos/buscar/historial?id={lid}&fecha={fecha}"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                )
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        payload = json.loads(resp.read().decode("utf-8"))
                except urllib.error.HTTPError as exc:
                    if exc.code in (429, 502, 503, 504):
                        retry_after = exc.headers.get("Retry-After")
                        wait = float(retry_after) if retry_after and str(retry_after).isdigit() else 2.0
                        for attempt in range(settings.lottery_sync_max_retries):
                            sleep_s = wait * (2**attempt) + (0.1 * attempt)
                            time.sleep(min(sleep_s, 30))
                            try:
                                with urllib.request.urlopen(req, timeout=30) as resp:
                                    payload = json.loads(resp.read().decode("utf-8"))
                                break
                            except urllib.error.HTTPError as exc2:
                                if exc2.code not in (429, 502, 503, 504) or attempt == settings.lottery_sync_max_retries - 1:
                                    raise RuntimeError(f"source_error: {exc2}") from exc2
                        else:
                            raise RuntimeError(f"source_error: {exc}") from exc
                    else:
                        raise RuntimeError(f"source_error: {exc}") from exc
                except urllib.error.URLError as exc:
                    raise RuntimeError(f"source_error: {exc}") from exc
                time.sleep(float(settings.lottery_sync_request_delay))

                items = (
                    payload
                    if isinstance(payload, list)
                    else payload.get("historial")
                    or payload.get("data")
                    or payload.get("resultados")
                    or []
                )
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if len(out) >= limit:
                        return out
                    dd = str(item.get("fecha_sorteo") or item.get("fecha") or item.get("draw_date") or "")[:10]
                    if from_date and dd and dd < from_date.isoformat():
                        continue
                    if to_date and dd and dd > to_date.isoformat():
                        continue
                    nums_raw = item.get("premios") or item.get("numeros") or item.get("numbers") or []
                    if isinstance(nums_raw, str):
                        nums = [
                            x.strip().zfill(2) if x.strip().isdigit() else x.strip()
                            for x in nums_raw.replace("-", ",").split(",")
                            if x.strip()
                        ]
                    elif isinstance(nums_raw, list):
                        nums = [
                            str(x).zfill(2) if str(x).isdigit() and len(str(x)) <= 2 else str(x)
                            for x in nums_raw
                        ]
                    else:
                        nums = []
                    for key in ("loto1", "loto2"):
                        if item.get(key) not in (None, "", "null"):
                            nums.append(str(item[key]))
                    out.append(
                        SyncCandidate(
                            source_id=lid,
                            lottery_name=str(
                                item.get("loteria") or item.get("name") or f"source:{lid}"
                            ),
                            draw_date=dd,
                            source_reference=str(
                                item.get("id")
                                or item.get("source_reference")
                                or item.get("numero_sorteo")
                                or ""
                            )
                            or None,
                            numbers=nums,
                        )
                    )
        return out


class LotterySyncService:
    def __init__(self, db: AsyncSession, *, database_url: str):
        self.db = db
        self.database_url = database_url

    async def dry_run(
        self,
        *,
        source: str = "sqlite",
        sqlite_path: Path | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        lottery_source_id: int | None = None,
        limit: int = 500,
        git_commit: str | None = None,
    ) -> SyncDryRunReport:
        assert_sync_environment_safe(self.database_url, allow_write=False)
        if settings.lottery_sync_enabled and False:  # noqa: SIM223 — explicit: never auto-write here
            pass

        adapter: SyncSourceAdapter
        if source == "api":
            adapter = ElBoletoApiAdapter()
        else:
            path = sqlite_path or Path("/Users/faustosantana/Projects/lottery-history-scraper/data/lottery.db")
            adapter = SqliteSnapshotAdapter(path)

        started = datetime.now(timezone.utc)
        run = LotterySyncRun(
            source=adapter.name,
            started_at=started,
            status="running",
            dry_run=True,
            git_commit=git_commit,
            app_version="phase6",
        )
        self.db.add(run)
        await self.db.flush()

        report = SyncDryRunReport(source=adapter.name, dry_run=True, run_id=run.id)
        try:
            candidates = adapter.fetch_candidates(
                from_date=from_date,
                to_date=to_date,
                lottery_source_id=lottery_source_id,
                limit=limit,
            )
            report.records_fetched = len(candidates)
            classifications: dict[str, int] = {}

            for cand in candidates:
                cls = await self._classify(cand)
                cand.classification = cls
                classifications[cls] = classifications.get(cls, 0) + 1
                if cls == "new":
                    report.records_new += 1
                elif cls == "unchanged":
                    report.records_skipped += 1
                elif cls == "changed":
                    report.records_updated += 1
                elif cls == "conflict":
                    report.conflicts += 1
                elif cls in ("unknown_lottery", "invalid", "source_error"):
                    report.errors += 1
                if len(report.sample) < 20:
                    report.sample.append(
                        {
                            "source_id": cand.source_id,
                            "lottery": cand.lottery_name,
                            "draw_date": cand.draw_date,
                            "numbers": cand.numbers,
                            "classification": cls,
                        }
                    )

            report.classifications = classifications
            report.status = "completed"
            payload_hash = hashlib.sha256(
                json.dumps(report.sample, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.records_fetched = report.records_fetched
            run.records_new = report.records_new
            run.records_updated = report.records_updated
            run.records_skipped = report.records_skipped
            run.conflicts = report.conflicts
            run.errors = report.errors
            run.source_response_hash = payload_hash
            run.report = {
                "classifications": classifications,
                "sample": report.sample,
                "wrote_to_database": False,
            }
            await self.db.flush()
            # dry-run: no insert/update de draws
            report.wrote_to_database = False
            return report
        except Exception as exc:  # noqa: BLE001 — surface in run row
            report.status = "failed"
            report.error_message = str(exc)
            report.errors += 1
            run.status = "failed"
            run.error_message = str(exc)[:2000]
            run.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
            return report

    async def _classify(self, cand: SyncCandidate) -> str:
        if not cand.draw_date or not cand.numbers:
            return "invalid"
        lot = await self.db.scalar(
            select(LotteryLottery).where(LotteryLottery.source_id == cand.source_id)
        )
        if not lot:
            return "unknown_lottery"
        try:
            d = date.fromisoformat(cand.draw_date)
        except ValueError:
            return "invalid"

        q = await self.db.execute(
            select(LotteryDraw).where(
                LotteryDraw.lottery_id == lot.id,
                LotteryDraw.draw_date == d,
            )
        )
        draws = list(q.scalars().all())
        if not draws:
            return "new"
        # Match by source_reference when present
        if cand.source_reference:
            for dr in draws:
                if dr.source_reference and str(dr.source_reference) == str(cand.source_reference):
                    return "unchanged"
            if len(draws) > 1:
                return "conflict"
        # Single draw same date → treat as unchanged if count matches loosely
        if len(draws) == 1:
            return "unchanged"
        return "conflict"

    async def draw_count(self) -> int:
        return int(await self.db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
