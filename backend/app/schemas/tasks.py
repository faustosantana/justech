"""Schemas API — Tasks Center."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class TaskCommentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    user_name: str | None
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskChecklistItemResponse(BaseModel):
    id: uuid.UUID
    text: str
    completed: bool
    completed_by_id: uuid.UUID | None
    completed_by_name: str | None
    completed_at: datetime | None
    sort_order: int

    model_config = {"from_attributes": True}


class TaskAssignmentHistoryItem(BaseModel):
    action: str
    user_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TaskAttachmentResponse(BaseModel):
    id: uuid.UUID
    name: str
    file_type: str | None
    storage_path: str | None
    related_document_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: str
    category: str
    department: str
    source: str
    created_by_id: uuid.UUID | None
    created_by_name: str | None = None
    created_by_email: str | None = None
    assigned_to_id: uuid.UUID | None
    assigned_to_name: str | None = None
    assigned_to_email: str | None = None
    supervisor_id: uuid.UUID | None
    supervisor_name: str | None = None
    supervisor_email: str | None = None
    suggested_assignee_name: str | None
    assignee_resolution_warning: str | None = None
    assignment_history: list[TaskAssignmentHistoryItem] = Field(default_factory=list)
    due_date: date | None
    completed_at: datetime | None
    company_id: int | None
    customer_name: str | None
    customer_id: str | None
    odoo_customer_id: int | None
    odoo_invoice_id: int | None
    odoo_quotation_id: int | None
    odoo_opportunity_id: int | None
    odoo_project_id: int | None
    dgcp_process_id: uuid.UUID | None
    support_ticket_id: str | None
    related_email_id: str | None
    related_document_id: str | None
    amount: Decimal | None
    currency: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    comments: list[TaskCommentResponse] = Field(default_factory=list)
    checklist_items: list[TaskChecklistItemResponse] = Field(default_factory=list)
    attachments: list[TaskAttachmentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None
    status: str = "pendiente"
    priority: str = "media"
    category: str = "otro"
    department: str = "operaciones"
    source: str = "manual"
    assigned_to_id: uuid.UUID | None = None
    suggested_assignee_name: str | None = None
    supervisor_id: uuid.UUID | None = None
    due_date: date | None = None
    company_id: int | None = None
    customer_name: str | None = None
    customer_id: str | None = None
    odoo_customer_id: int | None = None
    odoo_invoice_id: int | None = None
    odoo_quotation_id: int | None = None
    odoo_opportunity_id: int | None = None
    odoo_project_id: int | None = None
    dgcp_process_id: uuid.UUID | None = None
    support_ticket_id: str | None = None
    related_email_id: str | None = None
    related_document_id: str | None = None
    amount: Decimal | None = None
    currency: str = "DOP"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    checklist: list[str] = Field(default_factory=list)


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    department: str | None = None
    assigned_to_id: uuid.UUID | None = None
    suggested_assignee_name: str | None = None
    supervisor_id: uuid.UUID | None = None
    due_date: date | None = None
    customer_name: str | None = None
    amount: Decimal | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class TaskFromEventRequest(BaseModel):
    source: str
    event_type: str
    title: str
    description: str | None = None
    customer_name: str | None = None
    amount: Decimal | None = None
    currency: str = "DOP"
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    odoo_customer_id: int | None = None
    odoo_invoice_id: int | None = None
    odoo_quotation_id: int | None = None
    odoo_opportunity_id: int | None = None
    odoo_project_id: int | None = None
    dgcp_process_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    apply_routing: bool = True


class TaskCommentCreateRequest(BaseModel):
    comment: str


class TaskChecklistCreateRequest(BaseModel):
    text: str


class TaskChecklistUpdateRequest(BaseModel):
    completed: bool
