"""Interfaces futuras — OCR, Qdrant, M365, Hermes (Fase 7+, sin activar)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OcrPageResult:
    page_number: int
    text: str
    confidence: float = 0.0


class DocumentOcrProvider(ABC):
    """OCR para imágenes y PDF escaneados — implementación futura."""

    @abstractmethod
    async def extract_text(self, content: bytes, *, mime_type: str | None = None) -> list[OcrPageResult]:
        pass


@dataclass
class EmbeddingHit:
    document_id: str
    chunk_id: str
    score: float
    snippet: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentEmbeddingIndex(ABC):
    """Qdrant + embeddings — búsqueda semántica documental (futuro)."""

    @abstractmethod
    async def upsert_chunks(self, tenant_id: str, document_id: str, chunks: list[dict[str, Any]]) -> None:
        pass

    @abstractmethod
    async def semantic_search(self, tenant_id: str, query: str, *, limit: int = 10) -> list[EmbeddingHit]:
        pass


class ExternalDocumentConnector(ABC):
    """Conectores M365 / SharePoint / OneDrive / Gmail / Hermes — futuro."""

    source: str = "external"

    @abstractmethod
    async def list_documents(self, tenant_id: str, *, search: str = "", limit: int = 50) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_content(self, tenant_id: str, external_id: str) -> bytes:
        pass


class StubDocumentOcrProvider(DocumentOcrProvider):
    async def extract_text(self, content: bytes, *, mime_type: str | None = None) -> list[OcrPageResult]:
        return []


class StubDocumentEmbeddingIndex(DocumentEmbeddingIndex):
    async def upsert_chunks(self, tenant_id: str, document_id: str, chunks: list[dict[str, Any]]) -> None:
        return None

    async def semantic_search(self, tenant_id: str, query: str, *, limit: int = 10) -> list[EmbeddingHit]:
        return []


class StubExternalDocumentConnector(ExternalDocumentConnector):
    async def list_documents(self, tenant_id: str, *, search: str = "", limit: int = 50) -> list[dict[str, Any]]:
        return []

    async def fetch_content(self, tenant_id: str, external_id: str) -> bytes:
        return b""
