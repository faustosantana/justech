"""Servicio de correo Microsoft 365 — bandeja tipo Outlook."""

from __future__ import annotations

import base64
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.m365_mail import (
    M365MailActionResponse,
    M365MailAttachment,
    M365MailComposeRequest,
    M365MailDetailResponse,
    M365MailListResponse,
    M365MailMessage,
    M365MailPatchRequest,
)
from app.services.m365_graph_errors import graph_error_message
from app.services.m365_graph_session import M365GraphSessionService
from integrations.microsoft365.errors import GraphError

_WRITE_BLOCKED_MSG = "Operación de escritura bloqueada por configuración del sistema"
from integrations.microsoft365.outlook import FOLDER_PATHS
from integrations.microsoft365.schemas import M365OutlookMessage


class M365MailService:
    FOLDERS = tuple(FOLDER_PATHS.keys())

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._sessions = M365GraphSessionService(db, tenant_id, user_id)

    def _write_blocked(self) -> M365MailActionResponse | None:
        if settings.m365_read_only:
            return M365MailActionResponse(ok=False, message=_WRITE_BLOCKED_MSG)
        return None

    def _graph_action_error(self, exc: Exception) -> M365MailActionResponse:
        if isinstance(exc, PermissionError):
            return M365MailActionResponse(ok=False, message=_WRITE_BLOCKED_MSG)
        if isinstance(exc, GraphError):
            return M365MailActionResponse(ok=False, message=graph_error_message(exc))
        return M365MailActionResponse(ok=False, message=str(exc))

    def _to_mail(self, msg: M365OutlookMessage, *, account_id: uuid.UUID, account_email: str | None) -> M365MailMessage:
        return M365MailMessage(
            id=msg.id or "",
            subject=msg.subject,
            sender=msg.sender,
            sender_name=msg.sender_name,
            to_recipients=msg.to_recipients,
            cc_recipients=getattr(msg, "cc_recipients", []) or [],
            received_at=msg.received_at,
            sent_at=msg.sent_at,
            preview=msg.preview,
            body_html=msg.body_html,
            body_text=msg.body_text,
            is_read=msg.is_read,
            has_attachments=msg.has_attachments,
            attachments=[
                M365MailAttachment(
                    id=a.id,
                    name=a.name,
                    size_bytes=a.size_bytes,
                    content_type=a.content_type,
                    is_inline=a.is_inline,
                )
                for a in msg.attachments
            ],
            web_link=msg.web_link,
            folder=msg.folder,
            account_id=account_id,
            account_email=account_email,
        )

    def _error_list(self, *, folder: str, exc: GraphError, account_id: uuid.UUID | None = None, email: str | None = None) -> M365MailListResponse:
        return M365MailListResponse(
            items=[],
            total=0,
            folder=folder,
            account_id=account_id,
            account_email=email,
            connected=False,
            read_only=settings.m365_read_only,
            message=graph_error_message(exc),
            error=exc.message,
            permission_hint=exc.permission_hint,
        )

    async def _build_attachments(self, sess, refs) -> list[dict]:
        out: list[dict] = []
        outlook = sess.client.outlook
        for ref in refs:
            if ref.content_base64:
                out.append(
                    outlook.file_attachment(
                        ref.name,
                        base64.b64decode(ref.content_base64),
                        ref.content_type,
                    )
                )
            elif ref.onedrive_item_id:
                item = await sess.client.onedrive.get_item(ref.onedrive_item_id)
                url = item.download_url or item.web_url
                if url:
                    out.append(outlook.reference_attachment(ref.name, url))
            elif ref.source_url:
                out.append(outlook.reference_attachment(ref.name, ref.source_url))
        return out

    async def list_messages(
        self,
        *,
        folder: str = "inbox",
        search: str = "",
        limit: int = 50,
        account_id: uuid.UUID | None = None,
        from_filter: str = "",
        has_attachments: bool | None = None,
    ) -> M365MailListResponse:
        folder = folder if folder in self.FOLDERS else "inbox"
        try:
            sess = await self._sessions.session_for_account(account_id)
            raw = await sess.client.outlook.list_messages(
                folder=folder,
                search=search,
                limit=limit,
                from_filter=from_filter,
                has_attachments=has_attachments,
            )
        except GraphError as exc:
            return self._error_list(folder=folder, exc=exc, account_id=account_id)

        items = [self._to_mail(m, account_id=sess.account.id, account_email=sess.email) for m in raw]
        return M365MailListResponse(
            items=items,
            total=len(items),
            folder=folder,
            account_id=sess.account.id,
            account_email=sess.email,
            connected=True,
            read_only=settings.m365_read_only,
            message=f"{len(items)} correos",
        )

    async def get_message(self, message_id: str, *, account_id: uuid.UUID | None = None) -> M365MailDetailResponse | None:
        try:
            sess = await self._sessions.session_for_account(account_id)
            msg = await sess.client.outlook.get_message(message_id)
        except GraphError:
            return None
        if not msg or not msg.id:
            return None
        base = self._to_mail(msg, account_id=sess.account.id, account_email=sess.email)
        write_ok = not settings.m365_read_only
        return M365MailDetailResponse(
            **base.model_dump(),
            connected=True,
            read_only=settings.m365_read_only,
            can_reply=write_ok,
            can_forward=write_ok,
            can_send=write_ok,
        )

    async def list_attachments(self, message_id: str, *, account_id: uuid.UUID | None = None) -> list[M365MailAttachment]:
        sess = await self._sessions.session_for_account(account_id)
        raw = await sess.client.outlook.list_attachments(message_id)
        return [
            M365MailAttachment(id=a.id, name=a.name, size_bytes=a.size_bytes, content_type=a.content_type, is_inline=a.is_inline)
            for a in raw
        ]

    async def patch_message(
        self, message_id: str, payload: M365MailPatchRequest, *, account_id: uuid.UUID | None = None
    ) -> M365MailActionResponse:
        if payload.is_read is not None or payload.move_to_folder:
            if blocked := self._write_blocked():
                return blocked
        try:
            sess = await self._sessions.session_for_account(account_id)
            if payload.is_read is not None:
                await sess.client.outlook.mark_read(message_id, is_read=payload.is_read)
            if payload.move_to_folder:
                await sess.client.outlook.move_message(message_id, destination_folder=payload.move_to_folder)
        except (GraphError, PermissionError) as exc:
            return self._graph_action_error(exc)
        return M365MailActionResponse(ok=True, message="Actualizado", message_id=message_id)

    async def reply_message(
        self, message_id: str, payload: M365MailComposeRequest, *, account_id: uuid.UUID | None = None
    ) -> M365MailActionResponse:
        if blocked := self._write_blocked():
            return blocked
        try:
            sess = await self._sessions.session_for_account(account_id)
            if payload.reply_all:
                await sess.client.outlook.reply_all(message_id, comment=payload.body)
            else:
                await sess.client.outlook.reply(message_id, comment=payload.body)
        except (GraphError, PermissionError) as exc:
            return self._graph_action_error(exc)
        return M365MailActionResponse(ok=True, message="Respuesta enviada", message_id=message_id)

    async def forward_message(
        self, message_id: str, payload: M365MailComposeRequest, *, account_id: uuid.UUID | None = None
    ) -> M365MailActionResponse:
        if blocked := self._write_blocked():
            return blocked
        if not payload.to:
            return M365MailActionResponse(ok=False, message="Indique destinatarios")
        try:
            sess = await self._sessions.session_for_account(account_id)
            await sess.client.outlook.forward(message_id, comment=payload.body, to=payload.to)
        except (GraphError, PermissionError) as exc:
            return self._graph_action_error(exc)
        return M365MailActionResponse(ok=True, message="Correo reenviado", message_id=message_id)

    async def send_mail(
        self, payload: M365MailComposeRequest, *, account_id: uuid.UUID | None = None
    ) -> M365MailActionResponse:
        if blocked := self._write_blocked():
            return blocked
        if not payload.to or not payload.subject:
            return M365MailActionResponse(ok=False, message="Asunto y destinatarios requeridos")
        try:
            sess = await self._sessions.session_for_account(account_id)
            atts = await self._build_attachments(sess, payload.attachments)
            if payload.save_draft:
                draft = await sess.client.outlook.create_draft(
                    subject=payload.subject or "",
                    body=payload.body,
                    to=payload.to,
                    cc=payload.cc,
                    attachments=atts or None,
                )
                return M365MailActionResponse(ok=True, message="Borrador guardado", message_id=draft.id)
            await sess.client.outlook.send_mail(
                subject=payload.subject or "",
                body=payload.body,
                to=payload.to,
                cc=payload.cc,
                attachments=atts or None,
            )
        except (GraphError, PermissionError) as exc:
            return self._graph_action_error(exc)
        return M365MailActionResponse(ok=True, message="Correo enviado")

    async def download_attachment(
        self, message_id: str, attachment_id: str, *, account_id: uuid.UUID | None = None
    ) -> tuple[bytes, str, str] | None:
        try:
            sess = await self._sessions.session_for_account(account_id)
            raw = await sess.client.outlook.list_attachments(message_id)
            meta = next((a for a in raw if a.id == attachment_id), None)
            if not meta:
                return None
            content = await sess.client.outlook.get_attachment_content(message_id, attachment_id)
            return content, meta.name or "adjunto", meta.content_type or "application/octet-stream"
        except GraphError:
            return None
