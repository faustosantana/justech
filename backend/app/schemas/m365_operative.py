"""Schemas — Microsoft 365 Operativo."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class M365EmailAttachment(BaseModel):
    name: str
    content_type: str | None = None
    size_bytes: int | None = None
    extracted_text: str | None = None


class M365SuggestedAction(BaseModel):
    key: str
    label: str
    description: str | None = None
    confidence: int = 0
    href: str | None = None
    auto_eligible: bool = False


class M365EmailRelation(BaseModel):
    entity_type: str
    entity_id: str | None = None
    label: str
    confidence: int = 0
    href: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class M365ProcessedEmailResponse(BaseModel):
    id: uuid.UUID
    mailbox: str
    external_message_id: str
    subject: str
    sender_email: str
    sender_name: str | None = None
    received_at: datetime
    body_preview: str | None = None
    classification: str
    classification_label: str
    classification_confidence: int
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    relations: list[M365EmailRelation] = Field(default_factory=list)
    suggested_actions: list[M365SuggestedAction] = Field(default_factory=list)
    attachments: list[M365EmailAttachment] = Field(default_factory=list)
    sharepoint_path: str | None = None
    processing_status: str
    graph_connected: bool
    demo_source: bool
    hermes_indexed: bool
    related_dgcp_process_id: uuid.UUID | None = None
    related_task_id: uuid.UUID | None = None
    amount: Decimal | None = None
    currency: str | None = None


class M365ProcessedEmailListResponse(BaseModel):
    items: list[M365ProcessedEmailResponse]
    total: int
    graph_connected: bool
    demo_mode: bool
    message: str | None = None


class M365OperativeDashboard(BaseModel):
    graph_connected: bool
    demo_mode: bool
    mailboxes_monitored: int
    emails_today: int
    attachments_processed: int
    quotes_detected: int
    invoices_detected: int
    purchase_orders_detected: int
    dgcp_documents_detected: int
    tasks_generated: int
    documents_indexed: int
    pending_actions: int
    recent_emails: list[M365ProcessedEmailResponse] = Field(default_factory=list)
    briefing_lines: list[str] = Field(default_factory=list)
    quick_actions: list[M365SuggestedAction] = Field(default_factory=list)


class M365ExecuteActionRequest(BaseModel):
    action_key: str
    params: dict[str, Any] = Field(default_factory=dict)


class M365ExecuteActionResponse(BaseModel):
    status: str
    action_key: str
    message: str
    result: dict[str, Any] = Field(default_factory=dict)
    task_id: uuid.UUID | None = None
    notification_id: uuid.UUID | None = None


class M365InboundEmailWebhook(BaseModel):
    mailbox: str = "cotizaciones@justech.do"
    message_id: str | None = None
    subject: str
    sender_email: str
    sender_name: str | None = None
    body_text: str = ""
    received_at: datetime | None = None
    attachments: list[M365EmailAttachment] = Field(default_factory=list)


class M365CalendarSuggestion(BaseModel):
    title: str
    event_type: str
    suggested_date: datetime | None = None
    source_email_id: uuid.UUID | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    confidence: int = 0


class M365CalendarSuggestionsResponse(BaseModel):
    items: list[M365CalendarSuggestion]
    total: int


class M365SyncResponse(BaseModel):
    ingested: int
    processed: int
    skipped: int
    graph_connected: bool
    demo_mode: bool
    message: str
