"""Repositorios OneDrive/SharePoint configurables desde UI."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import AuditService
from app.services.repository_sync_service import FOLDER_DEFAULTS, RepositorySyncService


class IntegrationRepositoryService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self._sync = RepositorySyncService(db, tenant_id, user_id=actor_id)

    async def list_bindings(self) -> list[dict]:
        return await self._sync.list_bindings()

    async def upsert_binding(self, payload: dict) -> dict:
        row = await self._sync.upsert_binding(payload)
        await AuditService(self.db).log(
            action="settings.repository_updated",
            tenant_id=self.tenant_id,
            user_id=self.actor_id,
            resource_type="repository_binding",
            details={"folder_key": payload.get("folder_key"), "provider": payload.get("provider")},
        )
        return row

    async def sync_binding(self, binding_id: uuid.UUID) -> dict:
        result = await self._sync.sync_binding(binding_id, trigger="manual")
        await AuditService(self.db).log(
            action="settings.repository_synced",
            tenant_id=self.tenant_id,
            user_id=self.actor_id,
            resource_type="repository_binding",
            resource_id=binding_id,
            details={"ok": result.get("ok"), "indexed": result.get("indexed")},
        )
        return {
            "ok": result.get("ok", False),
            "indexed": result.get("indexed", 0),
            "records_indexed": result.get("records_indexed", 0),
            "job_id": result.get("job_id"),
            "message": result.get("message", ""),
        }

    async def sync_all(self) -> list[dict]:
        bindings = await self.list_bindings()
        results = []
        for b in bindings:
            if not b.get("id"):
                continue
            results.append(await self.sync_binding(uuid.UUID(str(b["id"]))))
        return results

    async def list_sync_jobs(self, *, limit: int = 50) -> list[dict]:
        return await self._sync.list_sync_jobs(limit=limit)

    @staticmethod
    def default_folders() -> list[dict]:
        return [
            {"folder_key": k, "label": label, "repository_type": rtype, "folder_path": path}
            for k, label, rtype, path in FOLDER_DEFAULTS
        ]
