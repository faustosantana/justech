"""Persistencia de alertas de sync/scheduler (sin notificaciones externas)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotterySyncAlert


async def create_alert(
    db: AsyncSession,
    *,
    code: str,
    title: str,
    message: str,
    severity: str = "warning",
    environment: str = "staging",
    sync_run_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> LotterySyncAlert:
    alert = LotterySyncAlert(
        environment=environment,
        severity=severity,
        code=code,
        title=title,
        message=message[:4000],
        sync_run_id=sync_run_id,
        status="open",
        metadata_=metadata or {},
    )
    db.add(alert)
    await db.flush()
    return alert


async def list_alerts(
    db: AsyncSession,
    *,
    environment: str = "staging",
    status: str | None = "open",
    limit: int = 50,
) -> list[LotterySyncAlert]:
    q = select(LotterySyncAlert).where(LotterySyncAlert.environment == environment)
    if status:
        q = q.where(LotterySyncAlert.status == status)
    q = q.order_by(LotterySyncAlert.created_at.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def acknowledge_alert(
    db: AsyncSession, alert_id: uuid.UUID, *, by: str
) -> LotterySyncAlert | None:
    alert = await db.get(LotterySyncAlert, alert_id)
    if not alert:
        return None
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = by
    await db.flush()
    return alert


async def resolve_alert(
    db: AsyncSession, alert_id: uuid.UUID, *, by: str
) -> LotterySyncAlert | None:
    alert = await db.get(LotterySyncAlert, alert_id)
    if not alert:
        return None
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = by
    await db.flush()
    return alert
