"""Notifications Center service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.task import Task
from app.schemas.notifications import NotificationListResponse, NotificationResponse


class NotificationService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        title: str,
        message: str,
        type: str,
        severity: str = "info",
        related_task_id: uuid.UUID | None = None,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
    ) -> Notification:
        notif = Notification(
            tenant_id=self.tenant_id,
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            severity=severity,
            related_task_id=related_task_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
        self.db.add(notif)
        await self.db.flush()
        return notif

    async def _notification_scope_clause(self):
        if not self.user_id:
            return None
        from app.services.company_scope_filter import CompanyScopeFilter

        clause = await CompanyScopeFilter(
            self.db, self.tenant_id, self.user_id
        ).task_company_clause(Task.company_id)
        if clause is None:
            return None
        return or_(Notification.related_task_id.is_(None), clause)

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> NotificationListResponse:
        q = select(Notification).where(
            Notification.tenant_id == self.tenant_id,
            Notification.user_id == user_id,
        )
        scope_clause = await self._notification_scope_clause()
        if scope_clause is not None:
            q = q.outerjoin(Task, Notification.related_task_id == Task.id).where(scope_clause)
        if unread_only:
            q = q.where(Notification.is_read.is_(False))
        q = q.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.db.execute(q)
        items = list(result.scalars().all())

        unread = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        unread_count = unread.scalar_one()

        return NotificationListResponse(
            items=[NotificationResponse.model_validate(n) for n in items],
            total=len(items),
            unread_count=unread_count,
        )

    async def search_for_user(
        self,
        user_id: uuid.UUID,
        query: str,
        *,
        limit: int = 10,
    ) -> list[NotificationResponse]:
        pattern = f"%{query.strip()}%"
        q = (
            select(Notification)
            .where(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
                or_(
                    Notification.title.ilike(pattern),
                    Notification.message.ilike(pattern),
                ),
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(q)
        return [NotificationResponse.model_validate(n) for n in result.scalars().all()]

    async def unread_count(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalar_one()

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
            )
        )
        notif = result.scalar_one_or_none()
        if not notif:
            return None
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        await self.db.flush()
        return notif

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        return result.rowcount or 0
