"""Canonical Bid Opportunity contract v1 (shared with Odoo Bid Center)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


SCHEMA_VERSION = "1.0.0"


class WorkflowStatus(str, Enum):
    discovered = "discovered"
    reviewed = "reviewed"
    interested = "interested"
    evaluating = "evaluating"
    go = "go"
    no_go = "no_go"
    preparing = "preparing"
    submitted = "submitted"
    won = "won"
    lost = "lost"
    cancelled = "cancelled"
    archived = "archived"


class SyncStatus(str, Enum):
    pending = "pending"
    synced = "synced"
    error = "error"
    conflict = "conflict"
    disabled = "disabled"


class InterestStatus(str, Enum):
    none = "none"
    pending = "pending"
    interested = "interested"
    discarded = "discarded"


class BidDocument(BaseModel):
    name: str
    url: str | None = None
    sha256: str | None = None
    mime: str | None = None
    size: int | None = None
    role: str | None = None


class BidOpportunityV1(BaseModel):
    schema_version: str = SCHEMA_VERSION
    source_system: str
    external_id: str
    jaios_tender_id: str | None = None
    odoo_tender_id: int | None = None
    source_portal: str | None = None
    source_url: str | None = None
    process_number: str | None = None
    title: str
    object: str | None = None
    institution_name: str
    institution_identifier: str | None = None
    publication_date: str | None = None
    clarification_deadline: str | None = None
    submission_deadline: str | None = None
    estimated_budget: float | None = None
    currency: str = "DOP"
    category: str | None = None
    province: str | None = None
    procurement_method: str | None = None
    summary: str | None = None
    compatibility_score: float | None = None
    compatibility_reasons: list[str] = Field(default_factory=list)
    risk_level: str | None = "medium"
    detected_requirements: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[BidDocument] = Field(default_factory=list)
    attachments: list[BidDocument] = Field(default_factory=list)
    source_status: str | None = None
    workflow_status: WorkflowStatus = WorkflowStatus.discovered
    interest_status: InterestStatus = InterestStatus.none
    sync_status: SyncStatus = SyncStatus.pending
    sync_version: int = 1
    content_hash: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_synced_at: datetime | None = None

    @field_validator("schema_version")
    @classmethod
    def _schema_major(cls, v: str) -> str:
        if not str(v).startswith("1."):
            raise ValueError(f"unsupported schema_version: {v}")
        return v

    @field_validator("compatibility_score")
    @classmethod
    def _score(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < 0 or v > 100:
            raise ValueError("compatibility_score out of range")
        return v

    @model_validator(mode="after")
    def _defaults(self) -> BidOpportunityV1:
        if not self.jaios_tender_id:
            self.jaios_tender_id = self.external_id
        if not self.content_hash:
            self.content_hash = compute_content_hash(self.model_dump())
        return self


def compute_content_hash(payload: dict[str, Any]) -> str:
    keys = (
        "source_system",
        "external_id",
        "source_portal",
        "process_number",
        "title",
        "object",
        "institution_name",
        "publication_date",
        "clarification_deadline",
        "submission_deadline",
        "estimated_budget",
        "currency",
        "category",
        "summary",
    )
    material = {k: payload.get(k) for k in keys}
    raw = json.dumps(material, sort_keys=True, default=str, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class InterestRequest(BaseModel):
    idempotency_key: str | None = None
    origin: str = "jaios"
    assignee_email: str | None = None


class InterestResponse(BaseModel):
    ok: bool
    idempotent: bool = False
    jaios_tender_id: str
    odoo_tender_id: int | None = None
    odoo_tender_reference: str | None = None
    odoo_url: str | None = None
    workflow_status: str | None = None
    user_name: str | None = None
    detail: str | None = None


class StatusUpdateRequest(BaseModel):
    workflow_status: WorkflowStatus
    interest_status: InterestStatus | None = None
    odoo_tender_id: int | None = None
    user_name: str | None = None
    reason: str | None = None


class AnalysisRequest(BaseModel):
    force: bool = False
    correlation_id: str | None = None
    odoo_tender_id: int | None = None
    mode: str = "standard"  # standard | copilot
    second_opinion: bool = False
