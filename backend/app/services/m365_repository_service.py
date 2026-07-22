"""Sincronización y clasificación de repositorios M365."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.integration_settings import IntegrationRepositoryBinding
from app.models.m365_repository import M365RepositoryFile
from app.schemas.m365_intelligence import M365RepositoryFileItem, M365RepositoryListResponse, M365RepositorySyncResponse
from app.services.m365_file_classifier import CATEGORY_LABELS, M365FileClassifier
from app.services.m365_graph_session import M365GraphSessionService
from app.services.m365_qdrant_service import M365QdrantService
from integrations.microsoft365.errors import GraphError


def _content_hash(name: str, size: int | None, modified: datetime | None) -> str:
    raw = f"{name}|{size}|{modified.isoformat() if modified else ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


@dataclass
class BindingSyncResult:
    ok: bool
    synced: int
    classified: int
    message: str
    files_new: int = 0
    files_updated: int = 0
    files_deleted: int = 0
    delta_link: str | None = None


class M365RepositoryService:
    MAX_DEPTH = 4
    MAX_FILES = 500

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._sessions = M365GraphSessionService(db, tenant_id, user_id)
        self._classifier = M365FileClassifier()

    async def sync_onedrive(self, *, account_id: uuid.UUID | None = None) -> M365RepositorySyncResponse:
        try:
            sess = await self._sessions.session_for_account(account_id)
        except GraphError as exc:
            return M365RepositorySyncResponse(ok=False, synced=0, classified=0, message=str(exc))

        await self.db.execute(
            delete(M365RepositoryFile).where(
                M365RepositoryFile.tenant_id == self.tenant_id,
                M365RepositoryFile.account_id == sess.account.id,
                M365RepositoryFile.source == "onedrive",
            )
        )

        synced = 0
        classified = 0
        queue: list[tuple[str | None, str, int]] = [(None, "", 0)]

        while queue and synced < self.MAX_FILES:
            folder_id, parent_path, depth = queue.pop(0)
            if depth > self.MAX_DEPTH:
                continue
            try:
                items = await sess.client.onedrive.list_items(
                    folder_id=folder_id,
                    limit=100,
                )
            except GraphError:
                continue
            for item in items:
                if synced >= self.MAX_FILES:
                    break
                name = (item.name or "").strip()
                if not name or name.lower() == "sin nombre":
                    continue
                path = f"{parent_path}/{name}".strip("/")
                cls = self._classifier.classify(name=name, parent_path=parent_path, mime_type=item.mime_type)
                if not item.is_folder:
                    classified += 1
                row = M365RepositoryFile(
                    tenant_id=self.tenant_id,
                    account_id=sess.account.id,
                    source="onedrive",
                    graph_item_id=item.id or f"od-{synced}",
                    parent_path=parent_path,
                    name=name,
                    mime_type=item.mime_type,
                    size_bytes=item.size_bytes,
                    web_url=item.web_url,
                    download_url=item.download_url,
                    is_folder=bool(item.is_folder),
                    document_category=cls.document_category,
                    document_type=cls.document_type,
                    folder_category=cls.folder_category,
                    classification_confidence=cls.confidence,
                    tags=cls.tags,
                    company_key=cls.company_key,
                    modified_at_graph=item.modified_at,
                )
                self.db.add(row)
                if not item.is_folder:
                    self._index_qdrant(row)
                synced += 1
                if item.is_folder and item.id:
                    queue.append((item.id, path, depth + 1))

        await self.db.commit()
        return M365RepositorySyncResponse(
            ok=True,
            synced=synced,
            classified=classified,
            message=f"{synced} elementos indexados (OneDrive), {classified} archivos clasificados",
        )

    async def sync_sharepoint(self, *, account_id: uuid.UUID | None = None) -> M365RepositorySyncResponse:
        try:
            sess = await self._sessions.session_for_account(account_id)
        except GraphError as exc:
            return M365RepositorySyncResponse(ok=False, synced=0, classified=0, message=str(exc))

        await self.db.execute(
            delete(M365RepositoryFile).where(
                M365RepositoryFile.tenant_id == self.tenant_id,
                M365RepositoryFile.account_id == sess.account.id,
                M365RepositoryFile.source == "sharepoint",
            )
        )

        synced = 0
        classified = 0
        sites = await sess.client.sharepoint.list_sites(limit=15)
        for site in sites[:10]:
            if not site.id:
                continue
            drives = await sess.client.sharepoint.list_site_drives(site.id, limit=5)
            for drive in drives[:3]:
                drive_id = drive.get("id")
                if not drive_id:
                    continue
                queue: list[tuple[str | None, str, int]] = [(None, f"{site.name}/{drive.get('name', '')}", 0)]
                while queue and synced < self.MAX_FILES:
                    folder_id, parent_path, depth = queue.pop(0)
                    if depth > self.MAX_DEPTH:
                        continue
                    try:
                        items = await sess.client.sharepoint.list_drive_items(
                            drive_id, folder_id=folder_id, limit=80
                        )
                    except GraphError:
                        continue
                    for item in items:
                        if synced >= self.MAX_FILES:
                            break
                        name = (item.name or "").strip()
                        if not name or name.lower() == "sin nombre":
                            continue
                        cls = self._classifier.classify(name=name, parent_path=parent_path, mime_type=item.mime_type)
                        if not item.is_folder:
                            classified += 1
                        row = M365RepositoryFile(
                            tenant_id=self.tenant_id,
                            account_id=sess.account.id,
                            source="sharepoint",
                            graph_item_id=item.id or f"sp-{synced}",
                            drive_id=drive_id,
                            parent_path=parent_path,
                            name=name,
                            mime_type=item.mime_type,
                            size_bytes=item.size_bytes,
                            web_url=item.web_url,
                            download_url=item.download_url,
                            is_folder=bool(item.is_folder),
                            document_category=cls.document_category,
                            document_type=cls.document_type,
                            folder_category=cls.folder_category,
                            classification_confidence=cls.confidence,
                            tags=cls.tags,
                            company_key=cls.company_key,
                            modified_at_graph=item.modified_at,
                        )
                        self.db.add(row)
                        if not item.is_folder:
                            self._index_qdrant(row)
                        synced += 1
                        if item.is_folder and item.id:
                            queue.append((item.id, f"{parent_path}/{name}".strip("/"), depth + 1))

        await self.db.commit()
        return M365RepositorySyncResponse(
            ok=True,
            synced=synced,
            classified=classified,
            message=f"{synced} elementos SharePoint indexados, {classified} clasificados",
        )

    async def sync_binding(
        self,
        binding: IntegrationRepositoryBinding,
        *,
        use_delta: bool = True,
        account_id: uuid.UUID | None = None,
    ) -> BindingSyncResult:
        try:
            sess = await self._sessions.session_for_account(account_id)
        except GraphError as exc:
            return BindingSyncResult(ok=False, synced=0, classified=0, message=str(exc))

        folder_id = binding.graph_item_id
        if not folder_id and binding.folder_path:
            resolved = await sess.client.onedrive.resolve_folder_by_path(binding.folder_path)
            if not resolved or not resolved.id:
                try:
                    resolved = await sess.client.onedrive.ensure_folder_by_path(binding.folder_path)
                except Exception:
                    resolved = None
            if resolved and resolved.id:
                folder_id = resolved.id
                binding.graph_item_id = resolved.id
                binding.drive_id = binding.drive_id or (resolved.path or None)

        if not folder_id:
            return BindingSyncResult(
                ok=False, synced=0, classified=0,
                message="No se pudo resolver la carpeta OneDrive. Configure folder_path o graph_item_id.",
            )

        root_prefix = (binding.folder_path or "").strip("/").lower()
        files_new = files_updated = files_deleted = classified = synced = 0
        delta_final: str | None = None

        all_tenant_rows = (
            await self.db.execute(
                select(M365RepositoryFile).where(M365RepositoryFile.tenant_id == self.tenant_id)
            )
        ).scalars().all()
        by_graph_id = {r.graph_item_id: r for r in all_tenant_rows}
        existing_rows = [r for r in all_tenant_rows if r.binding_id == binding.id]

        used_crawl = False
        if use_delta and binding.delta_link:
            items, delta_final, deleted_ids = await sess.client.onedrive.collect_delta(
                delta_link=binding.delta_link
            )
            for gid in deleted_ids:
                row = by_graph_id.get(gid)
                if row:
                    row.is_deleted = True
                    files_deleted += 1
        elif use_delta:
            items, delta_final, deleted_ids = await sess.client.onedrive.collect_delta(folder_id=folder_id)
            for gid in deleted_ids:
                row = by_graph_id.get(gid)
                if row:
                    row.is_deleted = True
                    files_deleted += 1
        else:
            items = await self._crawl_folder(sess, folder_id, root_prefix)
            used_crawl = True

        for item in items:
            if not item.id:
                continue
            name = (item.name or "").strip()
            if not name or name.lower() == "sin nombre":
                continue
            parent_path = self._relative_parent(item.path, root_prefix)
            if item.is_folder:
                parent_path = f"{parent_path}/{name}".strip("/") if parent_path else name
            cls = self._classifier.classify(name=name, parent_path=parent_path, mime_type=item.mime_type)
            content_hash = _content_hash(name, item.size_bytes, item.modified_at)
            row = by_graph_id.get(item.id)
            is_new = row is None
            if is_new:
                row = M365RepositoryFile(
                    tenant_id=self.tenant_id,
                    account_id=sess.account.id,
                    source="onedrive",
                    graph_item_id=item.id,
                    binding_id=binding.id,
                )
                self.db.add(row)
                by_graph_id[item.id] = row
                files_new += 1
            elif row.content_hash != content_hash:
                files_updated += 1
            elif not item.is_folder and not row.download_url:
                files_updated += 1
            else:
                continue

            download_url = item.download_url
            if not item.is_folder and not download_url and item.id:
                try:
                    download_url = await sess.client.onedrive.get_download_url(item.id)
                except GraphError:
                    download_url = None

            row.parent_path = parent_path
            row.name = name
            row.mime_type = item.mime_type
            row.size_bytes = item.size_bytes
            row.web_url = item.web_url
            row.download_url = download_url
            row.is_folder = bool(item.is_folder)
            row.is_deleted = False
            row.document_category = cls.document_category
            row.document_type = cls.document_type
            row.folder_category = cls.folder_category
            row.classification_confidence = cls.confidence
            row.tags = cls.tags
            row.company_key = cls.company_key or binding.company_key
            row.modified_at_graph = item.modified_at
            row.content_hash = content_hash
            row.binding_id = binding.id
            synced += 1
            if not item.is_folder:
                classified += 1
                self._index_qdrant(row)
                await self._maybe_cache_dgcp_template(row, download_url, sess)

        if used_crawl:
            crawled_ids = {i.id for i in items if i.id}
            for row in existing_rows:
                if row.graph_item_id not in crawled_ids and not row.is_deleted:
                    row.is_deleted = True
                    files_deleted += 1

        await self.db.flush()
        msg = (
            f"{synced} elementos en {binding.label or binding.folder_key}: "
            f"{files_new} nuevos, {files_updated} actualizados, {files_deleted} eliminados"
        )
        return BindingSyncResult(
            ok=True,
            synced=synced,
            classified=classified,
            message=msg,
            files_new=files_new,
            files_updated=files_updated,
            files_deleted=files_deleted,
            delta_link=delta_final,
        )

    async def _crawl_folder(self, sess, folder_id: str, root_prefix: str) -> list:
        from integrations.microsoft365.schemas import M365DriveItem

        found: list[M365DriveItem] = []
        queue: list[tuple[str, str, int]] = [(folder_id, "", 0)]
        while queue and len(found) < self.MAX_FILES:
            fid, parent_path, depth = queue.pop(0)
            if depth > self.MAX_DEPTH:
                continue
            try:
                children = await sess.client.onedrive.list_items(folder_id=fid, limit=100)
            except GraphError:
                continue
            for item in children:
                if len(found) >= self.MAX_FILES:
                    break
                name = item.name or ""
                path = f"{parent_path}/{name}".strip("/")
                found.append(item)
                if item.is_folder and item.id:
                    queue.append((item.id, path, depth + 1))
        return found

    @staticmethod
    def _relative_parent(graph_path: str | None, root_prefix: str) -> str:
        if not graph_path:
            return ""
        clean = graph_path.replace("/drive/root:", "").strip("/")
        if root_prefix and clean.lower().startswith(root_prefix):
            clean = clean[len(root_prefix) :].strip("/")
        parts = clean.split("/")
        return "/".join(parts[:-1]) if len(parts) > 1 else ""

    async def sync_all(self, *, account_id: uuid.UUID | None = None) -> M365RepositorySyncResponse:
        od = await self.sync_onedrive(account_id=account_id)
        sp = await self.sync_sharepoint(account_id=account_id)
        return M365RepositorySyncResponse(
            ok=od.ok and sp.ok,
            synced=od.synced + sp.synced,
            classified=od.classified + sp.classified,
            message=f"{od.message}. {sp.message}",
        )

    def _index_qdrant(self, row: M365RepositoryFile) -> None:
        qdrant = M365QdrantService(self.tenant_id)
        qdrant.upsert_document(
            doc_id=row.graph_item_id,
            title=row.name,
            text=f"{row.name} {row.parent_path} {row.document_category} {row.document_type}",
            source=row.source,
            category=row.document_category,
            url=row.web_url or "",
            metadata={"document_type": row.document_type, "tags": row.tags},
        )

    async def list_files(
        self,
        *,
        category: str | None = None,
        search: str = "",
        limit: int = 100,
        account_id: uuid.UUID | None = None,
    ) -> M365RepositoryListResponse:
        q = select(M365RepositoryFile).where(M365RepositoryFile.tenant_id == self.tenant_id)
        if account_id:
            q = q.where(M365RepositoryFile.account_id == account_id)
        if category:
            q = q.where(M365RepositoryFile.document_category == category)
        if search.strip():
            like = f"%{search.strip().lower()}%"
            q = q.where(func.lower(M365RepositoryFile.name).like(like))
        q = q.order_by(M365RepositoryFile.document_category, M365RepositoryFile.name).limit(limit)
        result = await self.db.execute(q)
        rows = list(result.scalars().all())

        cat_q = (
            select(M365RepositoryFile.document_category, func.count())
            .where(M365RepositoryFile.tenant_id == self.tenant_id, M365RepositoryFile.is_folder.is_(False))
            .group_by(M365RepositoryFile.document_category)
        )
        cat_result = await self.db.execute(cat_q)
        categories = {row[0]: row[1] for row in cat_result.all()}

        items = [
            M365RepositoryFileItem(
                id=r.id,
                name=r.name,
                source=r.source,
                parent_path=r.parent_path,
                document_category=r.document_category,
                document_category_label=CATEGORY_LABELS.get(r.document_category, r.document_category),
                document_type=r.document_type,
                classification_confidence=r.classification_confidence,
                tags=r.tags or [],
                company_key=r.company_key,
                is_folder=r.is_folder,
                mime_type=r.mime_type,
                size_bytes=r.size_bytes,
                web_url=r.web_url,
                download_url=r.download_url,
                graph_item_id=r.graph_item_id,
                synced_at=r.synced_at,
            )
            for r in rows
        ]
        return M365RepositoryListResponse(
            items=items,
            total=len(items),
            categories=categories,
            connected=True,
            message=f"{len(items)} documentos en repositorio",
        )

    async def upsert_m365_item(
        self,
        binding: IntegrationRepositoryBinding,
        item,
        *,
        source_type: str = "onedrive",
        download_content: bytes | None = None,
    ) -> M365RepositoryFile:
        """Indexa un ítem M365 en el repositorio JAIOS (vincular o importar)."""
        from integrations.microsoft365.schemas import M365DriveItem

        if not isinstance(item, M365DriveItem):
            raise ValueError("Ítem Graph inválido")
        if not item.id or item.is_folder:
            raise ValueError("Seleccione un archivo, no una carpeta.")

        sess = await self._sessions.session_for_account(None)
        root_prefix = (binding.folder_path or "").strip("/").lower()
        parent_path = self._relative_parent(item.path, root_prefix)
        name = (item.name or "documento").strip()
        cls = self._classifier.classify(name=name, parent_path=parent_path, mime_type=item.mime_type)
        content_hash = _content_hash(name, item.size_bytes, item.modified_at)

        row = (
            await self.db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.tenant_id == self.tenant_id,
                    M365RepositoryFile.graph_item_id == item.id,
                )
            )
        ).scalar_one_or_none()

        download_url = item.download_url
        if not download_url and item.id:
            try:
                download_url = await sess.client.onedrive.get_download_url(item.id)
            except GraphError:
                download_url = None

        if row is None:
            row = M365RepositoryFile(
                tenant_id=self.tenant_id,
                account_id=sess.account.id,
                source=source_type if source_type in ("onedrive", "sharepoint") else "onedrive",
                graph_item_id=item.id,
                binding_id=binding.id,
            )
            self.db.add(row)

        row.parent_path = parent_path
        row.name = name
        row.mime_type = item.mime_type
        row.size_bytes = item.size_bytes
        row.web_url = item.web_url
        row.download_url = download_url
        row.is_folder = False
        row.is_deleted = False
        row.document_category = cls.document_category
        row.document_type = cls.document_type
        row.folder_category = cls.folder_category
        row.classification_confidence = cls.confidence
        row.tags = cls.tags
        row.company_key = cls.company_key or binding.company_key
        row.modified_at_graph = item.modified_at
        row.content_hash = content_hash
        row.binding_id = binding.id
        row.synced_at = datetime.now(UTC)

        await self.db.flush()
        self._index_qdrant(row)
        count = await self.db.scalar(
            select(func.count()).select_from(M365RepositoryFile).where(
                M365RepositoryFile.tenant_id == self.tenant_id,
                M365RepositoryFile.binding_id == binding.id,
                M365RepositoryFile.is_deleted.is_(False),
                M365RepositoryFile.is_folder.is_(False),
            )
        )
        binding.indexed_files = int(count or 0)
        await self.db.commit()
        await self.db.refresh(row)
        if download_content and not row.is_folder:
            from app.services.document_autofill.m365_template_cache import write_cached_bytes
            from app.services.document_autofill.m365_template_catalog import is_dgcp_template_candidate

            if is_dgcp_template_candidate(row):
                write_cached_bytes(row.id, download_content)
        return row

    async def _maybe_cache_dgcp_template(self, row: M365RepositoryFile, download_url: str | None, sess) -> None:
        """Persist bytes de plantillas DGCP durante sync para autollenado offline."""
        from app.services.document_autofill.m365_template_cache import read_cached_bytes, write_cached_bytes
        from app.services.document_autofill.m365_template_catalog import is_dgcp_template_candidate

        if row.is_folder or not is_dgcp_template_candidate(row):
            return
        if read_cached_bytes(row.id):
            return
        content: bytes | None = None
        if download_url:
            import httpx

            try:
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                    resp = await client.get(download_url)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        content = resp.content
            except httpx.HTTPError:
                content = None
        if not content and row.graph_item_id:
            try:
                from app.services.m365_documents_service import M365DocumentsService

                docs = M365DocumentsService(self.db, self.tenant_id, sess.account.jaios_user_id)
                item = await docs._resolve_item(row.graph_item_id, drive_id=row.drive_id, source_type=row.source)
                content = await docs._download_item(item, drive_id=row.drive_id, source_type=row.source)
            except Exception:
                content = None
        if content:
            write_cached_bytes(row.id, content)
