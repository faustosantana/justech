"""Schemas API — Operational Routing Engine."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class RoutingPreviewRequest(BaseModel):
    event_type: str
    title: str = ""
    description: str = ""
    customer_name: str | None = None
    amount: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoutingPreviewResponse(BaseModel):
    event_type: str
    category: str
    department: str
    priority: str
    suggested_assignee_name: str | None
    suggested_supervisor_name: str | None = None
    assignee_resolved: bool = False
    supervisor_resolved: bool = False
    resolution_warning: str | None = None
    due_date: date | None
    notification_message: str
    checklist: list[str] = Field(default_factory=list)
    matched_rule: str


class RoutingApplyRequest(BaseModel):
    event_type: str
    title: str
    description: str = ""
    customer_name: str | None = None
    amount: float | None = None
    source: str = "event"
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    odoo_customer_id: int | None = None
    odoo_invoice_id: int | None = None
    odoo_quotation_id: int | None = None
    dgcp_process_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
