"""Document Intelligence Platform — servicio principal (Fase 7)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document, DocumentAlert, DocumentChunk, DocumentRelationship
from app.schemas.document import (
    DocumentHealthResponse,
    DocumentListResponse,
    DocumentRelationshipResponse,
    DocumentResponse,
    DocumentScanResult,
    DocumentSearchHit,
    DocumentSearchResponse,
)
from app.services.document_compliance_service import DocumentComplianceService
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_intelligence_engine import DocumentIntelligenceEngine
from app.services.document_index_service import DocumentIndexService


class DocumentService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.extractor = DocumentExtractionService()
        self.intelligence = DocumentIntelligenceEngine()
        self.compliance = DocumentComplianceService()
        self.indexer = DocumentIndexService(db, tenant_id)

    def _tenant_dir(self) -> Path:
        base = Path(settings.documents_storage_path) / str(self.tenant_id)
        base.mkdir(parents=True, exist_ok=True)
        return base

    async def health(self) -> DocumentHealthResponse:
        """Conteos honestos: solo documentos activos con archivo físico válido."""
        active_stmt = select(Document).where(
            Document.tenant_id == self.tenant_id,
            Document.is_active.is_(True),
            ~Document.title.contains(" — "),
        )
        active_docs = list((await self.db.execute(active_stmt)).scalars().all())
        valid = [
            d
            for d in active_docs
            if d.storage_path and Path(d.storage_path).is_file()
        ]
        indexed = sum(1 for d in valid if d.indexed_at is not None)
        archived = await self.db.scalar(
            select(func.count()).select_from(Document).where(
                Document.tenant_id == self.tenant_id,
                Document.is_active.is_(False),
            )
        )
        chunks = await self.db.scalar(
            select(func.count()).select_from(DocumentChunk).where(
                DocumentChunk.tenant_id == self.tenant_id,
            )
        )
        alerts = await self.db.scalar(
            select(func.count()).select_from(DocumentAlert).where(
                DocumentAlert.tenant_id == self.tenant_id,
                DocumentAlert.is_resolved.is_(False),
            )
        )
        return DocumentHealthResponse(
            enabled=settings.documents_intelligence_enabled,
            storage_path=str(self._tenant_dir()),
            documents_count=len(valid),
            indexed_count=indexed,
            alerts_open=int(alerts or 0),
            archived_count=int(archived or 0),
            chunks_count=int(chunks or 0),
            ocr_ready=DocumentExtractionService.ocr_available(),
            qdrant_ready=False,
            semantic_search_ready=False,
        )

    async def list_documents(
        self,
        *,
        search: str = "",
        category: str | None = None,
        client: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DocumentListResponse:
        stmt = select(Document).where(
            Document.tenant_id == self.tenant_id,
            Document.is_active.is_(True),
            ~Document.title.contains(" — "),
        )
        if self.user_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            clause = await CompanyScopeFilter(
                self.db, self.tenant_id, self.user_id
            ).document_company_clause(Document.company)
            if clause is not None:
                stmt = stmt.where(clause)
        if category:
            stmt = stmt.where(Document.category == category)
        if client:
            stmt = stmt.where(Document.client_name.ilike(f"%{client}%"))
        if search:
            pat = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Document.title.ilike(pat),
                    Document.filename.ilike(pat),
                    Document.extracted_text.ilike(pat),
                    Document.client_name.ilike(pat),
                )
            )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0
        stmt = stmt.order_by(Document.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        items = [DocumentResponse.from_orm_doc(d) for d in result.scalars().all()]
        return DocumentListResponse(items=items, total=int(total))

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def register_document(
        self,
        *,
        filename: str,
        content: bytes,
        title: str | None = None,
        category: str | None = None,
        company: str | None = None,
        client_name: str | None = None,
        supplier_name: str | None = None,
        mime_type: str | None = None,
        metadata: dict | None = None,
    ) -> DocumentResponse:
        fmt = self.extractor.detect_format(filename, mime_type)
        doc_id = uuid.uuid4()
        storage = self._tenant_dir() / str(doc_id) / filename
        storage.parent.mkdir(parents=True, exist_ok=True)
        storage.write_bytes(content)

        extraction = self.extractor.extract(content, filename=filename, mime_type=mime_type)
        inferred = self.intelligence.infer_metadata(extraction.text, title or filename, filename)

        doc = Document(
            id=doc_id,
            tenant_id=self.tenant_id,
            title=title or filename,
            filename=filename,
            format=fmt,
            category=category or inferred.get("category", "general"),
            company=company or inferred.get("company"),
            client_name=client_name or inferred.get("client_name"),
            supplier_name=supplier_name or inferred.get("supplier_name"),
            mime_type=mime_type,
            file_size=len(content),
            storage_path=str(storage),
            tags=inferred.get("tags", []),
            keywords=inferred.get("keywords", []),
            extracted_text=extraction.text,
            created_by=self.user_id,
            metadata_=metadata or {"source": "corporate_manual"},
        )
        self.db.add(doc)
        await self.db.flush()

        await self._store_chunks(doc, extraction.pages or ([extraction.text] if extraction.text else []))

        if settings.documents_intelligence_enabled:
            await self.analyze_document(doc.id)

        await self.db.commit()
        await self.db.refresh(doc)
        return DocumentResponse.from_orm_doc(doc)

    async def _store_chunks(self, doc: Document, pages: list[str]) -> None:
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        chunks = self.extractor.chunk_pages(pages)
        now = datetime.now(timezone.utc)
        for page_num, chunk_idx, content in chunks:
            self.db.add(
                DocumentChunk(
                    tenant_id=self.tenant_id,
                    document_id=doc.id,
                    page_number=page_num,
                    chunk_index=chunk_idx,
                    content=content,
                    created_at=now,
                )
            )

    async def analyze_document(self, document_id: uuid.UUID) -> DocumentResponse:
        doc = await self.get_document(document_id)
        if not doc:
            raise ValueError("Documento no encontrado")

        text = doc.extracted_text or ""
        if not text and doc.storage_path and os.path.isfile(doc.storage_path):
            content = Path(doc.storage_path).read_bytes()
            extraction = self.extractor.extract(content, filename=doc.filename, mime_type=doc.mime_type)
            doc.extracted_text = extraction.text
            await self._store_chunks(doc, extraction.pages or ([extraction.text] if extraction.text else []))
            text = extraction.text

        intel = self.intelligence.analyze(
            text=text,
            title=doc.title,
            filename=doc.filename,
            category=doc.category,
        )
        valid_until = self.intelligence.parse_valid_until(text)
        if valid_until:
            doc.valid_until = valid_until

        comp = self.compliance.validate(
            text=text,
            title=doc.title,
            doc_type=intel.document_type,
            valid_until=doc.valid_until,
        )

        doc.intelligence = intel.model_dump()
        doc.compliance = comp.model_dump()
        doc.analyzed_at = datetime.now(timezone.utc)
        doc.tags = list(dict.fromkeys((doc.tags or []) + [intel.document_type or "general"]))[:20]

        await self._sync_alerts(doc, comp, intel.document_type)
        await self._infer_relationships(doc, intel)
        await self.indexer.index_document(doc)
        doc.indexed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(doc)
        return DocumentResponse.from_orm_doc(doc)

    async def _sync_alerts(self, doc: Document, comp, doc_type: str | None) -> None:
        payload = self.compliance.build_alert_from_compliance(
            doc_id=str(doc.id),
            title=doc.title,
            compliance=comp,
            doc_type=doc_type,
        )
        now = datetime.now(timezone.utc)
        for item in payload:
            self.db.add(
                DocumentAlert(
                    tenant_id=self.tenant_id,
                    document_id=doc.id,
                    alert_type=item["alert_type"],
                    severity=item["severity"],
                    title=item["title"],
                    message=item["message"],
                    created_at=now,
                )
            )

    async def _infer_relationships(self, doc: Document, intel) -> None:
        entities = intel.entities or {}
        if doc.client_name:
            await self._add_rel(doc.id, "customer", doc.client_name, doc.client_name)
        if doc.supplier_name:
            await self._add_rel(doc.id, "vendor", doc.supplier_name, doc.supplier_name)
        for ref in intel.dgcp_references[:3]:
            await self._add_rel(doc.id, "dgcp", ref, ref)
        for ref in intel.odoo_references[:3]:
            await self._add_rel(doc.id, "sale_order", ref, ref)

    async def _add_rel(
        self,
        document_id: uuid.UUID,
        target_type: str,
        target_id: str,
        label: str | None,
    ) -> None:
        existing = await self.db.execute(
            select(DocumentRelationship).where(
                DocumentRelationship.document_id == document_id,
                DocumentRelationship.target_type == target_type,
                DocumentRelationship.target_id == target_id,
            )
        )
        if existing.scalar_one_or_none():
            return
        self.db.add(
            DocumentRelationship(
                tenant_id=self.tenant_id,
                document_id=document_id,
                target_type=target_type,
                target_id=target_id,
                target_label=label,
                created_at=datetime.now(timezone.utc),
            )
        )

    async def search_content(self, query: str, *, limit: int = 25) -> DocumentSearchResponse:
        if not query.strip():
            return DocumentSearchResponse(query=query, total=0, hits=[])

        pat = f"%{query.strip()}%"
        chunk_q = await self.db.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.tenant_id == self.tenant_id,
                Document.is_active.is_(True),
                DocumentChunk.content.ilike(pat),
            )
            .limit(limit * 2)
        )
        hits: list[DocumentSearchHit] = []
        seen: set[str] = set()
        for chunk, doc in chunk_q.all():
            key = f"{doc.id}:{chunk.page_number}:{chunk.chunk_index}"
            if key in seen:
                continue
            seen.add(key)
            snippet = self._snippet(chunk.content, query)
            score = self._score(query, chunk.content, doc.title)
            hits.append(
                DocumentSearchHit(
                    document_id=doc.id,
                    title=doc.title,
                    filename=doc.filename,
                    page_number=chunk.page_number,
                    snippet=snippet,
                    score=score,
                    category=doc.category,
                    client_name=doc.client_name,
                )
            )
            if len(hits) >= limit:
                break

        if len(hits) < limit:
            doc_q = await self.db.execute(
                select(Document).where(
                    Document.tenant_id == self.tenant_id,
                    Document.is_active.is_(True),
                    or_(Document.title.ilike(pat), Document.filename.ilike(pat)),
                ).limit(limit)
            )
            for doc in doc_q.scalars().all():
                if any(h.document_id == doc.id for h in hits):
                    continue
                hits.append(
                    DocumentSearchHit(
                        document_id=doc.id,
                        title=doc.title,
                        filename=doc.filename,
                        page_number=None,
                        snippet=doc.title,
                        score=60.0,
                        category=doc.category,
                        client_name=doc.client_name,
                    )
                )
                if len(hits) >= limit:
                    break

        hits.sort(key=lambda h: h.score, reverse=True)
        return DocumentSearchResponse(query=query, total=len(hits), hits=hits[:limit])

    @staticmethod
    def _snippet(text: str, query: str, width: int = 160) -> str:
        lower = text.lower()
        q = query.lower().strip()
        idx = lower.find(q) if q else -1
        if idx < 0:
            return text[:width] + ("…" if len(text) > width else "")
        start = max(0, idx - 40)
        end = min(len(text), idx + len(q) + 80)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(text):
            snippet += "…"
        return snippet

    @staticmethod
    def _score(query: str, content: str, title: str) -> float:
        q = query.lower()
        c = content.lower()
        t = title.lower()
        if q in c:
            return 90.0
        if q in t:
            return 80.0
        tokens = [w for w in q.split() if len(w) >= 3]
        if tokens and all(tok in c for tok in tokens):
            return 70.0
        return 50.0

    async def get_relationships(self, document_id: uuid.UUID) -> list[DocumentRelationshipResponse]:
        result = await self.db.execute(
            select(DocumentRelationship).where(
                DocumentRelationship.document_id == document_id,
                DocumentRelationship.tenant_id == self.tenant_id,
            )
        )
        return [DocumentRelationshipResponse.model_validate(r) for r in result.scalars().all()]

    async def scan_folder(self, relative_path: str = "") -> DocumentScanResult:
        if not settings.documents_scan_enabled:
            return DocumentScanResult(scanned=0, registered=0, skipped=0, errors=["Escaneo deshabilitado"])

        base = self._tenant_dir()
        target = (base / relative_path).resolve()
        if not str(target).startswith(str(base.resolve())):
            return DocumentScanResult(scanned=0, registered=0, skipped=0, errors=["Ruta no permitida"])

        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)

        scanned = registered = skipped = 0
        errors: list[str] = []
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            scanned += 1
            existing = await self.db.execute(
                select(Document).where(
                    Document.tenant_id == self.tenant_id,
                    Document.storage_path == str(path),
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue
            try:
                content = path.read_bytes()
                await self.register_document(filename=path.name, content=content, title=path.name)
                registered += 1
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")

        return DocumentScanResult(scanned=scanned, registered=registered, skipped=skipped, errors=errors[:10])
