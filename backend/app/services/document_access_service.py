"""Resolución unificada de acceso a documentos — local, M365, links, dedup."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document
from app.models.document_link import DocumentLink
from app.models.dgcp_process_document import DGCPProcessDocument
from app.models.knowledge import KnowledgeAsset
from app.models.m365_repository import M365RepositoryFile
from app.services.knowledge_source_provider import get_knowledge_source_provider

REMOTE_PATH_PREFIXES = ("onedrive/", "sharepoint/", "m365/")


@dataclass
class DocumentAccess:
    source_type: str
    source_id: str
    view_mode: str
    filename: str | None = None
    web_url: str | None = None
    local_api_path: str | None = None
    canonical_source_id: str | None = None
    relative_path: str | None = None
    available: bool = True
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "view_mode": self.view_mode,
            "filename": self.filename,
            "web_url": self.web_url,
            "local_api_path": self.local_api_path,
            "canonical_source_id": self.canonical_source_id,
            "relative_path": self.relative_path,
            "available": self.available,
            "reason": self.reason,
        }


def is_remote_knowledge_path(relative_path: str | None) -> bool:
    if not relative_path:
        return False
    norm = relative_path.lower().replace("\\", "/")
    return any(norm.startswith(p) for p in REMOTE_PATH_PREFIXES)


def asset_web_url_from_metadata(asset: KnowledgeAsset | Any) -> str | None:
    meta = getattr(asset, "metadata_", None) or getattr(asset, "metadata", None) or {}
    if isinstance(meta, dict):
        for key in ("web_url", "original_web_url", "m365_web_url"):
            url = meta.get(key)
            if url and str(url).startswith("http"):
                return str(url)
    return None


def can_read_local_path(relative_path: str | None) -> bool:
    if not relative_path or is_remote_knowledge_path(relative_path):
        return False
    source = get_knowledge_source_provider()
    if not source.is_available():
        return False
    try:
        source.read_bytes(relative_path)
        return True
    except Exception:
        return False


def can_read_storage_path(storage_path: str | None) -> bool:
    if not storage_path:
        return False
    return Path(storage_path).is_file()


async def resolve_canonical_knowledge_asset(
    db: AsyncSession,
    asset_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
) -> tuple[KnowledgeAsset | None, uuid.UUID | None]:
    """Sigue dedup_merged_into hasta el asset activo canónico."""
    seen: set[uuid.UUID] = set()
    current_id: uuid.UUID | None = asset_id
    original_id = asset_id

    while current_id and current_id not in seen:
        seen.add(current_id)
        asset = await db.get(KnowledgeAsset, current_id)
        if not asset or asset.tenant_id != tenant_id:
            return None, None
        if asset.is_active:
            canonical_id = None if asset.id == original_id else asset.id
            return asset, canonical_id
        merged = (asset.metadata_ or {}).get("dedup_merged_into")
        if merged:
            current_id = uuid.UUID(str(merged))
            continue
        graph_item_id = (asset.metadata_ or {}).get("graph_item_id")
        if graph_item_id:
            sibling = (
                await db.execute(
                    select(KnowledgeAsset).where(
                        KnowledgeAsset.tenant_id == tenant_id,
                        KnowledgeAsset.is_active.is_(True),
                        KnowledgeAsset.metadata_["graph_item_id"].as_string() == graph_item_id,
                    )
                )
            ).scalar_one_or_none()
            if sibling:
                canonical_id = None if sibling.id == original_id else sibling.id
                return sibling, canonical_id
        return None, None
    return None, None


async def resolve_knowledge_asset_web_url(
    db: AsyncSession,
    asset: KnowledgeAsset,
    *,
    tenant_id: uuid.UUID | None = None,
) -> str | None:
    url = asset_web_url_from_metadata(asset)
    if url:
        return url

    meta = asset.metadata_ or {}
    graph_item_id = meta.get("graph_item_id") or meta.get("item_id")
    if not graph_item_id:
        return None

    tid = tenant_id or asset.tenant_id
    row = (
        await db.execute(
            select(M365RepositoryFile).where(
                M365RepositoryFile.tenant_id == tid,
                M365RepositoryFile.graph_item_id == graph_item_id,
                M365RepositoryFile.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if row and row.web_url:
        return row.web_url
    if row and row.download_url and str(row.download_url).startswith("http"):
        return row.download_url
    return None


async def resolve_knowledge_asset_access(
    db: AsyncSession,
    asset_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
) -> DocumentAccess | None:
    asset, canonical_id = await resolve_canonical_knowledge_asset(db, asset_id, tenant_id=tenant_id)
    if not asset:
        return DocumentAccess(
            source_type="knowledge_asset",
            source_id=str(asset_id),
            view_mode="external",
            available=False,
            reason="asset_not_found",
        )

    local_ok = can_read_local_path(asset.relative_path)
    web_url = await resolve_knowledge_asset_web_url(db, asset, tenant_id=tenant_id)
    local_api = f"/api/v1/knowledge/assets/{asset.id}/file"

    if not web_url:
        meta = asset.metadata_ or {}
        graph_item_id = meta.get("graph_item_id") or meta.get("item_id")
        if graph_item_id:
            row = (
                await db.execute(
                    select(M365RepositoryFile).where(
                        M365RepositoryFile.tenant_id == tenant_id,
                        M365RepositoryFile.graph_item_id == str(graph_item_id),
                        M365RepositoryFile.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if row:
                web_url = row.web_url or (
                    row.download_url if row.download_url and str(row.download_url).startswith("http") else None
                )
        if not web_url and asset.filename:
            row = (
                await db.execute(
                    select(M365RepositoryFile).where(
                        M365RepositoryFile.tenant_id == tenant_id,
                        M365RepositoryFile.is_deleted.is_(False),
                        M365RepositoryFile.name.ilike(asset.filename),
                    ).limit(1)
                )
            ).scalar_one_or_none()
            if row:
                web_url = row.web_url or (
                    row.download_url if row.download_url and str(row.download_url).startswith("http") else None
                )

    if local_ok:
        return DocumentAccess(
            source_type="knowledge_asset",
            source_id=str(asset_id),
            view_mode="local",
            filename=asset.filename,
            web_url=web_url,
            local_api_path=local_api,
            canonical_source_id=str(canonical_id) if canonical_id else None,
            relative_path=asset.relative_path,
        )

    if web_url:
        return DocumentAccess(
            source_type="knowledge_asset",
            source_id=str(asset_id),
            view_mode="external",
            filename=asset.filename,
            web_url=web_url,
            canonical_source_id=str(canonical_id) if canonical_id else None,
            relative_path=asset.relative_path,
        )

    return DocumentAccess(
        source_type="knowledge_asset",
        source_id=str(asset_id),
        view_mode="external",
        filename=asset.filename,
        canonical_source_id=str(canonical_id) if canonical_id else None,
        relative_path=asset.relative_path,
        available=False,
        reason="no_local_or_web_url",
    )


async def resolve_document_access(
    db: AsyncSession,
    document_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
) -> DocumentAccess | None:
    doc = await db.get(Document, document_id)
    if not doc or doc.tenant_id != tenant_id or not doc.is_active:
        return DocumentAccess(
            source_type="document",
            source_id=str(document_id),
            view_mode="local",
            available=False,
            reason="document_not_found",
        )

    if can_read_storage_path(doc.storage_path):
        return DocumentAccess(
            source_type="document",
            source_id=str(document_id),
            view_mode="local",
            filename=doc.filename,
            local_api_path=f"/api/v1/documents/{doc.id}/download",
            relative_path=doc.storage_path,
        )

    meta = doc.metadata_ or {} if hasattr(doc, "metadata_") else {}
    web_url = meta.get("web_url") if isinstance(meta, dict) else None
    if web_url:
        return DocumentAccess(
            source_type="document",
            source_id=str(document_id),
            view_mode="external",
            filename=doc.filename,
            web_url=web_url,
        )

    return DocumentAccess(
        source_type="document",
        source_id=str(document_id),
        view_mode="local",
        filename=doc.filename,
        available=False,
        reason="storage_missing",
    )


async def resolve_document_link_access(
    db: AsyncSession,
    link_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
) -> DocumentAccess | None:
    link = await db.get(DocumentLink, link_id)
    if not link or link.tenant_id != tenant_id:
        return DocumentAccess(
            source_type="document_link",
            source_id=str(link_id),
            view_mode="external",
            available=False,
            reason="link_not_found",
        )

    if link.imported_storage_path and can_read_storage_path(link.imported_storage_path):
        return DocumentAccess(
            source_type="document_link",
            source_id=str(link_id),
            view_mode="local",
            filename=link.file_name,
            local_api_path=f"/api/v1/documents/access/open?document_link_id={link_id}",
            relative_path=link.imported_storage_path,
        )

    if link.web_url and str(link.web_url).startswith("http"):
        return DocumentAccess(
            source_type="document_link",
            source_id=str(link_id),
            view_mode="external",
            filename=link.file_name,
            web_url=link.web_url,
            relative_path=link.file_path,
        )

    if link.item_id:
        row = (
            await db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.tenant_id == tenant_id,
                    M365RepositoryFile.graph_item_id == link.item_id,
                    M365RepositoryFile.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if row and row.web_url:
            return DocumentAccess(
                source_type="document_link",
                source_id=str(link_id),
                view_mode="external",
                filename=link.file_name,
                web_url=row.web_url,
                relative_path=link.file_path,
            )

    return DocumentAccess(
        source_type="document_link",
        source_id=str(link_id),
        view_mode="external",
        filename=link.file_name,
        available=False,
        reason="no_access_path",
    )


async def resolve_m365_file_access(
    db: AsyncSession,
    file_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
) -> DocumentAccess | None:
    row = await db.get(M365RepositoryFile, file_id)
    if not row or row.tenant_id != tenant_id or row.is_deleted:
        return DocumentAccess(
            source_type="m365_file",
            source_id=str(file_id),
            view_mode="external",
            available=False,
            reason="m365_file_not_found",
        )

    web_url = row.web_url or (
        row.download_url if row.download_url and str(row.download_url).startswith("http") else None
    )
    if web_url:
        return DocumentAccess(
            source_type="m365_file",
            source_id=str(file_id),
            view_mode="external",
            filename=row.name,
            web_url=web_url,
            relative_path=row.parent_path,
        )

    return DocumentAccess(
        source_type="m365_file",
        source_id=str(file_id),
        view_mode="external",
        filename=row.name,
        available=False,
        reason="no_web_url",
    )


async def resolve_process_document_access(
    db: AsyncSession,
    process_document_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID | None = None,
) -> DocumentAccess | None:
    proc = await db.get(DGCPProcessDocument, process_document_id)
    if not proc or proc.tenant_id != tenant_id:
        return DocumentAccess(
            source_type="process_document",
            source_id=str(process_document_id),
            view_mode="local",
            available=False,
            reason="process_document_not_found",
        )
    opp_id = opportunity_id or proc.opportunity_id
    local_api = f"/api/v1/dgcp/opportunities/{opp_id}/process-documents/{proc.id}/file"
    meta = proc.metadata_ or {}
    storage = meta.get("storage_uri")
    if storage and can_read_storage_path(storage):
        return DocumentAccess(
            source_type="process_document",
            source_id=str(process_document_id),
            view_mode="local",
            filename=proc.title,
            local_api_path=local_api,
            relative_path=storage,
        )
    web_url = meta.get("web_url")
    if web_url:
        return DocumentAccess(
            source_type="process_document",
            source_id=str(process_document_id),
            view_mode="external",
            filename=proc.title,
            web_url=web_url,
        )
    return DocumentAccess(
        source_type="process_document",
        source_id=str(process_document_id),
        view_mode="local",
        filename=proc.title,
        local_api_path=local_api,
        available=False,
        reason="storage_missing",
    )


async def resolve_by_graph_item_id(
    db: AsyncSession,
    graph_item_id: str,
    *,
    tenant_id: uuid.UUID,
) -> DocumentAccess | None:
    asset = (
        await db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.tenant_id == tenant_id,
                KnowledgeAsset.is_active.is_(True),
                KnowledgeAsset.metadata_["graph_item_id"].as_string() == graph_item_id,
            )
        )
    ).scalar_one_or_none()
    if asset:
        return await resolve_knowledge_asset_access(db, asset.id, tenant_id=tenant_id)

    inactive = (
        await db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.tenant_id == tenant_id,
                KnowledgeAsset.is_active.is_(False),
                KnowledgeAsset.metadata_["graph_item_id"].as_string() == graph_item_id,
            )
        )
    ).scalar_one_or_none()
    if inactive:
        return await resolve_knowledge_asset_access(db, inactive.id, tenant_id=tenant_id)

    row = (
        await db.execute(
            select(M365RepositoryFile).where(
                M365RepositoryFile.tenant_id == tenant_id,
                M365RepositoryFile.graph_item_id == graph_item_id,
                M365RepositoryFile.is_deleted.is_(False),
                M365RepositoryFile.is_folder.is_(False),
            )
        )
    ).scalar_one_or_none()
    if row:
        return await resolve_m365_file_access(db, row.id, tenant_id=tenant_id)

    return None


REASON_MESSAGES = {
    "asset_not_found": "El documento ya no está disponible o fue consolidado sin ruta válida.",
    "document_not_found": "Documento no encontrado en JAIOS.",
    "link_not_found": "Vínculo documental no encontrado.",
    "m365_file_not_found": "Archivo no encontrado en el índice M365.",
    "no_local_or_web_url": "No hay copia local ni enlace OneDrive para este documento.",
    "storage_missing": "El archivo no está en almacenamiento local.",
    "no_access_path": "No se encontró ruta de acceso para el documento vinculado.",
    "no_web_url": "El archivo M365 no tiene URL de acceso.",
    "no_source_specified": "Indique qué documento desea abrir.",
    "not_found": "Documento no encontrado.",
    "process_document_not_found": "Documento de proceso no encontrado.",
}


def human_access_error(reason: str | None) -> str:
    if not reason:
        return "No se pudo abrir el documento."
    return REASON_MESSAGES.get(reason, f"No se pudo abrir el documento ({reason}).")


async def resolve_any_document_access(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    knowledge_asset_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    document_link_id: uuid.UUID | None = None,
    m365_file_id: uuid.UUID | None = None,
    process_document_id: uuid.UUID | None = None,
    opportunity_id: uuid.UUID | None = None,
    graph_item_id: str | None = None,
) -> DocumentAccess:
    if graph_item_id and not any(
        (knowledge_asset_id, document_id, document_link_id, m365_file_id, process_document_id)
    ):
        result = await resolve_by_graph_item_id(db, graph_item_id, tenant_id=tenant_id)
        if result:
            return result
        return DocumentAccess(
            source_type="graph_item",
            source_id=graph_item_id,
            view_mode="external",
            available=False,
            reason="m365_file_not_found",
        )
    if knowledge_asset_id:
        result = await resolve_knowledge_asset_access(db, knowledge_asset_id, tenant_id=tenant_id)
        return result or DocumentAccess(
            source_type="knowledge_asset",
            source_id=str(knowledge_asset_id),
            view_mode="external",
            available=False,
            reason="not_found",
        )
    if document_id:
        result = await resolve_document_access(db, document_id, tenant_id=tenant_id)
        return result or DocumentAccess(
            source_type="document",
            source_id=str(document_id),
            view_mode="local",
            available=False,
            reason="not_found",
        )
    if document_link_id:
        result = await resolve_document_link_access(db, document_link_id, tenant_id=tenant_id)
        return result or DocumentAccess(
            source_type="document_link",
            source_id=str(document_link_id),
            view_mode="external",
            available=False,
            reason="not_found",
        )
    if m365_file_id:
        result = await resolve_m365_file_access(db, m365_file_id, tenant_id=tenant_id)
        return result or DocumentAccess(
            source_type="m365_file",
            source_id=str(m365_file_id),
            view_mode="external",
            available=False,
            reason="not_found",
        )
    if process_document_id:
        result = await resolve_process_document_access(
            db, process_document_id, tenant_id=tenant_id, opportunity_id=opportunity_id
        )
        return result or DocumentAccess(
            source_type="process_document",
            source_id=str(process_document_id),
            view_mode="local",
            available=False,
            reason="not_found",
        )
    return DocumentAccess(
        source_type="unknown",
        source_id="",
        view_mode="external",
        available=False,
        reason="no_source_specified",
    )
