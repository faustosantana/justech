"""Schemas — Document Intelligence Platform."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentIntelligenceResult(BaseModel):
    summary: str = ""
    document_type: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    expirations: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    odoo_references: list[str] = Field(default_factory=list)
    dgcp_references: list[str] = Field(default_factory=list)


class DocumentComplianceResult(BaseModel):
    status: str = "ok"
    issues: list[dict[str, str]] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    expired_items: list[str] = Field(default_factory=list)


class DocumentChunkResponse(BaseModel):
    page_number: int | None
    chunk_index: int
    content: str

    model_config = {"from_attributes": True}


class DocumentRelationshipResponse(BaseModel):
    id: UUID
    target_type: str
    target_id: str
    target_label: str | None
    relation_type: str

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    filename: str
    display_name: str
    format: str
    category: str
    company: str | None
    client_name: str | None
    supplier_name: str | None
    mime_type: str | None
    file_size: int
    tags: list[str]
    keywords: list[str]
    intelligence: dict[str, Any]
    compliance: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    valid_from: date | None
    valid_until: date | None
    indexed_at: datetime | None
    analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_doc(cls, doc: Any) -> "DocumentResponse":
        raw_title = doc.title or doc.filename
        display = doc.filename
        if raw_title.startswith("Título ") and raw_title.endswith(doc.filename):
            display = doc.filename
        elif raw_title in ("Documento", "Archivo", "Resumen") or raw_title.startswith("Documento "):
            display = doc.filename
        else:
            display = doc.filename
        return cls(
            id=doc.id,
            title=raw_title,
            filename=doc.filename,
            display_name=display,
            format=doc.format,
            category=doc.category,
            company=doc.company,
            client_name=doc.client_name,
            supplier_name=doc.supplier_name,
            mime_type=doc.mime_type,
            file_size=doc.file_size,
            tags=list(doc.tags or []),
            keywords=list(doc.keywords or []),
            intelligence=dict(doc.intelligence or {}),
            compliance=dict(doc.compliance or {}),
            metadata=dict(doc.metadata_ or {}),
            valid_from=doc.valid_from,
            valid_until=doc.valid_until,
            indexed_at=doc.indexed_at,
            analyzed_at=doc.analyzed_at,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class DocumentSearchHit(BaseModel):
    document_id: UUID
    title: str
    filename: str
    page_number: int | None
    snippet: str
    score: float
    category: str | None = None
    client_name: str | None = None


class DocumentSearchResponse(BaseModel):
    query: str
    total: int
    hits: list[DocumentSearchHit]


class DocumentAlertResponse(BaseModel):
    id: UUID
    document_id: UUID | None
    alert_type: str
    severity: str
    title: str
    message: str
    is_resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentExpedienteItem(BaseModel):
    required_type: str
    label: str
    status: str
    document_id: UUID | None = None
    document_title: str | None = None


class DocumentExpedienteResponse(BaseModel):
    expediente_type: str
    subject: str
    items: list[DocumentExpedienteItem]
    complete: bool
    missing_count: int


class DocumentCompletionPreview(BaseModel):
    form_type: str
    company: str
    fields: dict[str, str]
    missing_in_source: list[str] = Field(default_factory=list)
    note: str = "Vista previa — no se modifica el archivo original."


class DocumentHealthResponse(BaseModel):
    enabled: bool
    storage_path: str
    documents_count: int
    indexed_count: int
    alerts_open: int
    archived_count: int = 0
    chunks_count: int = 0
    ocr_ready: bool = False
    qdrant_ready: bool = False
    semantic_search_ready: bool = False


class DocumentScanResult(BaseModel):
    scanned: int
    registered: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
