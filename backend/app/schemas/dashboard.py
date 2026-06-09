"""Schemas — panel ejecutivo."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ExecutiveKpi(BaseModel):
    id: str
    label: str
    value: str
    source: str
    href: str | None = None
    tone: str = "primary"
    delta: str | None = None


class ModuleSnapshot(BaseModel):
    id: str
    label: str
    status: str
    metrics: list[str] = Field(default_factory=list)
    href: str


class ExecutiveAlert(BaseModel):
    id: str
    title: str
    priority: str
    source: str
    href: str
    assignee: str | None = None


class ExecutiveActivityItem(BaseModel):
    id: str
    title: str
    subtitle: str
    timestamp: str | None = None
    href: str | None = None


class ExecutiveDashboardResponse(BaseModel):
    user_name: str
    tenant_name: str
    company_name: str | None = None
    updated_at: datetime
    proactive_message: str
    assistant_suggestions: list[str] = Field(default_factory=list)
    kpis: list[ExecutiveKpi] = Field(default_factory=list)
    modules: list[ModuleSnapshot] = Field(default_factory=list)
    alerts: list[ExecutiveAlert] = Field(default_factory=list)
    activity: list[ExecutiveActivityItem] = Field(default_factory=list)
