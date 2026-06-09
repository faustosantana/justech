"""Enterprise Document Repository — interfaces futuras (Fase 6)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StoredDocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    OTHER = "other"


@dataclass
class StoredDocument:
    name: str
    format: StoredDocumentFormat
    source_module: str
    storage_uri: str | None = None
    mime_type: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None


class DocumentRepository(ABC):
    @abstractmethod
    async def store(self, tenant_id: str, document: StoredDocument, content: bytes) -> str:
        pass

    @abstractmethod
    async def retrieve(self, tenant_id: str, document_id: str) -> StoredDocument:
        pass
