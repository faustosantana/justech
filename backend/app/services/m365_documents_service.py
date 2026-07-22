"""Microsoft 365 — búsqueda, navegación, vínculo e importación documental."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.knowledge import KnowledgeAsset
from app.models.m365_repository import M365RepositoryFile
from app.schemas.m365_documents import (
    M365DocumentActionResponse,
    M365DocumentBrowseResponse,
    M365DocumentItemResponse,
    M365DocumentSearchResponse,
)
from app.services.company_profile_field_service import FIELD_DEFINITIONS, CompanyProfileFieldService
from app.services.company_representative_service import CompanyRepresentativeService, FIELD_TO_DOC_TYPE
from app.services.m365_graph_session import M365GraphSessionService
from integrations.microsoft365.errors import GraphError
from integrations.microsoft365.query_utils import is_path_like_query, normalize_folder_path
from integrations.microsoft365.schemas import M365DriveItem

logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    "onedrive": "OneDrive Business",
    "sharepoint": "SharePoint",
    "teams": "Teams",
    "outlook_attachment": "Outlook adjunto",
    "repository": "Repositorio JAIOS",
}


class M365DocumentsService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def search(self, query: str, *, limit: int = 40) -> M365DocumentSearchResponse:
        q = query.strip()
        if not q:
            return M365DocumentSearchResponse(message="Indique un término de búsqueda")

        if is_path_like_query(q):
            return await self.browse_by_path(q, limit=limit)

        items: dict[str, M365DocumentItemResponse] = {}

        repo_rows = (
            await self.db.execute(
                self._repository_search_query(q, limit)
            )
        ).scalars().all()
        for row in repo_rows:
            items[f"repo:{row.id}"] = self._from_repository(row)

        connected = True
        message = f"{len(items)} resultado(s) en repositorio indexado"
        graph_error: GraphError | None = None

        try:
            sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
            od = await sess.client.onedrive.list_items(search=q, limit=min(limit, 25))
            for row in od:
                if row.is_folder:
                    continue
                key = f"od:{row.id}"
                if key not in items:
                    items[key] = self._from_drive_item(row, "onedrive")
            sites = await sess.client.sharepoint.list_sites(search=q, limit=5)
            for site in sites:
                if not site.id:
                    continue
                drives = await sess.client.sharepoint.list_site_drives(site.id, limit=3)
                for drive in drives:
                    drive_id = drive.get("id")
                    if not drive_id:
                        continue
                    sp_items = await sess.client.sharepoint.list_drive_items(
                        drive_id, search=q, limit=10
                    )
                    for row in sp_items:
                        if row.is_folder:
                            continue
                        key = f"sp:{row.id}"
                        if key not in items:
                            items[key] = self._from_drive_item(
                                row, "sharepoint", drive_id=drive_id, site_id=site.id
                            )
            message = f"{len(items)} resultado(s)"
        except GraphError as exc:
            connected = False
            graph_error = exc
            message = exc.message
            if exc.permission_hint:
                message = f"{message} {exc.permission_hint}"
            if "query syntax" in (exc.message or "").lower() or exc.status_code == 400:
                message = (
                    "La búsqueda enviada a Microsoft Graph tiene sintaxis inválida. "
                    "Si escribió una ruta de carpeta, use Explorar o «Abrir como carpeta»."
                )
            self._log_graph_error("search", q, exc)

        result = list(items.values())[:limit]
        suggest_folder = bool(
            graph_error
            and (graph_error.status_code == 400 or "syntax" in (graph_error.message or "").lower())
        )
        return M365DocumentSearchResponse(
            query=q,
            items=result,
            total=len(result),
            connected=connected,
            message=message,
            mode="search",
            suggest_open_as_folder=suggest_folder,
            folder_path=q if suggest_folder else "",
        )

    async def browse_by_path(self, path: str, *, limit: int = 80) -> M365DocumentSearchResponse:
        """Navega por ruta de carpeta — no usa búsqueda semántica Graph."""
        folder_path = normalize_folder_path(path)
        if not folder_path:
            return M365DocumentSearchResponse(message="Indique una ruta de carpeta")

        try:
            sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
            folder, children = await sess.client.onedrive.list_folder_by_path(folder_path, limit=limit)
            if not folder:
                return M365DocumentSearchResponse(
                    query=folder_path,
                    connected=True,
                    mode="path",
                    folder_path=folder_path,
                    message=f"No se pudo resolver la carpeta «{folder_path}». Verifique la ruta en OneDrive.",
                )
            items = [self._from_drive_item(row, "onedrive") for row in children]
            return M365DocumentSearchResponse(
                query=folder_path,
                items=items,
                total=len(items),
                connected=True,
                mode="path",
                folder_path=folder_path,
                message=f"{len(items)} elemento(s) en /{folder_path}",
            )
        except GraphError as exc:
            self._log_graph_error("browse_by_path", folder_path, exc)
            msg = exc.permission_hint or exc.message
            if exc.status_code == 404:
                msg = f"No se pudo resolver la carpeta «{folder_path}»."
            return M365DocumentSearchResponse(
                query=folder_path,
                connected=False,
                mode="path",
                folder_path=folder_path,
                message=msg,
            )

    async def recent(self, *, limit: int = 30) -> M365DocumentSearchResponse:
        rows = (
            await self.db.execute(
                select(M365RepositoryFile)
                .where(
                    M365RepositoryFile.tenant_id == self.tenant_id,
                    M365RepositoryFile.is_folder.is_(False),
                    M365RepositoryFile.is_deleted.is_(False),
                )
                .order_by(M365RepositoryFile.modified_at_graph.desc().nullslast())
                .limit(limit)
            )
        ).scalars().all()
        items = [self._from_repository(r) for r in rows]
        return M365DocumentSearchResponse(
            items=items,
            total=len(items),
            connected=True,
            message=f"{len(items)} documentos recientes indexados",
        )

    async def browse(
        self,
        *,
        source_type: str = "onedrive",
        drive_id: str | None = None,
        site_id: str | None = None,
        folder_id: str | None = None,
        limit: int = 80,
    ) -> M365DocumentBrowseResponse:
        try:
            sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
            items: list[M365DocumentItemResponse] = []
            breadcrumb: list[dict[str, str]] = []

            if source_type == "sharepoint" and drive_id:
                rows = await sess.client.sharepoint.list_drive_items(
                    drive_id, folder_id=folder_id, limit=limit
                )
                for row in rows:
                    items.append(
                        self._from_drive_item(row, "sharepoint", drive_id=drive_id, site_id=site_id)
                    )
                breadcrumb = [{"id": folder_id or "root", "name": "Biblioteca"}]
            else:
                rows = await sess.client.onedrive.list_items(folder_id=folder_id, limit=limit)
                for row in rows:
                    items.append(self._from_drive_item(row, "onedrive"))
                breadcrumb = [{"id": folder_id or "root", "name": "OneDrive"}]

            return M365DocumentBrowseResponse(
                items=items,
                parent_id=folder_id,
                drive_id=drive_id,
                site_id=site_id,
                breadcrumb=breadcrumb,
                connected=True,
                message=f"{len(items)} elementos",
            )
        except GraphError as exc:
            return M365DocumentBrowseResponse(
                connected=False,
                message=exc.permission_hint or exc.message,
            )

    async def list_sites(self, *, limit: int = 25) -> M365DocumentBrowseResponse:
        try:
            sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
            sites = await sess.client.sharepoint.list_sites(limit=limit)
            items = [
                M365DocumentItemResponse(
                    id=site.id or "",
                    name=site.name,
                    path=site.name,
                    source_type="sharepoint",
                    source_label="SharePoint sitio",
                    web_url=site.web_url,
                    is_folder=True,
                    site_id=site.id,
                )
                for site in sites
                if site.id
            ]
            return M365DocumentBrowseResponse(items=items, connected=True, message=f"{len(items)} sitios")
        except GraphError as exc:
            return M365DocumentBrowseResponse(connected=False, message=exc.message)

    async def list_site_drives(self, site_id: str) -> M365DocumentBrowseResponse:
        try:
            sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
            drives = await sess.client.sharepoint.list_site_drives(site_id, limit=25)
            items = [
                M365DocumentItemResponse(
                    id=d.get("id") or "",
                    name=d.get("name") or "Biblioteca",
                    path=d.get("name") or "",
                    source_type="sharepoint",
                    source_label="SharePoint biblioteca",
                    web_url=d.get("web_url"),
                    is_folder=True,
                    drive_id=d.get("id"),
                    site_id=site_id,
                )
                for d in drives
                if d.get("id")
            ]
            return M365DocumentBrowseResponse(
                items=items, site_id=site_id, connected=True, message=f"{len(items)} bibliotecas"
            )
        except GraphError as exc:
            return M365DocumentBrowseResponse(connected=False, message=exc.message)

    async def link_to_company_field(
        self,
        *,
        company_id: uuid.UUID,
        field_key: str,
        item_id: str,
        drive_id: str | None = None,
        source_type: str = "onedrive",
        site_id: str | None = None,
        name: str | None = None,
        web_url: str | None = None,
        path: str | None = None,
        valid_until: date | None = None,
        representative_id: uuid.UUID | None = None,
    ) -> M365DocumentActionResponse:
        item = await self._resolve_item(item_id, drive_id=drive_id, source_type=source_type)
        if not (web_url or item.web_url) and item.id:
            try:
                sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
                refreshed = await sess.client.onedrive.get_item(item.id)
                item.web_url = item.web_url or refreshed.web_url
            except GraphError:
                pass
        resolved_url = web_url or item.web_url
        filename = name or item.name or "documento"
        fields = CompanyProfileFieldService(self.db, self.tenant_id, user_id=self.user_id)
        defn = FIELD_DEFINITIONS.get(field_key)
        if not defn:
            raise ValueError(f"Campo desconocido: {field_key}")

        profile = await fields._get_profile(company_id)
        doc_type = defn.get("document_type", field_key)
        folder_path = path or item.path or fields._onedrive_folder(profile.company_key, defn.get("onedrive", "legal"))

        asset = await fields._index_uploaded_document(
            profile=profile,
            field_key=field_key,
            doc_type=doc_type,
            filename=filename,
            content=b"",
            folder_path=folder_path.replace("/drive/root:", "").strip("/") if folder_path else "",
            web_url=resolved_url,
            graph_item_id=item.id,
            content_type=item.mime_type or "application/octet-stream",
            valid_until=valid_until,
            identity_type=defn.get("identity_type"),
        )
        meta = dict(asset.metadata_ or {})
        meta.update(
            {
                "link_mode": "link",
                "source_system": "microsoft365",
                "source_type": source_type,
                "drive_id": drive_id or meta.get("drive_id"),
                "site_id": site_id,
                "linked_at": datetime.now(UTC).isoformat(),
                "linked_by": str(self.user_id),
                "path": path or item.path,
                "field_key": field_key,
                "web_url": resolved_url,
            }
        )
        asset.metadata_ = meta
        asset.content_hash = asset.content_hash or hashlib.sha256(f"link:{item.id}".encode()).hexdigest()
        await self.db.commit()

        rep_svc = CompanyRepresentativeService(self.db, self.tenant_id, user_id=self.user_id)
        rep_label = ""
        if field_key in FIELD_TO_DOC_TYPE or representative_id:
            rep, doc_type = await rep_svc.resolve_representative_for_field(
                company_id, field_key, representative_id
            )
            rep_label = f" — {rep.full_name}"
            await rep_svc.upsert_document(
                company_id=company_id,
                representative_id=rep.id,
                document_type=doc_type,
                filename=filename,
                knowledge_asset_id=asset.id,
                m365_drive_id=drive_id,
                m365_item_id=item.id,
                m365_web_url=resolved_url,
                link_mode="link",
                expiration_date=valid_until,
            )

        try:
            from app.services.document_attachment_service import DocumentAttachmentService

            await DocumentAttachmentService(self.db, self.tenant_id, user_id=self.user_id).link_document(
                entity_type="internal_company",
                entity_id=company_id,
                company_id=company_id,
                requirement_id=field_key,
                representative_id=representative_id,
                file_name=filename,
                source_system="m365",
                source_type=source_type,
                drive_id=drive_id,
                site_id=site_id,
                item_id=item.id,
                web_url=resolved_url,
                file_path=path or item.path,
                mime_type=item.mime_type,
                size_bytes=item.size_bytes,
                raw_payload={"field_key": field_key, "knowledge_asset_id": str(asset.id)},
            )
        except Exception:
            logger.exception("document_links insert failed after m365 link")

        try:
            await fields._pending.scan_and_upsert()
        except Exception:
            logger.exception("pending scan after m365 link failed")

        return M365DocumentActionResponse(
            ok=True,
            message=f"Documento «{filename}» vinculado al requisito «{defn.get('label', field_key)}»{rep_label}.",
            field_key=field_key,
            document_id=str(asset.id),
            onedrive_url=resolved_url,
            link_mode="link",
            filename=filename,
        )

    async def import_to_company_field(
        self,
        *,
        company_id: uuid.UUID,
        field_key: str,
        item_id: str,
        drive_id: str | None = None,
        source_type: str = "onedrive",
        valid_until: date | None = None,
        representative_id: uuid.UUID | None = None,
    ) -> M365DocumentActionResponse:
        item = await self._resolve_item(item_id, drive_id=drive_id, source_type=source_type)
        if not item.id:
            raise GraphError(400, "Item Graph sin identificador")
        if not item.web_url:
            try:
                sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
                refreshed = await sess.client.onedrive.get_item(item.id)
                item.web_url = refreshed.web_url
            except GraphError:
                pass
        content = await self._download_item(item, drive_id=drive_id, source_type=source_type)
        if not content:
            raise GraphError(
                403,
                "No pude descargar el archivo desde Microsoft 365.",
                error_code="DOWNLOAD_DENIED",
                permission_hint="Falta permiso Files.Read.All o el archivo no es accesible.",
            )
        filename = item.name or "documento.pdf"
        fields = CompanyProfileFieldService(self.db, self.tenant_id, user_id=self.user_id)
        defn = FIELD_DEFINITIONS.get(field_key)
        if not defn:
            raise ValueError(f"Campo desconocido: {field_key}")
        profile = await fields._get_profile(company_id)
        doc_type = defn.get("document_type", field_key)
        folder_path = fields._onedrive_folder(profile.company_key, defn.get("onedrive", "legal"))

        storage_dir = Path(settings.documents_storage_path) / str(self.tenant_id) / profile.company_key
        storage_dir.mkdir(parents=True, exist_ok=True)
        safe_name = filename.replace("/", "_")
        (storage_dir / safe_name).write_bytes(content)

        asset = await fields._index_uploaded_document(
            profile=profile,
            field_key=field_key,
            doc_type=doc_type,
            filename=safe_name,
            content=content,
            folder_path=folder_path,
            web_url=item.web_url,
            graph_item_id=item.id,
            content_type=item.mime_type or "application/octet-stream",
            valid_until=valid_until,
            identity_type=defn.get("identity_type"),
        )
        meta = dict(asset.metadata_ or {})
        meta.update(
            {
                "link_mode": "import",
                "source_system": "microsoft365",
                "source_type": source_type,
                "original_item_id": item.id,
                "original_drive_id": drive_id,
                "original_web_url": item.web_url,
                "local_path": str(storage_dir / safe_name),
                "imported_at": datetime.now(UTC).isoformat(),
                "imported_by": str(self.user_id),
            }
        )
        asset.metadata_ = meta
        if asset.source_provider != "onedrive":
            asset.source_provider = "jaios"
        await self.db.commit()

        rep_svc = CompanyRepresentativeService(self.db, self.tenant_id, user_id=self.user_id)
        rep_label = ""
        if field_key in FIELD_TO_DOC_TYPE or representative_id:
            rep, rep_doc_type = await rep_svc.resolve_representative_for_field(
                company_id, field_key, representative_id
            )
            rep_label = f" — {rep.full_name}"
            await rep_svc.upsert_document(
                company_id=company_id,
                representative_id=rep.id,
                document_type=rep_doc_type,
                filename=safe_name,
                knowledge_asset_id=asset.id,
                m365_drive_id=drive_id,
                m365_item_id=item.id,
                m365_web_url=item.web_url,
                link_mode="import",
                expiration_date=valid_until,
            )

        try:
            await fields._pending.scan_and_upsert()
        except Exception:
            logger.exception("pending scan after m365 import failed")

        return M365DocumentActionResponse(
            ok=True,
            message=f"Documento «{safe_name}» importado y asociado al requisito{rep_label}.",
            field_key=field_key,
            document_id=str(asset.id),
            onedrive_url=item.web_url,
            link_mode="import",
            filename=safe_name,
        )

    async def link_to_repository(
        self,
        *,
        binding_id: uuid.UUID,
        item_id: str,
        drive_id: str | None = None,
        source_type: str = "onedrive",
        site_id: str | None = None,
        name: str | None = None,
        web_url: str | None = None,
        path: str | None = None,
    ):
        from app.models.integration_settings import IntegrationRepositoryBinding
        from app.schemas.m365_documents import M365RepositoryDocumentResponse
        from app.services.m365_repository_service import M365RepositoryService

        binding = (
            await self.db.execute(
                select(IntegrationRepositoryBinding).where(
                    IntegrationRepositoryBinding.id == binding_id,
                    IntegrationRepositoryBinding.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not binding:
            raise ValueError("Repositorio no encontrado")

        item = await self._resolve_item(item_id, drive_id=drive_id, source_type=source_type)
        if name:
            item.name = name
        if web_url:
            item.web_url = web_url

        repo_svc = M365RepositoryService(self.db, self.tenant_id, self.user_id)
        row = await repo_svc.upsert_m365_item(binding, item, source_type=source_type)
        return M365RepositoryDocumentResponse(
            ok=True,
            message=f"Documento «{row.name}» vinculado al repositorio «{binding.label or binding.folder_key}».",
            repository_file_id=str(row.id),
            binding_id=str(binding.id),
            link_mode="link",
            filename=row.name,
            indexed=True,
        )

    async def import_to_repository(
        self,
        *,
        binding_id: uuid.UUID,
        item_id: str,
        drive_id: str | None = None,
        source_type: str = "onedrive",
        site_id: str | None = None,
        name: str | None = None,
        web_url: str | None = None,
        path: str | None = None,
    ):
        from app.models.integration_settings import IntegrationRepositoryBinding
        from app.schemas.m365_documents import M365RepositoryDocumentResponse
        from app.services.m365_repository_service import M365RepositoryService

        binding = (
            await self.db.execute(
                select(IntegrationRepositoryBinding).where(
                    IntegrationRepositoryBinding.id == binding_id,
                    IntegrationRepositoryBinding.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not binding:
            raise ValueError("Repositorio no encontrado")

        item = await self._resolve_item(item_id, drive_id=drive_id, source_type=source_type)
        content = await self._download_item(item, drive_id=drive_id, source_type=source_type)
        if not content:
            raise GraphError(
                403,
                "No pude descargar el archivo desde Microsoft 365.",
                error_code="DOWNLOAD_DENIED",
            )
        if name:
            item.name = name
        if web_url:
            item.web_url = web_url

        repo_svc = M365RepositoryService(self.db, self.tenant_id, self.user_id)
        row = await repo_svc.upsert_m365_item(
            binding, item, source_type=source_type, download_content=content
        )
        return M365RepositoryDocumentResponse(
            ok=True,
            message=f"Documento «{row.name}» importado e indexado en «{binding.label or binding.folder_key}».",
            repository_file_id=str(row.id),
            binding_id=str(binding.id),
            link_mode="import",
            filename=row.name,
            indexed=True,
        )

    async def _resolve_item(
        self, item_id: str, *, drive_id: str | None, source_type: str
    ) -> M365DriveItem:
        sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
        if source_type == "sharepoint" and drive_id:
            graph = sess.client.graph()
            row = await graph.request("GET", f"/drives/{drive_id}/items/{item_id}")
            return M365DriveItem(
                id=row.get("id"),
                name=row.get("name") or "",
                path=(row.get("parentReference") or {}).get("path") or "",
                web_url=row.get("webUrl"),
                mime_type=(row.get("file") or {}).get("mimeType"),
                size_bytes=row.get("size"),
                is_folder=bool(row.get("folder")),
                download_url=row.get("@microsoft.graph.downloadUrl"),
            )
        return await sess.client.onedrive.get_item(item_id)

    async def _download_item(
        self, item: M365DriveItem, *, drive_id: str | None, source_type: str
    ) -> bytes:
        url = item.download_url
        if not url and item.id:
            sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
            if source_type == "sharepoint" and drive_id:
                graph = sess.client.graph()
                row = await graph.request("GET", f"/drives/{drive_id}/items/{item.id}")
                url = row.get("@microsoft.graph.downloadUrl")
            else:
                url = await sess.client.onedrive.get_download_url(item.id)
        if not url:
            return b""
        import httpx

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    @staticmethod
    def _log_graph_error(operation: str, query: str, exc: GraphError) -> None:
        logger.warning(
            "m365_graph_error operation=%s query=%s status=%s code=%s message=%s",
            operation,
            query,
            exc.status_code,
            exc.error_code,
            exc.message,
        )

    @staticmethod
    def _from_drive_item(
        row: M365DriveItem,
        source_type: str,
        *,
        drive_id: str | None = None,
        site_id: str | None = None,
    ) -> M365DocumentItemResponse:
        path = (row.path or "").replace("/drive/root:", "").replace(":", "").strip("/")
        return M365DocumentItemResponse(
            id=row.id or "",
            name=row.name or "Sin nombre",
            path=path,
            source_type=source_type,
            source_label=SOURCE_LABELS.get(source_type, source_type),
            mime_type=row.mime_type,
            size_bytes=row.size_bytes,
            web_url=row.web_url,
            download_url=row.download_url,
            drive_id=drive_id,
            item_id=row.id,
            site_id=site_id,
            is_folder=bool(row.is_folder),
            owner_name=row.owner_name,
            modified_at=row.modified_at,
        )

    def _repository_search_query(self, q: str, limit: int):
        """Búsqueda multi-término AND sobre repositorio indexado."""
        terms = [t.strip() for t in q.split() if len(t.strip()) >= 2]
        if not terms:
            terms = [q.strip()]
        stmt = select(M365RepositoryFile).where(
            M365RepositoryFile.tenant_id == self.tenant_id,
            M365RepositoryFile.is_folder.is_(False),
            M365RepositoryFile.is_deleted.is_(False),
        )
        for term in terms:
            like = f"%{term.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(M365RepositoryFile.name).like(like),
                    func.lower(M365RepositoryFile.parent_path).like(like),
                )
            )
        return stmt.limit(limit)

    @staticmethod
    def _from_repository(row: M365RepositoryFile) -> M365DocumentItemResponse:
        st = row.source or "repository"
        return M365DocumentItemResponse(
            id=row.graph_item_id,
            name=row.name,
            path=row.parent_path,
            source_type=st,
            source_label=SOURCE_LABELS.get(st, "Repositorio JAIOS"),
            mime_type=row.mime_type,
            size_bytes=row.size_bytes,
            web_url=row.web_url,
            download_url=row.download_url,
            drive_id=row.drive_id,
            item_id=row.graph_item_id,
            is_folder=row.is_folder,
            modified_at=row.modified_at_graph,
            indexed=True,
            repository_id=str(row.id),
        )
