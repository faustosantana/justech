"""Tasks / Pendientes / Asignaciones — interfaces futuras (Fase 5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TaskItem:
    title: str
    tenant_id: UUID
    status: str = "pending"
    priority: TaskPriority = TaskPriority.NORMAL
    assignee_id: UUID | None = None
    due_at: datetime | None = None
    source_module: str | None = None
    source_ref: str | None = None
    metadata: dict = field(default_factory=dict)


class TaskSource(ABC):
    @abstractmethod
    async def list_open(self, tenant_id: UUID, *, assignee_id: UUID | None = None) -> list[TaskItem]:
        pass
