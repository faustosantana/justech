"""Sincronización M365 + caché oficial de plantillas DGCP para autollenado."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.m365_account import M365UserAccount
from app.models.m365_repository import M365RepositoryFile
from app.services.document_autofill.m365_template_cache import (
    cache_status,
    is_likely_stub,
    list_cached_ids,
    read_cached_bytes,
    write_cached_bytes,
)
from app.services.document_autofill.m365_template_catalog import is_dgcp_template_candidate
from app.services.document_autofill.m365_template_resolver import M365TemplateReference, M365TemplateResolver
from app.services.m365_repository_service import M365RepositoryService

logger = logging.getLogger(__name__)

_CACHE_META = (
    Path(getattr(settings, "documents_storage_path", "/var/jaios/documents"))
    / "m365_template_cache"
    / "_bootstrap_meta.json"
)


@dataclass
class CacheBootstrapResult:
    ok: int = 0
    skipped: int = 0
    failed: int = 0
    failures: list[str] = field(default_factory=list)


@dataclass
class OfficialTemplateOperationalStatus:
    oauth_connected: bool
    oauth_email: str | None
    oauth_accounts_connected: int
    oauth_last_sync_at: str | None
    templates_indexed: int
    templates_docx: int
    templates_pdf: int
    cache_count: int
    cache_missing_docx: int
    last_cache_bootstrap_at: str | None
    stubs_blocked: bool = True
    message: str = ""


@dataclass
class SyncAndCacheResult:
    repository_ok: bool
    repository_synced: int
    repository_message: str
    cache: CacheBootstrapResult
    operational: OfficialTemplateOperationalStatus


class M365OfficialTemplateSyncService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.resolver = M365TemplateResolver(db, tenant_id, user_id)

    async def operational_status(self) -> OfficialTemplateOperationalStatus:
        accounts = (
            await self.db.execute(
                select(M365UserAccount).where(
                    M365UserAccount.tenant_id == self.tenant_id,
                    M365UserAccount.is_active.is_(True),
                )
            )
        ).scalars().all()
        connected = [a for a in accounts if a.connection_status == "connected" and a.connection_mode == "oauth"]
        primary = connected[0] if connected else None

        rows = (
            await self.db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.tenant_id == self.tenant_id,
                    M365RepositoryFile.is_deleted.is_(False),
                    M365RepositoryFile.is_folder.is_(False),
                )
            )
        ).scalars().all()
        candidates = [r for r in rows if is_dgcp_template_candidate(r)]
        docx_rows = [r for r in candidates if (r.name or "").lower().endswith(".docx")]
        pdf_rows = [r for r in candidates if (r.name or "").lower().endswith(".pdf")]
        cached_ids = {str(x) for x in list_cached_ids()}
        missing = sum(1 for r in docx_rows if str(r.id) not in cached_ids)

        meta = self._read_meta()
        msg = ""
        if not connected:
            msg = "OAuth M365 desconectado — reconecte en Cuentas M365."
        elif missing:
            msg = f"{missing} plantillas DOCX sin caché oficial — sincronice plantillas."

        return OfficialTemplateOperationalStatus(
            oauth_connected=bool(connected),
            oauth_email=primary.email if primary else None,
            oauth_accounts_connected=len(connected),
            oauth_last_sync_at=primary.last_sync_at.isoformat() if primary and primary.last_sync_at else None,
            templates_indexed=len(candidates),
            templates_docx=len(docx_rows),
            templates_pdf=len(pdf_rows),
            cache_count=len(cached_ids),
            cache_missing_docx=missing,
            last_cache_bootstrap_at=meta.get("last_bootstrap_at"),
            message=msg,
        )

    async def bootstrap_official_cache(self) -> CacheBootstrapResult:
        result = CacheBootstrapResult()
        rows = (
            await self.db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.tenant_id == self.tenant_id,
                    M365RepositoryFile.is_deleted.is_(False),
                    M365RepositoryFile.is_folder.is_(False),
                )
            )
        ).scalars().all()
        docx_rows = [
            r for r in rows if is_dgcp_template_candidate(r) and (r.name or "").lower().endswith(".docx")
        ]

        for row in sorted(docx_rows, key=lambda r: (r.name or "").lower()):
            if read_cached_bytes(row.id):
                st = cache_status(row.id)
                if not st.likely_stub:
                    result.skipped += 1
                    continue
            ref = M365TemplateReference(
                form_type="",
                m365_file_id=row.id,
                graph_item_id=row.graph_item_id,
                drive_id=row.drive_id,
                source=row.source,
                name=row.name,
                web_url=row.web_url,
                parent_path=row.parent_path or "",
                content_hash=row.content_hash,
                template_version=row.content_hash or "index",
                document_type=row.document_type or "general",
            )
            try:
                content = await self.resolver.download_bytes(ref)
                if is_likely_stub(content):
                    result.failed += 1
                    result.failures.append(f"{row.name}: stub detectado")
                    continue
                write_cached_bytes(row.id, content)
                result.ok += 1
            except Exception as exc:
                result.failed += 1
                result.failures.append(f"{row.name}: {exc}")
                logger.warning("template_cache_bootstrap_failed name=%s err=%s", row.name, exc)

        self._write_meta(
            {
                "last_bootstrap_at": datetime.now(UTC).isoformat(),
                "ok": result.ok,
                "skipped": result.skipped,
                "failed": result.failed,
            }
        )
        return result

    async def sync_repository_and_cache(
        self,
        *,
        account_id: uuid.UUID | None = None,
    ) -> SyncAndCacheResult:
        repo = M365RepositoryService(self.db, self.tenant_id, self.user_id)
        sync = await repo.sync_all(account_id=account_id)
        cache = await self.bootstrap_official_cache()
        operational = await self.operational_status()
        return SyncAndCacheResult(
            repository_ok=sync.ok,
            repository_synced=sync.synced,
            repository_message=sync.message,
            cache=cache,
            operational=operational,
        )

    @staticmethod
    def _read_meta() -> dict:
        if _CACHE_META.is_file():
            try:
                return json.loads(_CACHE_META.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    @staticmethod
    def _write_meta(data: dict) -> None:
        _CACHE_META.parent.mkdir(parents=True, exist_ok=True)
        existing = M365OfficialTemplateSyncService._read_meta()
        existing.update(data)
        _CACHE_META.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
