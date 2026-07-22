"""Resolución de plantillas DGCP desde Microsoft 365 / SharePoint."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m365_account import M365UserAccount
from app.models.m365_repository import M365RepositoryFile
from app.services.document_autofill.m365_template_cache import read_cached_bytes, write_cached_bytes
from app.services.document_autofill.m365_template_catalog import (
    TemplateCatalogEntry,
    _form_type_from_name,
    classify_template,
    is_dgcp_template_candidate,
    row_to_catalog_entry,
    score_template_row,
)
from app.services.m365_documents_service import M365DocumentsService
from app.services.repository_sync_service import FOLDER_DEFAULTS
from integrations.microsoft365.errors import GraphError

logger = logging.getLogger(__name__)

FORM_TYPE_TO_DOC_TYPE: dict[str, str] = {
    "SNCC.F033": "sncc_f033",
    "SNCC.F034": "sncc_f034",
    "SNCC.F042": "sncc_f042",
    "SNCC.F047": "sncc_f047",
    "OFERTA.ECONOMICA": "oferta_economica",
    "CARTA.PRESENTACION": "carta_presentacion",
}

# Términos de búsqueda Graph por form_type conocido
FORM_TYPE_SEARCH_TERMS: dict[str, tuple[str, ...]] = {
    "SNCC.F033": ("sncc f033", "sncc f.033", "f033", "033", "oferta economica"),
    "SNCC.F034": ("sncc f034", "sncc f.034", "f034", "f.034", "034"),
    "SNCC.F042": ("sncc f042", "sncc f.042", "f042", "f.042", "informacion oferente", "042"),
    "SNCC.F047": ("sncc f047", "sncc f.047", "f047", "047", "fabricante"),
    "OFERTA.ECONOMICA": ("oferta economica", "oferta económica"),
    "CARTA.PRESENTACION": ("carta presentacion", "carta de presentacion"),
}

FILENAME_SCORE_RULES: dict[str, list[tuple[re.Pattern[str], int]]] = {
    "SNCC.F033": [(re.compile(r"sncc[_\s.-]*f[_\s.-]*0?33", re.I), 100), (re.compile(r"f[_\s.-]*0?33", re.I), 80)],
    "SNCC.F034": [(re.compile(r"sncc[_\s.-]*f[_\s.-]*0?34", re.I), 100), (re.compile(r"f[_\s.-]*0?34", re.I), 80)],
    "SNCC.F042": [
        (re.compile(r"sncc[_\s.-]*f[_\s.-]*0?42", re.I), 100),
        (re.compile(r"f[_\s.-]*0?42.*informacion.*oferente", re.I), 98),
        (re.compile(r"informacion.*oferente", re.I), 90),
        (re.compile(r"f[_\s.-]*0?42", re.I), 85),
    ],
    "SNCC.F047": [(re.compile(r"sncc[_\s.-]*f[_\s.-]*0?47", re.I), 100), (re.compile(r"fabricante", re.I), 90)],
}

EXCLUDE_NAME_RE = re.compile(
    r"(_copia|_final|autollenado|relleno|filled|preview|borrador|draft)",
    re.I,
)

DOCX_MIME_HINTS = (
    "wordprocessingml",
    "msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml",
)


@dataclass(frozen=True)
class M365TemplateReference:
    form_type: str
    m365_file_id: uuid.UUID | None
    graph_item_id: str
    drive_id: str | None
    source: str
    name: str
    web_url: str | None
    parent_path: str
    content_hash: str | None
    template_version: str
    document_type: str
    resolver: str = "m365_index"

    def audit_dict(self) -> dict:
        return {
            "m365_file_id": str(self.m365_file_id) if self.m365_file_id else None,
            "graph_item_id": self.graph_item_id,
            "drive_id": self.drive_id,
            "source": self.source,
            "name": self.name,
            "web_url": self.web_url,
            "parent_path": self.parent_path,
            "content_hash": self.content_hash,
            "template_version": self.template_version,
            "document_type": self.document_type,
            "resolver": self.resolver,
        }


class M365TemplateResolver:
    """Localiza plantillas corporativas indexadas o en Graph y descarga bytes sin modificar origen."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def list_all_templates(self) -> list[TemplateCatalogEntry]:
        rows = (
            await self.db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.tenant_id == self.tenant_id,
                    M365RepositoryFile.is_deleted.is_(False),
                    M365RepositoryFile.is_folder.is_(False),
                )
            )
        ).scalars().all()
        return sorted(
            [row_to_catalog_entry(r) for r in rows if is_dgcp_template_candidate(r)],
            key=lambda e: (-e.score, e.name.lower()),
        )

    async def resolve_by_file_id(self, m365_file_id: uuid.UUID) -> M365TemplateReference | None:
        row = (
            await self.db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.id == m365_file_id,
                    M365RepositoryFile.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not row or not is_dgcp_template_candidate(row):
            return None
        entry = row_to_catalog_entry(row)
        return self._entry_to_ref(entry)

    async def resolve(self, form_type: str) -> M365TemplateReference | None:
        form_key = form_type.upper().replace(" ", ".")

        # Catálogo indexado (mismo form_type que la UI / batch) tiene prioridad sobre heurísticas.
        for entry in await self.list_all_templates():
            if entry.form_type == form_key:
                return self._entry_to_ref(entry)

        ref = await self._resolve_from_index(form_key)
        if ref:
            return ref

        if self.user_id:
            return await self._resolve_from_graph(form_key)
        return None

    @staticmethod
    def _entry_to_ref(entry: TemplateCatalogEntry) -> M365TemplateReference:
        return M365TemplateReference(
            form_type=entry.form_type,
            m365_file_id=entry.m365_file_id,
            graph_item_id=entry.graph_item_id,
            drive_id=entry.drive_id,
            source=entry.source,
            name=entry.name,
            web_url=entry.web_url,
            parent_path=entry.parent_path,
            content_hash=entry.content_hash,
            template_version=entry.content_hash or "index",
            document_type=entry.document_type,
            resolver="m365_index",
        )

    async def download_bytes(self, ref: M365TemplateReference) -> bytes:
        if ref.m365_file_id:
            cached = read_cached_bytes(ref.m365_file_id)
            if cached:
                return cached

        row: M365RepositoryFile | None = None
        if ref.m365_file_id:
            row = (
                await self.db.execute(
                    select(M365RepositoryFile).where(
                        M365RepositoryFile.id == ref.m365_file_id,
                        M365RepositoryFile.tenant_id == self.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if row and row.download_url:
                content = await self._http_download(row.download_url)
                if content:
                    write_cached_bytes(row.id, content)
                    return content

        actor_id = await self._resolve_graph_actor_id(row.account_id if row else None)
        if actor_id:
            try:
                docs = M365DocumentsService(self.db, self.tenant_id, actor_id)
                item = await docs._resolve_item(
                    ref.graph_item_id,
                    drive_id=ref.drive_id,
                    source_type=ref.source,
                )
                content = await docs._download_item(item, drive_id=ref.drive_id, source_type=ref.source)
                if content:
                    if ref.m365_file_id:
                        write_cached_bytes(ref.m365_file_id, content)
                    return content
            except Exception as exc:
                logger.warning("m365_template_graph_download_failed name=%s err=%s", ref.name, exc)

        content = await self._try_dgcp_official(ref)
        if content:
            return content

        raise FileNotFoundError(
            f"No se pudo descargar plantilla M365: {ref.name}. "
            "Reconecte la cuenta M365 o sincronice el repositorio de plantillas."
        )

    async def _try_dgcp_official(self, ref: M365TemplateReference) -> bytes | None:
        from app.services.document_autofill.official_template_downloader import download_dgcp_official_docx

        content = await download_dgcp_official_docx(ref.name)
        if content and ref.m365_file_id:
            write_cached_bytes(ref.m365_file_id, content)
        return content

    async def _resolve_graph_actor_id(self, account_id: uuid.UUID | None) -> uuid.UUID | None:
        if self.user_id:
            return self.user_id
        if account_id:
            acc = await self.db.get(M365UserAccount, account_id)
            if acc and acc.jaios_user_id and acc.connection_mode == "oauth":
                if acc.connection_status == "connected":
                    return acc.jaios_user_id
        result = await self.db.execute(
            select(M365UserAccount).where(
                M365UserAccount.tenant_id == self.tenant_id,
                M365UserAccount.is_active.is_(True),
                M365UserAccount.connection_mode == "oauth",
                M365UserAccount.connection_status == "connected",
            ).limit(1)
        )
        acc = result.scalar_one_or_none()
        return acc.jaios_user_id if acc else None

    async def resolve_and_download(self, form_type: str) -> tuple[bytes, M365TemplateReference]:
        ref = await self.resolve(form_type)
        if not ref:
            raise FileNotFoundError(f"Plantilla M365 no encontrada para {form_type}")
        content = await self.download_bytes(ref)
        content_hash = hashlib.sha256(content).hexdigest()[:16]
        updated = M365TemplateReference(
            form_type=ref.form_type,
            m365_file_id=ref.m365_file_id,
            graph_item_id=ref.graph_item_id,
            drive_id=ref.drive_id,
            source=ref.source,
            name=ref.name,
            web_url=ref.web_url,
            parent_path=ref.parent_path,
            content_hash=content_hash,
            template_version=ref.template_version or content_hash,
            document_type=ref.document_type,
            resolver=ref.resolver,
        )
        return content, updated

    async def _resolve_from_index(self, form_key: str) -> M365TemplateReference | None:
        doc_type = FORM_TYPE_TO_DOC_TYPE.get(form_key, "")
        patterns = FORM_TYPE_SEARCH_TERMS.get(form_key, ())
        name_filters = [M365RepositoryFile.name.ilike(f"%{p}%") for p in patterns[:4]]
        path_filters = [
            M365RepositoryFile.parent_path.ilike("%PLANTILLAS%"),
            M365RepositoryFile.parent_path.ilike("%DGCP%"),
        ]

        stmt = (
            select(M365RepositoryFile)
            .where(
                M365RepositoryFile.tenant_id == self.tenant_id,
                M365RepositoryFile.is_deleted.is_(False),
                M365RepositoryFile.is_folder.is_(False),
                or_(
                    M365RepositoryFile.document_type == doc_type,
                    M365RepositoryFile.document_category.in_(("plantilla", "formulario")),
                    *name_filters,
                    *path_filters,
                ),
            )
            .limit(200)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        candidates = [r for r in rows if self._is_docx_candidate(r) and not self._is_excluded(r.name)]

        # También buscar por form_type generado desde nombre
        if not candidates:
            all_tpl = await self.list_all_templates()
            for entry in all_tpl:
                if entry.form_type == form_key:
                    row = next((r for r in rows if r.id == entry.m365_file_id), None)
                    if row:
                        candidates.append(row)
            if not candidates:
                for entry in all_tpl:
                    if entry.form_type == form_key:
                        return self._entry_to_ref(entry)

        if not candidates:
            return None

        best = max(candidates, key=lambda r: self._score_row(form_key, r))
        if self._score_row(form_key, best) < 30 and form_key not in FILENAME_SCORE_RULES:
            # Para form_types genéricos, aceptar si hay match exacto de form_type en catálogo
            entry_match = next((e for e in await self.list_all_templates() if e.form_type == form_key), None)
            if entry_match:
                return self._entry_to_ref(entry_match)
            if self._score_row(form_key, best) < 30:
                return None
        elif self._score_row(form_key, best) < 50 and form_key in FILENAME_SCORE_RULES:
            return None
        return self._row_to_ref(form_key, best)

    async def _resolve_from_graph(self, form_key: str) -> M365TemplateReference | None:
        assert self.user_id
        docs = M365DocumentsService(self.db, self.tenant_id, self.user_id)
        search_terms = FORM_TYPE_SEARCH_TERMS.get(form_key, (form_key,))

        for term in search_terms:
            try:
                result = await docs.search(term, limit=30)
            except GraphError as exc:
                logger.warning("m365_template_graph_search_failed term=%s err=%s", term, exc.message)
                continue
            for item in result.items:
                if item.is_folder:
                    continue
                name = item.name or ""
                if self._is_excluded(name):
                    continue
                if not self._name_matches(form_key, name):
                    continue
                mime = (item.mime_type or "").lower()
                if mime and not any(h in mime for h in DOCX_MIME_HINTS) and not name.lower().endswith(".docx"):
                    continue
                path = item.path or ""
                if "plantilla" not in f"{path} {name}".lower() and "sncc" not in name.lower():
                    continue
                return M365TemplateReference(
                    form_type=form_key,
                    m365_file_id=None,
                    graph_item_id=item.item_id or item.id,
                    drive_id=item.drive_id,
                    source=item.source_type or "onedrive",
                    name=name,
                    web_url=item.web_url,
                    parent_path=path,
                    content_hash=None,
                    template_version=item.modified_at.isoformat() if item.modified_at else "graph",
                    document_type=FORM_TYPE_TO_DOC_TYPE.get(form_key, "general"),
                    resolver="m365_graph_search",
                )

        dgcp_paths = [
            p for key, _, _, p in FOLDER_DEFAULTS if key in ("02_PLANTILLAS_DGCP", "02_PLANTILLAS")
        ]
        for folder_path in dgcp_paths:
            try:
                browse = await docs.browse_by_path(folder_path, limit=80)
            except GraphError:
                continue
            for item in browse.items:
                if item.is_folder:
                    continue
                name = item.name or ""
                if self._is_excluded(name) or not self._name_matches(form_key, name):
                    continue
                return M365TemplateReference(
                    form_type=form_key,
                    m365_file_id=None,
                    graph_item_id=item.item_id or item.id,
                    drive_id=item.drive_id,
                    source=item.source_type or "onedrive",
                    name=name,
                    web_url=item.web_url,
                    parent_path=item.path or folder_path,
                    content_hash=None,
                    template_version=item.modified_at.isoformat() if item.modified_at else "graph",
                    document_type=FORM_TYPE_TO_DOC_TYPE.get(form_key, "general"),
                    resolver="m365_graph_browse",
                )
        return None

    def _row_to_ref(self, form_key: str, row: M365RepositoryFile) -> M365TemplateReference:
        version = row.content_hash or (
            row.modified_at_graph.isoformat() if row.modified_at_graph else str(row.synced_at)
        )
        return M365TemplateReference(
            form_type=form_key,
            m365_file_id=row.id,
            graph_item_id=row.graph_item_id,
            drive_id=row.drive_id,
            source=row.source,
            name=row.name,
            web_url=row.web_url,
            parent_path=row.parent_path,
            content_hash=row.content_hash,
            template_version=version,
            document_type=row.document_type,
            resolver="m365_index",
        )

    def _score_row(self, form_key: str, row: M365RepositoryFile) -> int:
        blob = f"{row.parent_path}/{row.name}".lower()
        score = 0
        if row.document_type == FORM_TYPE_TO_DOC_TYPE.get(form_key):
            score += 40
        if row.document_category in ("plantilla", "formulario"):
            score += 15
        if "plantilla" in blob or "02_plantillas" in blob.replace("-", "_"):
            score += 20
        if "dgcp" in blob:
            score += 10
        for pattern, pts in FILENAME_SCORE_RULES.get(form_key, []):
            if pattern.search(row.name):
                score += pts
        if row.name.lower().endswith(".docx"):
            score += 5
        return score

    @staticmethod
    def _is_docx_candidate(row: M365RepositoryFile) -> bool:
        name = row.name.lower()
        mime = (row.mime_type or "").lower()
        if name.endswith(".docx"):
            return True
        return any(h in mime for h in DOCX_MIME_HINTS)

    @staticmethod
    def _is_excluded(name: str) -> bool:
        return bool(EXCLUDE_NAME_RE.search(name))

    @staticmethod
    def _name_matches(form_key: str, name: str) -> bool:
        if _form_type_from_name(name) == form_key:
            return True
        for pattern, _ in FILENAME_SCORE_RULES.get(form_key, []):
            if pattern.search(name):
                return True
        # Match parcial: clave sin prefijo PLANTILLA.
        slug = form_key.replace(".", " ").replace("_", " ").lower()
        return slug[:12] in name.lower()

    @staticmethod
    async def _http_download(url: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
        except httpx.HTTPError:
            return b""
