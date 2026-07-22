"""Recordatorios automáticos de pendientes documentales (3 y 7 días)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_pending import DocumentPendingItem
from app.models.user import User
from app.schemas.tasks import TaskCreateRequest
from app.services.document_pending_service import DocumentPendingService, LEGAL_LABELS
from app.config import settings
from app.services.document_outlook_email_service import DocumentOutlookEmailService
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


class DocumentPendingReminderService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def process_due_reminders(self) -> dict:
        now = datetime.now(UTC)
        rows = list(
            (
                await self.db.execute(
                    select(DocumentPendingItem).where(
                        DocumentPendingItem.tenant_id == self.tenant_id,
                        DocumentPendingItem.status == "requested",
                    )
                )
            ).scalars().all()
        )
        reminders = escalations = 0
        for row in rows:
            if not row.requested_at:
                continue
            age_days = (now - row.requested_at).days
            if age_days >= DocumentPendingService.ESCALATION_DAYS and row.reminder_count < 2:
                await self._notify(row, escalate=True)
                row.reminder_count = 2
                row.requested_to_email = DocumentPendingService.ESCALATION_RECIPIENT
                escalations += 1
            elif age_days >= DocumentPendingService.REMINDER_DAYS and row.reminder_count < 1:
                await self._notify(row, escalate=False)
                row.reminder_count = 1
                reminders += 1
        await self.db.commit()
        return {"reminders": reminders, "escalations": escalations}

    async def _notify(self, row: DocumentPendingItem, *, escalate: bool) -> None:
        recipient_email = (
            DocumentOutlookEmailService.escalation_recipient()
            if escalate
            else DocumentOutlookEmailService.notify_recipient()
        )
        user = (
            await self.db.execute(select(User).where(User.email == recipient_email))
        ).scalar_one_or_none()
        label = LEGAL_LABELS.get(row.item_key, row.item_label)
        title = (
            f"Escalación documental — {row.company_key}"
            if escalate
            else f"Recordatorio documental — {row.company_key}"
        )
        body = (
            f"Pendiente sin recibir ({row.reminder_count + 1}° aviso):\n"
            f"Empresa: {row.company_key}\n"
            f"Ítem: {label}\n"
            f"Ruta OneDrive: {row.onedrive_path or '—'}\n"
            f"Archivo sugerido: {row.suggested_filename or '—'}"
        )
        if user:
            notif = NotificationService(self.db, self.tenant_id)
            await notif.create(
                user_id=user.id,
                title=title,
                message=body,
                type="document_pending",
                severity="warning" if escalate else "info",
                related_entity_type="company",
                related_entity_id=row.company_key,
            )
            tasks = TaskService(self.db, self.tenant_id)
            await tasks.create_task(
                TaskCreateRequest(
                    title=title,
                    description=body,
                    category="documento",
                    department="legal",
                    priority="alta" if escalate else "media",
                    assigned_to_id=user.id,
                )
            )
        if settings.documents_outlook_auto_send:
            subject = title
            mail_body = (
                f"Hola,\n\n{body}\n\n"
                f"Este es un aviso automático de JAIOS.\n\nGracias."
            )
            await DocumentOutlookEmailService(self.db, self.tenant_id).send(
                to=recipient_email,
                subject=subject,
                body=mail_body,
            )

        logger.info(
            "Document reminder tenant=%s company=%s item=%s escalate=%s recipient=%s",
            self.tenant_id,
            row.company_key,
            row.item_key,
            escalate,
            recipient_email,
        )
