"""Ingesta de adjuntos y documentos del proceso DGCP (Fase 7.3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_process_document import DGCPProcessDocument
from app.services.dgcp_process_document_classifier import classify_process_document
from app.services.dgcp_process_storage_service import DGCPProcessStorageService
from app.services.document_extraction_service import DocumentExtractionService

# Tipos de fuente del repositorio de proceso (nunca documentos corporativos indexados).
PROCESS_SOURCE_TYPES = frozenset({"portal", "dgcp_api", "portal_text", "process_file", "reference"})


class DGCPAttachmentIngestionService:
    SUPPORTED_FORMATS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"}

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.storage = DGCPProcessStorageService(tenant_id)

    async def ingest(self, opportunity: DGCPOpportunity) -> list[dict]:
        if not settings.dgcp_attachment_ingestion_enabled:
            return []

        # Conservar cargas manuales (process_file). Solo regenerar referencias portal/API.
        await self.db.execute(
            delete(DGCPProcessDocument).where(
                DGCPProcessDocument.tenant_id == self.tenant_id,
                DGCPProcessDocument.opportunity_id == opportunity.id,
                DGCPProcessDocument.source_type.notin_(("process_file",)),
            )
        )
        await self.db.commit()

        existing = await self.load_process_documents(opportunity.id)
        seen_titles: set[str] = {d.title.lower() for d in existing if d.title}
        discovered: list[dict] = [self._summary(d) for d in existing]

        for item in self._discover_from_payload(opportunity):
            title = item["title"]
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            doc = await self._register_reference(opportunity, item)
            discovered.append(self._summary(doc))

        await self.db.commit()
        return sorted(discovered, key=lambda d: {"alta": 0, "media": 1, "baja": 2}.get(d["priority"], 9))

    def _discover_from_payload(self, opportunity: DGCPOpportunity) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        payload = opportunity.raw_payload or opportunity.full_info or {}
        if not isinstance(payload, dict):
            return items

        if opportunity.source_url:
            role, priority = classify_process_document("Portal DGCP", source_url=opportunity.source_url)
            items.append({
                "title": f"Portal DGCP — {opportunity.code}",
                "source_url": opportunity.source_url,
                "source_type": "portal",
                "doc_role": role,
                "priority": priority,
                "format": "link",
            })

        for key in ("documentos", "pliego", "anexos", "adjuntos", "archivos", "requisitos"):
            val = payload.get(key) or (payload.get("extra") or {}).get(key)
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, dict):
                        title = str(entry.get("nombre") or entry.get("title") or entry.get("descripcion") or "Documento")
                        url = entry.get("url") or entry.get("link")
                        role, priority = classify_process_document(title, source_url=str(url) if url else None)
                        items.append({
                            "title": title,
                            "source_url": url,
                            "source_type": "dgcp_api",
                            "doc_role": role,
                            "priority": priority,
                            "format": "link",
                        })
                    elif isinstance(entry, str):
                        role, priority = classify_process_document(entry)
                        items.append({
                            "title": entry,
                            "source_type": "dgcp_api",
                            "doc_role": role,
                            "priority": priority,
                            "format": "reference",
                        })
            elif isinstance(val, str) and val.strip():
                role, priority = classify_process_document(val)
                items.append({
                    "title": val[:200],
                    "source_type": "dgcp_api",
                    "doc_role": role,
                    "priority": priority,
                    "format": "text",
                    "extracted_text": val,
                })

        desc = opportunity.description or ""
        if desc.strip() and len(desc) > 120:
            items.append({
                "title": f"Descripción del proceso — {opportunity.code}",
                "source_type": "portal_text",
                "doc_role": "invitacion",
                "priority": "media",
                "format": "text",
                "extracted_text": desc,
            })

        return items

    async def _register_reference(self, opportunity: DGCPOpportunity, item: dict[str, Any]) -> DGCPProcessDocument:
        role = item.get("doc_role", "general")
        priority = item.get("priority", "media")
        extracted_text = item.get("extracted_text")
        storage_filename = None
        source_type = item.get("source_type", "reference")

        if extracted_text:
            slug = self.storage.slugify(item["title"])
            storage_filename = self.storage.write_text(
                opportunity.code,
                f"{slug}.txt",
                extracted_text[:500_000],
            )
            source_type = "process_file"

        metadata: dict[str, Any] = {"discovery": item.get("source_type")}
        if storage_filename:
            metadata["storage_filename"] = storage_filename
            metadata["storage_uri"] = self.storage.relative_uri(opportunity.code, storage_filename)

        doc = DGCPProcessDocument(
            tenant_id=self.tenant_id,
            opportunity_id=opportunity.id,
            title=item["title"],
            source_url=item.get("source_url"),
            source_type=source_type,
            doc_role=role,
            priority=priority,
            format=item.get("format", "reference"),
            ingestion_status="analyzed" if extracted_text else "registered",
            extracted_text=extracted_text[:100000] if extracted_text else None,
            metadata_=metadata,
            analyzed_at=datetime.now(timezone.utc) if extracted_text else None,
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def load_process_documents(self, opportunity_id: uuid.UUID) -> list[DGCPProcessDocument]:
        result = await self.db.execute(
            select(DGCPProcessDocument).where(
                DGCPProcessDocument.tenant_id == self.tenant_id,
                DGCPProcessDocument.opportunity_id == opportunity_id,
            ).order_by(DGCPProcessDocument.priority, DGCPProcessDocument.created_at)
        )
        return list(result.scalars().all())

    async def build_extraction_corpus(self, opportunity_id: uuid.UUID) -> tuple[str, list[DGCPProcessDocument]]:
        docs = await self.load_process_documents(opportunity_id)
        priority_order = {"alta": 0, "media": 1, "baja": 2}
        usable = [
            d for d in docs
            if d.extracted_text and d.priority in ("alta", "media") and d.doc_role not in ("imagen",)
        ]
        usable.sort(key=lambda d: (priority_order.get(d.priority, 9), d.title))
        if not usable:
            usable = [d for d in docs if d.extracted_text]
        parts = [f"=== {d.title} ({d.doc_role}) ===\n{d.extracted_text}" for d in usable]
        return "\n\n".join(parts), usable

    async def read_process_file(
        self,
        opportunity: DGCPOpportunity,
        process_document: DGCPProcessDocument,
    ) -> tuple[bytes, str]:
        meta = process_document.metadata_ or {}
        filename = meta.get("storage_filename")
        if not filename:
            raise FileNotFoundError("Documento de proceso sin archivo almacenado")
        content = self.storage.read_bytes(opportunity.code, filename)
        mime = "text/plain" if str(filename).endswith(".txt") else "application/octet-stream"
        return content, mime

    @staticmethod
    def _summary(doc: DGCPProcessDocument) -> dict:
        display = DGCPAttachmentIngestionService._display_status(doc)
        meta = doc.metadata_ or {}
        return {
            "id": str(doc.id),
            "title": doc.title,
            "doc_role": doc.doc_role,
            "priority": doc.priority,
            "format": doc.format,
            "source_type": doc.source_type,
            "source_url": doc.source_url,
            "ingestion_status": doc.ingestion_status,
            "display_status": display,
            "has_text": bool(doc.extracted_text),
            "document_id": str(doc.document_id) if doc.document_id else None,
            "storage_uri": meta.get("storage_uri"),
        }

    @staticmethod
    def _display_status(doc: DGCPProcessDocument) -> str:
        meta = doc.metadata_ or {}
        if meta.get("read_error"):
            return "Error de lectura"
        if doc.ingestion_status == "error":
            return "Error de lectura"
        if doc.extracted_text and doc.doc_role in ("pliego", "tdr", "ficha_tecnica", "especificaciones"):
            return "Requisitos extraídos"
        if doc.extracted_text and doc.ingestion_status == "analyzed":
            return "Texto extraído"
        if doc.source_type == "process_file":
            return "Archivo del proceso"
        if doc.ingestion_status == "registered":
            return "Detectado"
        if doc.source_type in ("portal", "dgcp_api", "reference") and not doc.extracted_text:
            return "Detectado"
        return "Sin contenido relevante"

    def build_documents_response(self, docs: list[DGCPProcessDocument]) -> dict[str, Any]:
        """Serializa documentos del proceso para la API (nunca lanza por lista vacía)."""
        items: list[dict[str, Any]] = []
        portal: dict[str, Any] | None = None
        for doc in docs:
            summary = self._summary(doc)
            if doc.source_type == "portal":
                summary["is_portal_link"] = True
                if portal is None:
                    portal = summary
            else:
                summary["is_portal_link"] = False
            items.append(summary)
        return {"items": items, "total": len(items), "portal": portal}

    async def refresh_portal_documents(self, opportunity: DGCPOpportunity) -> dict[str, Any]:
        """Re-descubre referencias del payload sin borrar archivos ya subidos."""
        existing = await self.load_process_documents(opportunity.id)
        existing_urls = {(d.source_url or "").rstrip("/") for d in existing if d.source_url}
        existing_titles = {d.title.lower() for d in existing}
        discovered = 0
        for item in self._discover_from_payload(opportunity):
            title = str(item.get("title") or "").strip()
            url = (item.get("source_url") or "")
            url_key = url.rstrip("/")
            if url_key and url_key in existing_urls:
                continue
            if title.lower() in existing_titles and not url_key:
                continue
            await self._register_reference(opportunity, item)
            discovered += 1
            if url_key:
                existing_urls.add(url_key)
            if title:
                existing_titles.add(title.lower())
        await self.db.flush()
        docs = await self.load_process_documents(opportunity.id)
        return {
            "discovered": discovered,
            "downloaded": 0,
            "items": self.build_documents_response(docs),
        }

    async def upload_process_document(
        self,
        opportunity: DGCPOpportunity,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
        doc_role: str | None = None,
    ) -> DGCPProcessDocument:
        if not content:
            raise ValueError("Archivo vacío")
        max_bytes = 40 * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError("El archivo supera el límite de 40 MB")
        clean_name = (filename or "documento").strip() or "documento"
        lower = clean_name.lower()
        allowed_ext = (".pdf", ".doc", ".docx", ".zip", ".txt", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg")
        if not any(lower.endswith(ext) for ext in allowed_ext):
            raise ValueError("Formato no soportado. Use PDF, DOC, DOCX, ZIP, imagen o texto.")
        role = doc_role or classify_process_document(clean_name)[0]
        if role == "general" and doc_role is None:
            role, _prio = classify_process_document(clean_name)
        priority = "alta" if role in ("pliego", "tdr", "ficha_tecnica", "especificaciones", "terminos_referencia") else "media"
        storage_filename = self.storage.write_bytes(opportunity.code, clean_name, content)
        extracted = ""
        pages_text: list[str] = []
        ocr_used = False
        ocr_confidence = None
        try:
            result = DocumentExtractionService().extract(content, filename=clean_name, mime_type=mime_type)
            extracted = (result.text or "")[:500_000]
            pages_text = list(result.pages or [])[:500]
            ocr_used = bool(getattr(result, "ocr_used", False))
            ocr_confidence = getattr(result, "ocr_confidence", None)
        except Exception:
            extracted = ""
        import hashlib

        meta: dict[str, Any] = {
            "storage_filename": storage_filename,
            "storage_uri": self.storage.relative_uri(opportunity.code, storage_filename),
            "original_filename": clean_name,
            "mime_type": mime_type,
            "size_bytes": len(content),
            "source_label": "Carga manual",
            "content_hash": hashlib.sha256(content).hexdigest(),
            "page_count": len(pages_text) if pages_text else None,
            "ocr_used": ocr_used,
            "ocr_confidence": ocr_confidence,
        }
        # Guardar texto por página solo si es manejable (evidencia real de página)
        pages_payload_size = sum(len(p) for p in pages_text)
        if pages_text and pages_payload_size <= 400_000 and len(pages_text) <= 200:
            meta["pages_text"] = pages_text
        elif pages_text:
            meta["pages_text_omitted"] = True
            meta["pages_text_count"] = len(pages_text)
        if not extracted:
            meta["read_error"] = "sin_texto_extraible"
            meta["extraction_error"] = "sin_texto_extraible"
        doc = DGCPProcessDocument(
            tenant_id=self.tenant_id,
            opportunity_id=opportunity.id,
            title=clean_name,
            source_url=None,
            source_type="process_file",
            doc_role=role or "pliego",
            priority=priority,
            format=DocumentExtractionService.detect_format(clean_name, mime_type),
            ingestion_status="analyzed" if extracted else "registered",
            extracted_text=extracted or None,
            metadata_=meta,
            analyzed_at=datetime.now(timezone.utc) if extracted else None,
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def reingest_process_document(
        self,
        opportunity: DGCPOpportunity,
        process_document: DGCPProcessDocument,
    ) -> DGCPProcessDocument:
        content, mime = await self.read_process_file(opportunity, process_document)
        filename = (process_document.metadata_ or {}).get("storage_filename") or f"{process_document.title}.bin"
        extracted = ""
        pages_text: list[str] = []
        ocr_used = False
        ocr_confidence = None
        try:
            result = DocumentExtractionService().extract(content, filename=str(filename), mime_type=mime)
            extracted = (result.text or "")[:500_000]
            pages_text = list(result.pages or [])[:500]
            ocr_used = bool(getattr(result, "ocr_used", False))
            ocr_confidence = getattr(result, "ocr_confidence", None)
        except Exception:
            extracted = ""
        import hashlib

        meta = dict(process_document.metadata_ or {})
        meta["content_hash"] = hashlib.sha256(content).hexdigest()
        meta["page_count"] = len(pages_text) if pages_text else meta.get("page_count")
        meta["ocr_used"] = ocr_used
        meta["ocr_confidence"] = ocr_confidence
        pages_payload_size = sum(len(p) for p in pages_text)
        if pages_text and pages_payload_size <= 400_000 and len(pages_text) <= 200:
            meta["pages_text"] = pages_text
            meta.pop("pages_text_omitted", None)
        elif pages_text:
            meta["pages_text"] = None
            meta["pages_text_omitted"] = True
            meta["pages_text_count"] = len(pages_text)
        if extracted:
            meta.pop("read_error", None)
            meta.pop("extraction_error", None)
        else:
            meta["read_error"] = "sin_texto_extraible"
            meta["extraction_error"] = "sin_texto_extraible"
        process_document.extracted_text = extracted or None
        process_document.ingestion_status = "analyzed" if extracted else "registered"
        process_document.analyzed_at = datetime.now(timezone.utc) if extracted else None
        process_document.metadata_ = meta
        await self.db.flush()
        return process_document

    async def update_document_role(
        self,
        process_document: DGCPProcessDocument,
        doc_role: str,
    ) -> DGCPProcessDocument:
        role = (doc_role or "").strip() or "general"
        process_document.doc_role = role
        if role in ("pliego", "tdr", "ficha_tecnica", "especificaciones"):
            process_document.priority = "alta"
        await self.db.flush()
        return process_document
