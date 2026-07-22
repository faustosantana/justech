"""Schemas — inteligencia M365 (correo y repositorios)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class M365SuggestedAction(BaseModel):
    id: str
    label: str
    action_type: str
    href: str | None = None


class M365MailIntelligenceResponse(BaseModel):
    message_id: str
    classification: str
    classification_label: str
    classification_confidence: int
    matched_signals: list[str] = Field(default_factory=list)
    summary: str = ""
    sentiment: str = "neutral"
    priority_score: int = 50
    priority_label: str = "Normal"
    vendor: str | None = None
    client: str | None = None
    amount: float | None = None
    currency: str | None = None
    dgcp_process_code: str | None = None
    products: list[str] = Field(default_factory=list)
    document_type: str | None = None
    dates: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    suggested_actions: list[M365SuggestedAction] = Field(default_factory=list)


class M365CalendarEventCreate(BaseModel):
    subject: str
    start: str
    end: str
    location: str = ""
    body: str = ""
    attendees: list[str] = Field(default_factory=list)
    is_online: bool = False


class M365CalendarEventUpdate(BaseModel):
    subject: str | None = None
    start: str | None = None
    end: str | None = None
    location: str | None = None
    body: str | None = None


class M365CalendarActionResponse(BaseModel):
    ok: bool
    message: str
    event_id: str | None = None


class M365RepositoryFileItem(BaseModel):
    id: uuid.UUID
    name: str
    source: str
    parent_path: str = ""
    document_category: str
    document_category_label: str
    document_type: str
    classification_confidence: int
    tags: list[str] = Field(default_factory=list)
    company_key: str | None = None
    is_folder: bool = False
    mime_type: str | None = None
    size_bytes: int | None = None
    web_url: str | None = None
    download_url: str | None = None
    graph_item_id: str
    synced_at: datetime | None = None


class M365RepositoryListResponse(BaseModel):
    items: list[M365RepositoryFileItem]
    total: int
    categories: dict[str, int] = Field(default_factory=dict)
    connected: bool = True
    message: str = ""


class M365RepositorySyncResponse(BaseModel):
    ok: bool
    synced: int
    classified: int
    message: str


class M365TemplateField(BaseModel):
    key: str
    label: str
    value: str
    source: str = ""
    confidence: float = 0.0


class M365TemplatePreviewResponse(BaseModel):
    template_type: str
    template_label: str
    fields: list[M365TemplateField] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    generate_enabled: bool = False


class M365TemplateGenerateResponse(BaseModel):
    ok: bool
    filename: str
    content_base64: str
    format: str = "docx"
    message: str = ""


class M365SemanticSearchResponse(BaseModel):
    query: str
    hits: list[dict] = Field(default_factory=list)
    total: int = 0
    qdrant_ready: bool = False
    message: str = ""


class M365UploadResponse(BaseModel):
    ok: bool
    message: str
    item_id: str | None = None
    web_url: str | None = None
