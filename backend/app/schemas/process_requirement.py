"""Schemas — process_requirements (Fase 1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.process_requirement_status_mapper import APPROVED_STATUSES


class ProcessRequirementItem(BaseModel):
    id: UUID
    opportunity_id: UUID
    requirement_key: str
    label: str
    category: str
    mandatory: bool = True
    priority: str = "normal"
    status: str
    source: str = "manual"
    source_evidence: dict[str, Any] = Field(default_factory=dict)
    assignee_user_id: UUID | None = None
    assignee_name: str | None = None
    due_date: date | None = None
    document_ref_type: str | None = None
    document_ref_id: UUID | None = None
    document_title: str | None = None
    template_ref: dict[str, Any] | None = None
    task_id: UUID | None = None
    notes: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)
    sort_order: int = 0
    legacy_checklist_item_id: UUID | None = None
    legacy_status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProcessRequirementListResponse(BaseModel):
    opportunity_id: UUID
    items: list[ProcessRequirementItem]
    total: int
    data_source: str = "process_requirements"
    status_counts: dict[str, int] = Field(default_factory=dict)


class ProcessRequirementUpdateRequest(BaseModel):
    status: str | None = Field(default=None, description=f"Uno de: {', '.join(sorted(APPROVED_STATUSES))}")
    document_ref_type: str | None = None
    document_ref_id: UUID | None = None
    assignee_user_id: UUID | None = None
    due_date: date | None = None
    notes: str | None = None
    history_note: str | None = Field(default=None, max_length=4000)


class ProcessRequirementUpdateResponse(BaseModel):
    opportunity_id: UUID
    requirement: ProcessRequirementItem
    synced_legacy_checklist: bool = False
