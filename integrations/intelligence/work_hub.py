"""Work Hub — agregador de trabajo (Fase 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WorkHubEntry:
    item_type: str
    title: str
    module_id: str
    reference_id: str
    priority: str = "normal"
    due_at: datetime | None = None
    url: str | None = None
    metadata: dict = field(default_factory=dict)


class WorkHubAggregator:
    """Combina tareas, notificaciones y pendientes — implementación futura."""

    async def collect(self, tenant_id: str) -> list[WorkHubEntry]:
        raise NotImplementedError("Work Hub disponible en Fase 5")
