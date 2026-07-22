"""Escritura controlada de sync en staging + rollback + reconciliación."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.lottery import (
    LotteryDraw,
    LotteryDrawNumber,
    LotteryDrawRevision,
    LotteryLottery,
    LotterySyncRun,
)
from app.services.lottery_permissions import AMBIGUOUS_NACIONAL_DIA_CANDIDATES
from app.services.lottery_sync_gates import assert_write_gates
from app.services.lottery_sync_lock import (
    SyncLockError,
    acquire_sync_lock,
    heartbeat_sync_lock,
    release_sync_lock,
)
from app.services.lottery_sync_service import (
    ElBoletoApiAdapter,
    SqliteSnapshotAdapter,
    SyncCandidate,
    SyncEnvironmentGuardError,
    SyncSourceAdapter,
    assert_sync_environment_safe,
)


NACIONAL_DIA_NAMES = {"nacional dia", "nacional día", "nacional-dia"}


def _canonical_hash(*, source_id: int, draw_date: str, source_reference: str | None, numbers: list[str], game_name: str = "quiniela") -> str:
    payload = {
        "source_id": source_id,
        "draw_date": draw_date,
        "source_reference": source_reference or "",
        "game_name": game_name,
        "numbers": numbers,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@dataclass
class SyncWriteReport:
    source: str
    dry_run: bool
    wrote_to_database: bool
    run_id: uuid.UUID | None = None
    status: str = "completed"
    records_fetched: int = 0
    records_new: int = 0
    records_inserted: int = 0
    records_unchanged: int = 0
    records_changed: int = 0
    records_updated: int = 0
    records_conflicted: int = 0
    records_invalid: int = 0
    records_skipped: int = 0
    records_ambiguous: int = 0
    draws_before: int = 0
    draws_after: int = 0
    numbers_before: int = 0
    numbers_after: int = 0
    inserted_draw_ids: list[str] = field(default_factory=list)
    classifications: dict[str, int] = field(default_factory=dict)
    sample: list[dict[str, Any]] = field(default_factory=list)
    checkpoint: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    change_policy: str = "reject"


class FixtureSourceAdapter:
    """Adapter de prueba controlada — no usa red ni SQLite histórico."""

    name = "fixture"

    def __init__(self, candidates: list[SyncCandidate] | None = None, *, tag: str | None = None):
        self.tag = tag or uuid.uuid4().hex[:10]
        if candidates is not None:
            self._candidates = candidates
        else:
            # Un sorteo nuevo válido sobre Quiniela Real (13)
            self._candidates = [
                SyncCandidate(
                    source_id=13,
                    lottery_name="Quiniela Real",
                    draw_date="2099-01-01",  # fecha futura sintética aislada
                    source_reference=f"fixture-p7-{self.tag}",
                    numbers=["00", "05", "19"],
                )
            ]

    def fetch_candidates(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        lottery_source_id: int | None,
        limit: int,
    ) -> list[SyncCandidate]:
        out = []
        for c in self._candidates:
            if lottery_source_id is not None and c.source_id != lottery_source_id:
                continue
            if from_date and c.draw_date < from_date.isoformat():
                continue
            if to_date and c.draw_date > to_date.isoformat():
                continue
            out.append(c)
            if len(out) >= limit:
                break
        return out


class LotterySyncWriter:
    def __init__(self, db: AsyncSession, *, database_url: str):
        self.db = db
        self.database_url = database_url

    async def count_draws(self) -> int:
        return int(await self.db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)

    async def count_numbers(self) -> int:
        return int(await self.db.scalar(select(func.count()).select_from(LotteryDrawNumber)) or 0)

    def _adapter(self, source: str, *, sqlite_path: Path | None, fixture: FixtureSourceAdapter | None) -> SyncSourceAdapter:
        if source == "fixture":
            return fixture or FixtureSourceAdapter()
        if source == "api":
            return ElBoletoApiAdapter()
        return SqliteSnapshotAdapter(sqlite_path or Path("/Users/faustosantana/Projects/lottery-history-scraper/data/lottery.db"))

    async def run(
        self,
        *,
        source: str = "fixture",
        write: bool = False,
        environment: str | None = None,
        confirm_database: str | None = None,
        yes: bool = False,
        backup_path: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        lottery_source_id: int | None = None,
        limit: int = 50,
        change_policy: str = "reject",
        allow_updates: bool = False,
        sqlite_path: Path | None = None,
        fixture: FixtureSourceAdapter | None = None,
        initiated_by: str = "cli",
        resume_run_id: uuid.UUID | None = None,
        via_scheduler: bool = False,
        skip_lock: bool = False,
    ) -> SyncWriteReport:
        assert_sync_environment_safe(self.database_url, allow_write=write)
        if write:
            assert_write_gates(
                database_url=self.database_url,
                environment=environment,
                confirm_database=confirm_database,
                write=True,
                yes=yes,
                backup_path=backup_path,
                via_scheduler=via_scheduler,
            )
            if (to_date and from_date) and (to_date - from_date).days > settings.lottery_sync_max_range_days_write:
                raise SyncEnvironmentGuardError(
                    f"Rango máximo escritura: {settings.lottery_sync_max_range_days_write} días"
                )
            if change_policy == "update" and not allow_updates:
                raise SyncEnvironmentGuardError("update requiere --allow-updates")

        lock_key = f"lottery:sync:staging:{source}"
        handle = None
        if write and not skip_lock:
            try:
                handle = await acquire_sync_lock(lock_key)
            except SyncLockError as exc:
                raise SyncEnvironmentGuardError(str(exc)) from exc

        draws_before = await self.count_draws()
        numbers_before = await self.count_numbers()
        adapter = self._adapter(source, sqlite_path=sqlite_path, fixture=fixture)
        started = datetime.now(timezone.utc)
        run = LotterySyncRun(
            source=adapter.name,
            started_at=started,
            status="validating",
            dry_run=not write,
            write_enabled=write,
            environment=environment or ("staging" if write else "local"),
            mode="write" if write else "dry_run",
            from_date=from_date,
            to_date=to_date,
            lottery_ids=[lottery_source_id] if lottery_source_id is not None else [],
            change_policy=change_policy,
            backup_path=backup_path,
            initiated_by=initiated_by,
            lock_key=lock_key if write else None,
            draws_before=draws_before,
            numbers_before=numbers_before,
            app_version="phase7",
            checkpoint={},
            inserted_draw_ids=[],
            updated_draw_ids=[],
        )
        self.db.add(run)
        await self.db.flush()

        report = SyncWriteReport(
            source=adapter.name,
            dry_run=not write,
            wrote_to_database=False,
            run_id=run.id,
            draws_before=draws_before,
            numbers_before=numbers_before,
            change_policy=change_policy,
        )
        try:
            run.status = "running"
            run.heartbeat_at = datetime.now(timezone.utc)
            candidates = adapter.fetch_candidates(
                from_date=from_date,
                to_date=to_date,
                lottery_source_id=lottery_source_id,
                limit=limit,
            )
            report.records_fetched = len(candidates)
            inserted_ids: list[str] = []
            classifications: dict[str, int] = {}

            for cand in candidates:
                if handle:
                    await heartbeat_sync_lock(handle)
                cls = await self._classify(cand)
                # Nacional Día ambiguity by name
                if cand.lottery_name and cand.lottery_name.strip().lower() in NACIONAL_DIA_NAMES:
                    cls = "ambiguous_lottery"
                    cand.detail = json.dumps(list(AMBIGUOUS_NACIONAL_DIA_CANDIDATES))
                cand.classification = cls
                classifications[cls] = classifications.get(cls, 0) + 1

                if cls == "new":
                    report.records_new += 1
                    if write:
                        draw_id = await self._insert_draw(cand, run.id)
                        inserted_ids.append(str(draw_id))
                        report.records_inserted += 1
                elif cls == "unchanged":
                    report.records_unchanged += 1
                elif cls == "changed":
                    report.records_changed += 1
                    if write and change_policy == "update" and allow_updates:
                        await self._update_draw(cand, run.id)
                        report.records_updated += 1
                    else:
                        report.records_conflicted += 1
                        classifications["conflict"] = classifications.get("conflict", 0) + 1
                elif cls == "conflict":
                    report.records_conflicted += 1
                elif cls == "ambiguous_lottery":
                    report.records_ambiguous += 1
                    report.records_skipped += 1
                elif cls in ("invalid", "unknown_lottery", "source_error"):
                    report.records_invalid += 1
                else:
                    report.records_skipped += 1

                if len(report.sample) < 25:
                    report.sample.append(
                        {
                            "source_id": cand.source_id,
                            "lottery": cand.lottery_name,
                            "draw_date": cand.draw_date,
                            "source_reference": cand.source_reference,
                            "numbers": cand.numbers,
                            "classification": cls,
                            "detail": cand.detail,
                        }
                    )
                run.checkpoint = {
                    "last_source_id": cand.source_id,
                    "last_draw_date": cand.draw_date,
                    "last_source_reference": cand.source_reference,
                    "processed": report.records_fetched,
                }
                await self.db.flush()

            report.classifications = classifications
            report.inserted_draw_ids = inserted_ids
            report.checkpoint = dict(run.checkpoint or {})
            report.wrote_to_database = bool(write and inserted_ids)
            report.draws_after = await self.count_draws()
            report.numbers_after = await self.count_numbers()
            report.status = "completed_with_warnings" if report.records_conflicted or report.records_ambiguous else "completed"

            run.status = report.status
            run.completed_at = datetime.now(timezone.utc)
            run.records_fetched = report.records_fetched
            run.records_new = report.records_new
            run.records_inserted = report.records_inserted
            run.records_unchanged = report.records_unchanged
            run.records_changed = report.records_changed
            run.records_updated = report.records_updated
            run.records_conflicted = report.records_conflicted
            run.records_invalid = report.records_invalid
            run.records_skipped = report.records_skipped
            run.conflicts = report.records_conflicted
            run.draws_after = report.draws_after
            run.numbers_after = report.numbers_after
            run.inserted_draw_ids = inserted_ids
            run.report = {
                "classifications": classifications,
                "sample": report.sample,
                "wrote_to_database": report.wrote_to_database,
            }
            await self.db.flush()
            return report
        except Exception as exc:  # noqa: BLE001
            report.status = "failed"
            report.error_message = str(exc)
            run.status = "failed"
            run.error_message = str(exc)[:2000]
            run.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
            raise
        finally:
            if handle:
                await release_sync_lock(handle)

    async def _classify(self, cand: SyncCandidate) -> str:
        if not cand.draw_date or not cand.numbers:
            return "invalid"
        # Preserve zeros as strings
        if any(not isinstance(n, str) for n in cand.numbers):
            return "invalid"
        lot = await self.db.scalar(select(LotteryLottery).where(LotteryLottery.source_id == cand.source_id))
        if not lot:
            return "unknown_lottery"
        try:
            d = date.fromisoformat(cand.draw_date)
        except ValueError:
            return "invalid"

        new_hash = _canonical_hash(
            source_id=cand.source_id,
            draw_date=cand.draw_date,
            source_reference=cand.source_reference,
            numbers=cand.numbers,
        )

        if cand.source_reference:
            q = await self.db.execute(
                select(LotteryDraw)
                .where(
                    LotteryDraw.lottery_id == lot.id,
                    LotteryDraw.source_reference == cand.source_reference,
                )
                .options(selectinload(LotteryDraw.numbers))
            )
            existing = q.scalar_one_or_none()
            if existing:
                nums = [n.number_value for n in sorted(existing.numbers, key=lambda x: x.position)]
                old_hash = _canonical_hash(
                    source_id=cand.source_id,
                    draw_date=existing.draw_date.isoformat(),
                    source_reference=existing.source_reference,
                    numbers=nums,
                    game_name=existing.game_name,
                )
                if old_hash == new_hash or existing.content_hash == new_hash:
                    return "unchanged"
                return "changed"

        q = await self.db.execute(
            select(LotteryDraw).where(LotteryDraw.lottery_id == lot.id, LotteryDraw.draw_date == d)
        )
        draws = list(q.scalars().all())
        if not draws:
            return "new"
        if cand.source_reference is None and len(draws) >= 1:
            # NULL source_reference — could be multi-draw; treat as conflict if multiple
            if len(draws) > 1:
                return "conflict"
            return "unchanged"
        return "new" if not any(dr.source_reference == cand.source_reference for dr in draws) else "conflict"

    async def _insert_draw(self, cand: SyncCandidate, sync_run_id: uuid.UUID) -> uuid.UUID:
        lot = await self.db.scalar(select(LotteryLottery).where(LotteryLottery.source_id == cand.source_id))
        assert lot is not None
        d = date.fromisoformat(cand.draw_date)
        ch = _canonical_hash(
            source_id=cand.source_id,
            draw_date=cand.draw_date,
            source_reference=cand.source_reference,
            numbers=cand.numbers,
        )
        draw = LotteryDraw(
            lottery_id=lot.id,
            draw_date=d,
            draw_time=None,
            game_name="quiniela",
            source_reference=cand.source_reference,
            source_url=None,
            content_hash=ch,
            raw_payload={"sync_run_id": str(sync_run_id), "phase": 7},
            scraped_at=datetime.now(timezone.utc),
        )
        self.db.add(draw)
        await self.db.flush()
        labels = {0: "1ra", 1: "2da", 2: "3ra"}
        for i, num in enumerate(cand.numbers):
            ntype = "principal"
            label = labels.get(i, f"n{i+1}")
            low = num.lower() if isinstance(num, str) else ""
            if "loto" in low:
                ntype = "loto"
                label = num
            if num in ("Más", "Mas", "más") or (isinstance(num, str) and num.lower() == "mas"):
                ntype = "mas"
                label = "Más"
            self.db.add(
                LotteryDrawNumber(
                    draw_id=draw.id,
                    position=i + 1,
                    position_label=label,
                    number_value=str(num),
                    number_raw=str(num),
                    number_type=ntype,
                )
            )
        # Update lottery coverage hints
        if lot.last_draw_date is None or d > lot.last_draw_date:
            lot.last_draw_date = d
        lot.draw_count = int(lot.draw_count or 0) + 1
        await self.db.flush()
        return draw.id

    async def _update_draw(self, cand: SyncCandidate, sync_run_id: uuid.UUID) -> None:
        lot = await self.db.scalar(select(LotteryLottery).where(LotteryLottery.source_id == cand.source_id))
        assert lot and cand.source_reference
        q = await self.db.execute(
            select(LotteryDraw)
            .where(LotteryDraw.lottery_id == lot.id, LotteryDraw.source_reference == cand.source_reference)
            .options(selectinload(LotteryDraw.numbers))
        )
        existing = q.scalar_one()
        prev_nums = [n.number_value for n in sorted(existing.numbers, key=lambda x: x.position)]
        prev_hash = existing.content_hash
        new_hash = _canonical_hash(
            source_id=cand.source_id,
            draw_date=cand.draw_date,
            source_reference=cand.source_reference,
            numbers=cand.numbers,
        )
        self.db.add(
            LotteryDrawRevision(
                draw_id=existing.id,
                sync_run_id=sync_run_id,
                revision_number=1,
                previous_content_hash=prev_hash,
                new_content_hash=new_hash,
                previous_snapshot={"numbers": prev_nums, "draw_date": existing.draw_date.isoformat()},
                new_snapshot={"numbers": cand.numbers, "draw_date": cand.draw_date},
                change_reason="sync_update",
                source="sync",
            )
        )
        existing.content_hash = new_hash
        existing.draw_date = date.fromisoformat(cand.draw_date)
        await self.db.execute(delete(LotteryDrawNumber).where(LotteryDrawNumber.draw_id == existing.id))
        for i, num in enumerate(cand.numbers):
            self.db.add(
                LotteryDrawNumber(
                    draw_id=existing.id,
                    position=i + 1,
                    position_label=f"n{i+1}",
                    number_value=str(num),
                    number_raw=str(num),
                    number_type="principal",
                )
            )
        await self.db.flush()

    async def rollback_run(
        self,
        run_id: uuid.UUID,
        *,
        environment: str,
        confirm_database: str,
        yes: bool,
        backup_path: str | None,
        initiated_by: str = "cli",
        via_scheduler: bool = False,
    ) -> dict[str, Any]:
        assert_write_gates(
            database_url=self.database_url,
            environment=environment,
            confirm_database=confirm_database,
            write=True,
            yes=yes,
            backup_path=backup_path,
            via_scheduler=via_scheduler,
        )
        run = await self.db.get(LotterySyncRun, run_id)
        if not run:
            raise SyncEnvironmentGuardError("sync_run no encontrado")
        if run.dry_run or not run.write_enabled:
            raise SyncEnvironmentGuardError("Solo se puede hacer rollback de ejecuciones con escritura")
        if run.rollback_status == "rolled_back":
            return {"status": "already_rolled_back", "run_id": str(run_id)}

        ids = [uuid.UUID(x) for x in (run.inserted_draw_ids or [])]
        before = await self.count_draws()
        if ids:
            await self.db.execute(delete(LotteryDrawNumber).where(LotteryDrawNumber.draw_id.in_(ids)))
            await self.db.execute(delete(LotteryDraw).where(LotteryDraw.id.in_(ids)))
        run.rollback_status = "rolled_back"
        run.status = "rolled_back"
        await self.db.flush()
        after = await self.count_draws()
        return {
            "status": "rolled_back",
            "run_id": str(run_id),
            "deleted_draws": len(ids),
            "draws_before": before,
            "draws_after": after,
            "initiated_by": initiated_by,
        }

    async def reconcile(
        self,
        *,
        source: str = "fixture",
        from_date: date | None = None,
        to_date: date | None = None,
        lottery_source_id: int | None = None,
        limit: int = 200,
        fixture: FixtureSourceAdapter | None = None,
        sqlite_path: Path | None = None,
    ) -> dict[str, Any]:
        """Solo lectura — compara fuente vs staging."""
        assert_sync_environment_safe(self.database_url, allow_write=False)
        adapter = self._adapter(source, sqlite_path=sqlite_path, fixture=fixture)
        candidates = adapter.fetch_candidates(
            from_date=from_date,
            to_date=to_date,
            lottery_source_id=lottery_source_id,
            limit=limit,
        )
        summary = {
            "exact_match": 0,
            "missing_in_staging": 0,
            "changed": 0,
            "conflict": 0,
            "invalid": 0,
            "unknown_lottery": 0,
            "ambiguous_lottery": 0,
            "duplicate": 0,
        }
        details: list[dict[str, Any]] = []
        for cand in candidates:
            if cand.lottery_name and cand.lottery_name.strip().lower() in NACIONAL_DIA_NAMES:
                cls = "ambiguous_lottery"
            else:
                cls = await self._classify(cand)
            key = {
                "new": "missing_in_staging",
                "unchanged": "exact_match",
                "changed": "changed",
                "conflict": "conflict",
                "invalid": "invalid",
                "unknown_lottery": "unknown_lottery",
                "ambiguous_lottery": "ambiguous_lottery",
            }.get(cls, cls)
            summary[key] = summary.get(key, 0) + 1
            if len(details) < 50:
                details.append({"classification": key, "candidate": cand.__dict__})
        return {"source": adapter.name, "summary": summary, "details": details, "fetched": len(candidates)}
