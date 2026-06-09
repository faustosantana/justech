"""Schemas API — Work Hub."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.notifications import NotificationResponse
from app.schemas.tasks import TaskResponse


class WorkDepartmentSummary(BaseModel):
    department: str
    pending: int
    overdue: int
    critical: int


class WorkAlert(BaseModel):
    type: str
    title: str
    message: str
    count: int
    severity: str = "warning"
    link: str | None = None


class WorkActivityItem(BaseModel):
    action: str
    task_id: str | None
    task_title: str | None
    user_name: str | None
    created_at: str


class WorkHubResponse(BaseModel):
    my_tasks: list[TaskResponse] = Field(default_factory=list)
    my_pending: int = 0
    my_in_progress: int = 0
    my_overdue: int = 0
    my_critical: int = 0
    my_due_soon: int = 0
    tasks_created_by_me: list[TaskResponse] = Field(default_factory=list)
    tasks_supervised_by_me: list[TaskResponse] = Field(default_factory=list)
    by_department: list[WorkDepartmentSummary] = Field(default_factory=list)
    alerts: list[WorkAlert] = Field(default_factory=list)
    recent_activity: list[WorkActivityItem] = Field(default_factory=list)
    recent_notifications: list[NotificationResponse] = Field(default_factory=list)
    unread_notifications: int = 0
