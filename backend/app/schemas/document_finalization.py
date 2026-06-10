"""Schemas — finalización documental DGCP (firma + sello + PDF final)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentFinalizationPreviewRequest(BaseModel):
    requirement_key: str
    checklist_item_id: uuid.UUID | None = None
    company_key: str | None = None
    signature_filename: str | None = None
    stamp_filename: str | None = None
    source_process_document_id: uuid.UUID | None = None


class DocumentFinalizationPreviewResponse(BaseModel):
    opportunity_id: uuid.UUID
    requirement_key: str
    document_type: str
    document_title: str | None = None
    company_key: str
    company_label: str
    signature: dict[str, Any] | None = None
    stamp: dict[str, Any] | None = None
    placement: dict[str, Any] = Field(default_factory=dict)
    source_filename: str | None = None
    warnings: list[str] = Field(default_factory=list)
    can_finalize: bool = False
    requires_signature: bool = True
    requires_stamp: bool = True


class DocumentFinalizationGenerateRequest(DocumentFinalizationPreviewRequest):
    notes: str | None = None
    regenerate: bool = False


class DocumentFinalizationRecordResponse(BaseModel):
    id: uuid.UUID
    requirement_key: str
    document_type: str
    output_filename: str
    output_storage_uri: str
    previous_status: str | None = None
    new_status: str
    signature_filename: str | None = None
    stamp_filename: str | None = None
    company_key: str
    finalized_at: datetime | None = None
    download_url: str | None = None


class DocumentFinalizationGenerateResponse(BaseModel):
    record: DocumentFinalizationRecordResponse
    preparation_pct: float | None = None
    expediente_status: str | None = None
    checklist_status: str | None = None
    message: str


class DocumentFinalizationBatchResponse(BaseModel):
    processed: list[DocumentFinalizationRecordResponse] = Field(default_factory=list)
    skipped: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    preparation_pct: float | None = None
    expediente_status: str | None = None
