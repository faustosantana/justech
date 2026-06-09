"""Modelos de datos futuros — Pydantic stubs sin tablas DB (Fase 4+)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Tasks / Work Hub (Fase 5) ───────────────────────────────────────────────


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskAssignment(BaseModel):
    """Tarea o pendiente — sin persistencia aún."""

    id: UUID | None = None
    tenant_id: UUID
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    assignee_id: UUID | None = None
    created_by_id: UUID | None = None
    due_at: datetime | None = None
    source_module: str | None = None
    source_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkHubItem(BaseModel):
    """Elemento agregado en Work Hub."""

    item_type: str
    title: str
    module_id: str
    reference_id: str
    priority: TaskPriority = TaskPriority.NORMAL
    due_at: datetime | None = None
    url: str | None = None


# ─── Notificaciones (Fase 5) ───────────────────────────────────────────────


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    TEAMS = "teams"
    PUSH = "push"


class NotificationEvent(BaseModel):
    id: UUID | None = None
    tenant_id: UUID
    user_id: UUID | None = None
    channel: NotificationChannel = NotificationChannel.IN_APP
    title: str
    body: str | None = None
    source_module: str
    source_event: str
    read: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


# ─── Enterprise Search (Fase 6) ──────────────────────────────────────────────


class SearchDocumentType(str, Enum):
    OPPORTUNITY = "opportunity"
    CUSTOMER = "customer"
    INVOICE = "invoice"
    PRODUCT = "product"
    EMAIL = "email"
    FILE = "file"
    TASK = "task"
    DOCUMENT = "document"


class SearchIndexEntry(BaseModel):
    id: str
    tenant_id: UUID
    document_type: SearchDocumentType
    title: str
    snippet: str | None = None
    source_module: str
    source_id: str
    url: str | None = None
    indexed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Enterprise Document Repository (Fase 6) ───────────────────────────────


class DocumentFormat(str, Enum):
    PDF = "pdf"
    WORD = "docx"
    EXCEL = "xlsx"
    OTHER = "other"


class EnterpriseDocument(BaseModel):
    id: UUID | None = None
    tenant_id: UUID
    name: str
    format: DocumentFormat
    source_module: str
    source_id: str | None = None
    storage_uri: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


# ─── Hermes Enterprise Memory (Fase 7) ───────────────────────────────────────


class MemoryEntryType(str, Enum):
    FACT = "fact"
    INTERACTION = "interaction"
    DECISION = "decision"
    CONTEXT = "context"


class MemoryEntry(BaseModel):
    id: UUID | None = None
    tenant_id: UUID
    entry_type: MemoryEntryType
    content: str
    source_module: str | None = None
    source_ref: str | None = None
    embedding_id: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


# ─── Multi-Agent Operations (Fase 7) ─────────────────────────────────────────


class AgentOperationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentOperation(BaseModel):
    id: UUID | None = None
    tenant_id: UUID
    agent_name: str
    operation: str
    status: AgentOperationStatus = AgentOperationStatus.QUEUED
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    modules_used: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ─── Supplier / Price (re-export conceptual; ver integrations/intelligence) ─


class SupplierQuoteStub(BaseModel):
    proveedor: str
    sku: str | None = None
    mpn: str | None = None
    precio: Decimal = Decimal("0")
    moneda: str = "USD"
    fuente: str = ""


class PriceRecommendationStub(BaseModel):
    best_supplier: str | None = None
    best_price: Decimal | None = None
    recommended_margin_pct: float | None = None
