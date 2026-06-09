"""Indexación de documentos en search_index + enterprise search."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.search_index import SearchIndexEntry, SearchIndexState


class DocumentIndexService:
    SOURCE = "documents"

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def index_document(self, doc: Document) -> None:
        summary = ""
        if doc.intelligence and isinstance(doc.intelligence, dict):
            summary = str(doc.intelligence.get("summary", ""))[:500]
        description = (doc.extracted_text or "")[:1000]
        stmt = insert(SearchIndexEntry).values(
            tenant_id=self.tenant_id,
            source=self.SOURCE,
            entity_type="document",
            entity_id=str(doc.id),
            title=doc.title,
            subtitle=doc.filename,
            description=description or summary,
            url=f"/documents?id={doc.id}",
            company=doc.company,
            metadata_={
                "category": doc.category,
                "client_name": doc.client_name,
                "supplier_name": doc.supplier_name,
                "tags": doc.tags,
            },
            indexed_at=datetime.now(timezone.utc),
            is_active=True,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "source", "entity_type", "entity_id"],
            set_={
                "title": doc.title,
                "subtitle": doc.filename,
                "description": description or summary,
                "metadata": {
                    "category": doc.category,
                    "client_name": doc.client_name,
                    "supplier_name": doc.supplier_name,
                    "tags": doc.tags,
                },
                "indexed_at": datetime.now(timezone.utc),
                "is_active": True,
            },
        )
        await self.db.execute(stmt)

    async def touch_state(self) -> None:
        now = datetime.now(timezone.utc)
        stmt = insert(SearchIndexState).values(
            tenant_id=self.tenant_id,
            source=self.SOURCE,
            last_run_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "source"],
            set_={"last_run_at": now},
        )
        await self.db.execute(stmt)
