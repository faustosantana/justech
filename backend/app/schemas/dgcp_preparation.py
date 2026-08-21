"""Schemas — Mis Licitaciones / checklist preparación."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TaskStatus = Literal["pending", "in_progress", "completed", "not_applicable"]
TaskPriority = Literal["high", "medium", "low"]
TrafficLight = Literal["green", "yellow", "orange", "red", "black", "none"]
ScopeFilter = Literal["mine", "team", "unassigned", "all"]


class PrepTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority = "medium"
    assigned_user_id: UUID | None = None
    due_at: datetime | None = None


class PrepTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_user_id: UUID | None = None
    due_at: datetime | None = None


class PrepTaskOut(BaseModel):
    id: UUID
    opportunity_id: UUID
    title: str
    description: str | None = None
    status: str
    priority: str
    assigned_user_id: UUID | None = None
    assigned_user_name: str | None = None
    due_at: datetime | None = None
    template_item_key: str | None = None
    created_by_id: UUID | None = None
    completed_by_id: UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    traffic_light: TrafficLight = "none"
    hours_remaining: float | None = None


class ChecklistProgress(BaseModel):
    completed: int = 0
    applicable: int = 0
    pct: float = 0.0


class MyLicitacionRow(BaseModel):
    opportunity_id: UUID
    code: str
    institution: str
    title: str
    company: str
    status: str
    status_label: str
    process_deadline: datetime | None = None
    process_traffic_light: TrafficLight = "none"
    process_hours_remaining: float | None = None
    responsible_user_id: UUID | None = None
    responsible_name: str | None = None
    checklist_progress: ChecklistProgress = Field(default_factory=ChecklistProgress)
    next_pending_title: str | None = None
    next_pending_due_at: datetime | None = None
    priority: str = "medium"
    source_url: str | None = None


class MyWorkSummary(BaseModel):
    require_attention_today: int = 0
    due_in_3_days: int = 0
    in_preparation: int = 0
    overdue_tasks: int = 0
    new_awards: int = 0


class MyLicitacionesResponse(BaseModel):
    summary: MyWorkSummary
    items: list[MyLicitacionRow]
    total: int
    scope: str = "mine"


class HoyItem(BaseModel):
    kind: Literal["task_overdue", "task_today", "task_tomorrow", "task_soon", "process_today", "process_tomorrow"]
    sort_rank: int
    title: str
    opportunity_id: UUID
    opportunity_code: str
    institution: str
    due_at: datetime | None = None
    task_id: UUID | None = None
    priority: str | None = None
    status: str | None = None


class HoyResponse(BaseModel):
    items: list[HoyItem]
    total: int


class MyPendientesResponse(BaseModel):
    items: list[PrepTaskOut]
    total: int
    # enriched
    opportunity_code: dict[str, str] = Field(default_factory=dict)
    institution: dict[str, str] = Field(default_factory=dict)


class PrepChecklistResponse(BaseModel):
    opportunity_id: UUID
    process_deadline: datetime | None = None
    responsible_user_id: UUID | None = None
    responsible_name: str | None = None
    progress: ChecklistProgress
    next_pending: PrepTaskOut | None = None
    items: list[PrepTaskOut]


class ApplyTemplateRequest(BaseModel):
    template_id: UUID | None = None
    assign_to_responsible: bool = True


class ApplyTemplateResponse(BaseModel):
    opportunity_id: UUID
    template_id: UUID
    created: int
    skipped_duplicates: int
    items: list[PrepTaskOut]


class TemplateItemIn(BaseModel):
    item_key: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority = "medium"
    sort_order: int = 0
    default_offset_hours: int | None = None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    is_default: bool = False
    items: list[TemplateItemIn] = Field(default_factory=list)


class TemplateOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_default: bool
    is_active: bool
    items: list[TemplateItemIn] = Field(default_factory=list)


class SetResponsibleRequest(BaseModel):
    responsible_user_id: UUID | None = None
    reassign_open_tasks: bool = False


class AlertScanResponse(BaseModel):
    created: int
    skipped_duplicates: int
