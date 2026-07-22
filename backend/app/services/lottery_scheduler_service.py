"""Tick del scheduler de lotería — observe / guarded_write / disabled."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.lottery import LotteryDraw, LotterySchedulerState
from app.services.lottery_automatic_write_gates import (
    assert_automatic_write_gates,
    compute_lookback_range,
)
from app.services.lottery_circuit_breaker import (
    evaluate_circuit,
    next_state_after_failure,
    next_state_after_success,
)
from app.services.lottery_sync_alerts import create_alert
from app.services.lottery_sync_lock import (
    SyncLockError,
    acquire_sync_lock,
    heartbeat_sync_lock,
    release_sync_lock,
)
from app.services.lottery_sync_service import SyncEnvironmentGuardError
from app.services.lottery_sync_writer import FixtureSourceAdapter, LotterySyncWriter

logger = logging.getLogger(__name__)

MODES = frozenset({"disabled", "observe", "guarded_write"})


@dataclass
class SchedulerTickResult:
    status: str
    mode: str
    wrote: bool = False
    blocked_reason: str | None = None
    dry_run_id: str | None = None
    write_run_id: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)
    from_date: str | None = None
    to_date: str | None = None
    circuit_state: str = "closed"


class LotterySchedulerService:
    def __init__(self, db: AsyncSession, *, database_url: str | None = None):
        self.db = db
        self.database_url = database_url or settings.database_url

    async def get_or_create_state(self, environment: str = "staging") -> LotterySchedulerState:
        q = await self.db.execute(
            select(LotterySchedulerState).where(LotterySchedulerState.environment == environment)
        )
        state = q.scalar_one_or_none()
        if state:
            return state
        state = LotterySchedulerState(
            environment=environment,
            mode=settings.lottery_scheduler_mode or "disabled",
            enabled=bool(settings.lottery_scheduler_enabled),
            circuit_state="closed",
            consecutive_failures=0,
            metadata_={},
            source_contract_version=settings.lottery_source_contract_version,
        )
        self.db.add(state)
        await self.db.flush()
        return state

    async def set_mode(
        self,
        mode: str,
        *,
        enabled: bool | None = None,
        confirmation: str | None = None,
        by: str = "admin",
    ) -> LotterySchedulerState:
        mode = (mode or "").strip().lower()
        if mode not in MODES:
            raise SyncEnvironmentGuardError(f"Modo inválido: {mode}")
        if mode == "guarded_write":
            expected = "ENABLE GUARDED WRITE ON jaios_lottery_staging"
            if (confirmation or "").strip() != expected:
                raise SyncEnvironmentGuardError(
                    f"Confirmación fuerte requerida: escriba exactamente '{expected}'"
                )
        state = await self.get_or_create_state()
        state.mode = mode
        if enabled is not None:
            state.enabled = enabled
        if mode == "guarded_write" and settings.lottery_sync_write_enabled:
            state.write_enabled_since = datetime.now(timezone.utc)
        if mode == "disabled":
            state.enabled = False
            state.write_enabled_since = None
        state.updated_at = datetime.now(timezone.utc)
        state.metadata_ = {**(state.metadata_ or {}), "last_mode_change_by": by}
        await self.db.flush()
        return state

    async def reset_circuit(self, *, by: str = "admin") -> LotterySchedulerState:
        state = await self.get_or_create_state()
        state.circuit_state = "closed"
        state.circuit_opened_at = None
        state.circuit_reason = None
        state.consecutive_failures = 0
        state.updated_at = datetime.now(timezone.utc)
        state.metadata_ = {**(state.metadata_ or {}), "circuit_reset_by": by}
        await self.db.flush()
        return state

    def _effective_mode(self, state: LotterySchedulerState) -> str:
        if not settings.lottery_scheduler_enabled or not state.enabled:
            return "disabled"
        mode = (settings.lottery_scheduler_mode or state.mode or "disabled").lower()
        return mode if mode in MODES else "disabled"

    async def tick(
        self,
        *,
        source: str | None = None,
        fixture: FixtureSourceAdapter | None = None,
        backup_path: str | None = None,
        force: bool = False,
        initiated_by: str = "scheduler",
    ) -> SchedulerTickResult:
        state = await self.get_or_create_state()
        mode = self._effective_mode(state)
        now = datetime.now(timezone.utc)
        interval = max(1, int(settings.lottery_sync_interval_minutes))
        state.last_tick_at = now
        state.next_run_at = now + timedelta(minutes=interval)
        state.updated_at = now

        if mode == "disabled" and not force:
            await self.db.flush()
            return SchedulerTickResult(status="disabled", mode="disabled", circuit_state=state.circuit_state)

        decision = evaluate_circuit(
            state=state.circuit_state,
            consecutive_failures=state.consecutive_failures,
            opened_at=state.circuit_opened_at,
        )
        if not decision.allow_tick and not force:
            await create_alert(
                self.db,
                code="circuit_breaker_open",
                title="Circuit breaker abierto",
                message=decision.reason or "open",
                severity="error",
            )
            await self.db.flush()
            return SchedulerTickResult(
                status="blocked",
                mode=mode,
                blocked_reason=decision.reason,
                circuit_state=decision.state,
            )

        # Write-flag timeout monitoring
        if settings.lottery_sync_write_enabled or settings.lottery_sync_automatic_write_enabled:
            since = state.write_enabled_since or now
            if state.write_enabled_since is None and (
                settings.lottery_sync_write_enabled or settings.lottery_sync_automatic_write_enabled
            ):
                state.write_enabled_since = now
                since = now
            minutes = (now - since).total_seconds() / 60
            if minutes > settings.lottery_sync_write_flag_max_minutes:
                await create_alert(
                    self.db,
                    code="write_flag_enabled_too_long",
                    title="Write flags habilitados demasiado tiempo",
                    message=f"{minutes:.0f} minutos > {settings.lottery_sync_write_flag_max_minutes}",
                    severity="critical",
                )
                # Runtime effective block — do not mutate .env
                decision = evaluate_circuit(
                    state="open",
                    consecutive_failures=settings.lottery_sync_circuit_failure_threshold,
                    opened_at=now,
                )
                state.circuit_state = "open"
                state.circuit_opened_at = now
                state.circuit_reason = "write_flag_timeout"

        src = source or settings.lottery_sync_source or "api"
        if fixture is not None:
            src = "fixture"

        max_draw = await self.db.scalar(select(func.max(LotteryDraw.draw_date)))
        if fixture is not None:
            # Fixture dates are synthetic — do not apply production lookback window.
            from_d, to_d = None, None
        else:
            from_d, to_d = compute_lookback_range(max_draw_date=max_draw)
        writer = LotterySyncWriter(self.db, database_url=self.database_url)
        lock_key = f"lottery:sync:staging:{src}"
        handle = None
        alerts: list[str] = []

        try:
            handle = await acquire_sync_lock(lock_key, ttl_seconds=settings.lottery_sync_lock_ttl_seconds)
        except SyncLockError as exc:
            await create_alert(
                self.db,
                code="lock_stale",
                title="Lock de sync ocupado",
                message=str(exc),
                severity="warning",
            )
            await self.db.flush()
            return SchedulerTickResult(
                status="blocked",
                mode=mode,
                blocked_reason=str(exc),
                circuit_state=state.circuit_state,
                alerts=["lock_stale"],
            )

        try:
            await heartbeat_sync_lock(handle)
            # Always dry-run first
            dry = await writer.run(
                source=src,
                write=False,
                from_date=from_d,
                to_date=to_d,
                fixture=fixture,
                initiated_by=initiated_by,
                skip_lock=True,
                limit=min(500, settings.lottery_sync_max_new_per_run + 50),
            )
            metrics = {
                "fetched": dry.records_fetched,
                "new": dry.records_new,
                "unchanged": dry.records_unchanged,
                "changed": dry.records_changed,
                "conflicts": dry.records_conflicted,
                "invalid": dry.records_invalid,
                "ambiguous": dry.records_ambiguous,
            }
            if dry.records_changed:
                await create_alert(
                    self.db,
                    code="changed_detected",
                    title="Cambios retroactivos detectados",
                    message=f"{dry.records_changed} registros CHANGED",
                    severity="warning",
                    sync_run_id=dry.run_id,
                )
                alerts.append("changed_detected")
            if dry.records_conflicted:
                await create_alert(
                    self.db,
                    code="conflict_detected",
                    title="Conflictos detectados",
                    message=f"{dry.records_conflicted} conflictos",
                    severity="error",
                    sync_run_id=dry.run_id,
                )
                alerts.append("conflict_detected")
            if dry.records_ambiguous:
                await create_alert(
                    self.db,
                    code="ambiguous_lottery",
                    title="Lotería ambigua (Nacional Día u otra)",
                    message=f"{dry.records_ambiguous} ambiguos — no insertados",
                    severity="warning",
                    sync_run_id=dry.run_id,
                )
                alerts.append("ambiguous_lottery")

            result = SchedulerTickResult(
                status="observe_ok",
                mode=mode,
                wrote=False,
                dry_run_id=str(dry.run_id) if dry.run_id else None,
                metrics=metrics,
                alerts=alerts,
                from_date=from_d.isoformat() if from_d else None,
                to_date=to_d.isoformat() if to_d else None,
                circuit_state=state.circuit_state,
            )

            if mode != "guarded_write" or not decision.allow_write:
                state.last_run_id = dry.run_id
                state.consecutive_failures = 0
                state.circuit_state = next_state_after_success(state.circuit_state)
                await self.db.flush()
                return result

            # Guarded write path
            bp = backup_path
            if not bp:
                backups = sorted(
                    Path("data/lottery-staging-backups").glob("pre-phase*.dump")
                ) + sorted(Path("data/lottery-staging-backups").glob("pre-sync*.dump"))
                bp = str(backups[-1]) if backups else None
            try:
                assert_automatic_write_gates(
                    database_url=self.database_url,
                    mode=mode,
                    dry_run_report=dry,
                    backup_path=bp,
                    circuit_allow_write=decision.allow_write,
                    write_enabled_since=state.write_enabled_since,
                )
            except SyncEnvironmentGuardError as exc:
                await create_alert(
                    self.db,
                    code="sync_blocked",
                    title="Escritura automática bloqueada",
                    message=str(exc),
                    severity="warning",
                    sync_run_id=dry.run_id,
                )
                state.last_run_id = dry.run_id
                await self.db.flush()
                result.status = "blocked"
                result.blocked_reason = str(exc)
                result.alerts = alerts + ["sync_blocked"]
                return result

            # change_policy always reject for scheduler; never update
            write_report = await writer.run(
                source=src,
                write=True,
                environment="staging",
                confirm_database="jaios_lottery_staging",
                yes=True,
                backup_path=bp,
                from_date=from_d,
                to_date=to_d,
                fixture=fixture,
                change_policy="reject",
                allow_updates=False,
                initiated_by=initiated_by,
                via_scheduler=True,
                skip_lock=True,
                limit=min(500, settings.lottery_sync_max_new_per_run + 50),
            )
            result.wrote = bool(write_report.records_inserted)
            result.write_run_id = str(write_report.run_id) if write_report.run_id else None
            result.status = "guarded_write_ok"
            result.metrics.update(
                {
                    "inserted": write_report.records_inserted,
                    "draws_after": write_report.draws_after,
                }
            )
            state.last_run_id = write_report.run_id or dry.run_id
            state.consecutive_failures = 0
            state.circuit_state = next_state_after_success(state.circuit_state)
            await self.db.flush()
            return result
        except Exception as exc:  # noqa: BLE001
            logger.exception("scheduler tick failed")
            state.consecutive_failures = int(state.consecutive_failures or 0) + 1
            state.circuit_state = next_state_after_failure(
                state.circuit_state, state.consecutive_failures
            )
            if state.circuit_state == "open":
                state.circuit_opened_at = datetime.now(timezone.utc)
                state.circuit_reason = str(exc)[:500]
            await create_alert(
                self.db,
                code="scheduler_failed",
                title="Fallo de scheduler",
                message=str(exc),
                severity="error",
            )
            await self.db.flush()
            return SchedulerTickResult(
                status="failed",
                mode=mode,
                blocked_reason=str(exc),
                circuit_state=state.circuit_state,
                alerts=["scheduler_failed"],
                from_date=from_d.isoformat() if from_d else None,
                to_date=to_d.isoformat() if to_d else None,
            )
        finally:
            if handle:
                await release_sync_lock(handle)


async def status_payload(db: AsyncSession, *, database_url: str | None = None) -> dict[str, Any]:
    svc = LotterySchedulerService(db, database_url=database_url)
    state = await svc.get_or_create_state()
    max_draw = await db.scalar(select(func.max(LotteryDraw.draw_date)))
    return {
        "environment": state.environment,
        "enabled": state.enabled and settings.lottery_scheduler_enabled,
        "mode": svc._effective_mode(state),
        "configured_mode": settings.lottery_scheduler_mode,
        "interval_minutes": settings.lottery_sync_interval_minutes,
        "lookback_days": settings.lottery_sync_lookback_days,
        "timezone": settings.lottery_sync_timezone,
        "last_tick_at": state.last_tick_at.isoformat() if state.last_tick_at else None,
        "next_run_at": state.next_run_at.isoformat() if state.next_run_at else None,
        "last_run_id": str(state.last_run_id) if state.last_run_id else None,
        "consecutive_failures": state.consecutive_failures,
        "circuit_state": state.circuit_state,
        "circuit_opened_at": state.circuit_opened_at.isoformat() if state.circuit_opened_at else None,
        "circuit_reason": state.circuit_reason,
        "write_enabled_since": state.write_enabled_since.isoformat() if state.write_enabled_since else None,
        "sync_write_enabled": settings.lottery_sync_write_enabled,
        "automatic_write_enabled": settings.lottery_sync_automatic_write_enabled,
        "max_draw_date": max_draw.isoformat() if max_draw else None,
        "source_contract_version": state.source_contract_version
        or settings.lottery_source_contract_version,
        "allowed_database": settings.lottery_sync_allowed_database,
        "allowed_port": settings.lottery_sync_allowed_port,
    }
