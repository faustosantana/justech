"""Upload de archivos a OneDrive y SharePoint."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.m365_intelligence import M365UploadResponse
from app.services.m365_graph_errors import graph_error_message
from app.services.m365_graph_session import M365GraphSessionService
from integrations.microsoft365.errors import GraphError

_WRITE_BLOCKED = "Operación de escritura bloqueada por configuración del sistema"


class M365UploadService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._sessions = M365GraphSessionService(db, tenant_id, user_id)

    def _blocked(self) -> M365UploadResponse | None:
        if settings.m365_read_only:
            return M365UploadResponse(ok=False, message=_WRITE_BLOCKED)
        return None

    async def upload_onedrive(
        self,
        *,
        name: str,
        content: bytes,
        folder_id: str | None = None,
        content_type: str = "application/octet-stream",
        account_id: uuid.UUID | None = None,
    ) -> M365UploadResponse:
        if blocked := self._blocked():
            return blocked
        try:
            sess = await self._sessions.session_for_account(account_id)
            item = await sess.client.onedrive.upload_file(
                name=name, content=content, folder_id=folder_id, content_type=content_type
            )
        except (GraphError, PermissionError) as exc:
            msg = _WRITE_BLOCKED if isinstance(exc, PermissionError) else graph_error_message(exc)
            return M365UploadResponse(ok=False, message=msg)
        return M365UploadResponse(
            ok=True,
            message=f"Archivo {name} subido a OneDrive",
            item_id=item.id,
            web_url=item.web_url,
        )

    async def upload_sharepoint(
        self,
        *,
        drive_id: str,
        name: str,
        content: bytes,
        folder_id: str | None = None,
        content_type: str = "application/octet-stream",
        account_id: uuid.UUID | None = None,
    ) -> M365UploadResponse:
        if blocked := self._blocked():
            return blocked
        try:
            sess = await self._sessions.session_for_account(account_id)
            item = await sess.client.sharepoint.upload_file(
                drive_id,
                name=name,
                content=content,
                folder_id=folder_id,
                content_type=content_type,
            )
        except (GraphError, PermissionError) as exc:
            msg = _WRITE_BLOCKED if isinstance(exc, PermissionError) else graph_error_message(exc)
            return M365UploadResponse(ok=False, message=msg)
        return M365UploadResponse(
            ok=True,
            message=f"Archivo {name} subido a SharePoint",
            item_id=item.id,
            web_url=item.web_url,
        )
