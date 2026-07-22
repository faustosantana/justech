"""Descubrimiento y descarga de documentos publicados en el portal DGCP."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.dgcp_process_document_classifier import classify_process_document

logger = logging.getLogger(__name__)

_PORTAL_BASE = "https://comunidad.comprasdominicana.gob.do"
_RETRIEVE_PATH = (
    "/Public/Archive/RetrieveFile/Index"
    "?DocumentId={document_id}&InCommunity=False&InPaymentGateway=False&DocUniqueIdentifier="
)
_FILE_ID_RE = re.compile(r"documentFileId=' \+ '(\d+)' \+ '&mkey=")
_PDF_TITLE_RE = re.compile(r">([^<]{5,200}\.[a-zA-Z0-9]{2,5})<", re.I)
_GRID_ROW_RE = re.compile(
    r'spnDocumentName_\d+"\s+class="VortalSpan">([^<]+)</span>.*?'
    r'spnDocumentTypeSpan_\d+"\s+class="VortalSpan">([^<]*)</span>.*?'
    r"documentFileId=' \+ '(\d+)'",
    re.I | re.S,
)
_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class PortalDocumentRef:
    portal_document_id: str
    title: str
    filename: str
    format: str
    doc_role: str
    priority: str
    retrieve_url: str
    section: str = "general"


class DGCPPortalDocumentService:
    """Parsea la ficha pública del proceso y descarga archivos del comprador."""

    def __init__(self, *, timeout_seconds: float = 45.0) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def notice_uid_from_url(source_url: str | None) -> str | None:
        if not source_url:
            return None
        parsed = urlparse(source_url)
        for part in (parsed.query or "").split("&"):
            if part.lower().startswith("noticeuid="):
                return part.split("=", 1)[1] or None
        return None

    @staticmethod
    def normalize_portal_url(source_url: str | None) -> str | None:
        if not source_url:
            return None
        uid = DGCPPortalDocumentService.notice_uid_from_url(source_url)
        if uid:
            return f"{_PORTAL_BASE}/Public/Tendering/OpportunityDetail/Index?noticeUID={uid}"
        if "comprasdominicana.gob.do" in source_url:
            return source_url.split("#")[0]
        return None

    def discover_from_html(self, html: str, *, process_code: str) -> list[PortalDocumentRef]:
        refs: list[PortalDocumentRef] = []
        seen_ids: set[str] = set()

        for match in _GRID_ROW_RE.finditer(html):
            filename = match.group(1).strip()
            portal_type = match.group(2).strip()
            doc_id = match.group(3)
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            refs.append(self._build_ref(doc_id, filename, process_code, portal_type=portal_type))

        for match in _FILE_ID_RE.finditer(html):
            doc_id = match.group(1)
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            filename = self._filename_near_file_id(html, match)
            refs.append(self._build_ref(doc_id, filename, process_code))

        return self._filter_refs_for_process(refs, process_code)

    @staticmethod
    def _filename_near_file_id(html: str, match: re.Match[str]) -> str:
        doc_id = match.group(1)
        after = html[match.end() : match.end() + 400]
        before = html[max(0, match.start() - 900) : match.start()]
        after_titles = [t.strip() for t in _PDF_TITLE_RE.findall(after) if t.strip()]
        if after_titles:
            return after_titles[0]
        before_titles = [t.strip() for t in _PDF_TITLE_RE.findall(before) if t.strip()]
        if before_titles:
            return before_titles[-1]
        return f"Documento {doc_id}.pdf"

    def _build_ref(
        self,
        doc_id: str,
        filename: str,
        process_code: str,
        *,
        portal_type: str = "",
    ) -> PortalDocumentRef:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
        role, priority = classify_process_document(filename)
        role = self._refine_role(filename, role, portal_type=portal_type)
        section = self._section_for_role(role)
        return PortalDocumentRef(
            portal_document_id=doc_id,
            title=self._clean_title(filename, process_code),
            filename=filename,
            format=ext,
            doc_role=role,
            priority=priority,
            retrieve_url=f"{_PORTAL_BASE}{_RETRIEVE_PATH.format(document_id=doc_id)}",
            section=section,
        )

    @staticmethod
    def _filter_refs_for_process(refs: list[PortalDocumentRef], process_code: str) -> list[PortalDocumentRef]:
        if not refs:
            return refs
        tokens = DGCPPortalDocumentService._process_match_tokens(process_code)
        if not tokens:
            return refs
        matching = [r for r in refs if DGCPPortalDocumentService._matches_process(r.filename, tokens)]
        if not matching:
            # Títulos sin código del proceso (p. ej. RESIDE) — conservar todo el lote de la ficha.
            return refs
        if len(matching) == len(refs):
            return refs
        # Mezcla: priorizar los que citan el código, pero no omitir el resto del mismo detalle.
        matching_ids = {r.portal_document_id for r in matching}
        extras = [r for r in refs if r.portal_document_id not in matching_ids]
        return matching + extras

    async def discover_from_portal(self, source_url: str | None, *, process_code: str) -> list[PortalDocumentRef]:
        page_url = self.normalize_portal_url(source_url)
        if not page_url:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(
                    page_url,
                    headers={"User-Agent": "JAIOS-DGCP/1.0", "Accept": "text/html"},
                )
                response.raise_for_status()
                html = response.text
        except Exception as exc:
            logger.warning("DGCP portal fetch failed for %s: %s", process_code, exc)
            return []
        return self.discover_from_html(html, process_code=process_code)

    async def download(self, ref: PortalDocumentRef) -> tuple[bytes, str] | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(
                    ref.retrieve_url,
                    headers={"User-Agent": "JAIOS-DGCP/1.0", "Accept": "application/pdf,*/*"},
                )
                response.raise_for_status()
                content = response.content
        except Exception as exc:
            logger.warning("DGCP download failed id=%s: %s", ref.portal_document_id, exc)
            return None
        if not content or len(content) > _MAX_DOWNLOAD_BYTES:
            return None
        if content[:4] != b"%PDF":
            return None
        return content, "application/pdf"

    @staticmethod
    def _process_match_tokens(process_code: str) -> list[str]:
        generic = {"DAF", "CD", "CCC", "PEEX", "CM", "SNCC", "DGCP"}
        tokens: list[str] = []
        for part in re.split(r"[-_\s]+", process_code.upper()):
            if len(part) >= 4 and part not in generic:
                tokens.append(part)
            elif part.isdigit() and len(part) >= 4:
                tokens.append(part)
        return tokens

    @staticmethod
    def _matches_process(filename: str, tokens: list[str]) -> bool:
        blob = filename.upper()
        return any(token in blob for token in tokens)

    @staticmethod
    def _clean_title(filename: str, process_code: str) -> str:
        name = filename.rsplit(".", 1)[0].strip()
        code = process_code.strip()
        if code and name.lower().startswith(code.lower()):
            name = name[len(code) :].lstrip(" .-_")
        return name or filename

    @staticmethod
    def _refine_role(filename: str, role: str, *, portal_type: str = "") -> str:
        blob = f"{filename} {portal_type}".lower()
        if "anexo" in blob:
            return "anexo"
        if "adenda" in blob:
            return "adenda"
        if "enmienda" in blob or "modificacion" in blob or "modificación" in blob:
            return "enmienda"
        if "circular" in blob:
            return "circular"
        if role == "anexo_tecnico":
            return "anexo"
        if "ficha tecnica" in blob or "ficha técnica" in blob:
            return "tdr"
        if role in ("ficha_tecnica", "especificaciones") and "pliego" not in blob:
            if "tdr" in blob or "terminos" in blob or "términos" in blob:
                return "tdr"
            return "tdr" if "especificacion" in blob else role
        if (
            "pliego" in blob
            or "bases de condiciones" in blob
            or "bases de la contratacion" in blob
            or "acta de aprobacion" in blob
            or "acta de aprobación" in blob
        ):
            return "pliego"
        if (
            "formulario" in blob
            or "estudios previos" in blob
            or "solicitud de compra" in blob
            or "certificado de apropiacion" in blob
            or "certificación de existencia" in blob
            or "certificacion de existencia" in blob
        ):
            return "formulario"
        return role

    @staticmethod
    def _section_for_role(role: str) -> str:
        mapping = {
            "pliego": "pliego",
            "tdr": "tdr",
            "formulario": "formulario",
            "anexo": "anexo",
            "anexo_tecnico": "anexo",
            "enmienda": "enmienda",
            "circular": "circular",
            "adenda": "adenda",
        }
        return mapping.get(role, "complementario")

    @staticmethod
    def discovery_meta(ref: PortalDocumentRef) -> dict[str, Any]:
        return {
            "portal_document_id": ref.portal_document_id,
            "portal_section": ref.section,
            "original_filename": ref.filename,
            "retrieve_url": ref.retrieve_url,
        }
