"""Hermes Enterprise Memory — interfaces futuras (Fase 7)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MemoryKind(str, Enum):
    FACT = "fact"
    INTERACTION = "interaction"
    DECISION = "decision"
    CONTEXT = "context"


@dataclass
class MemoryRecord:
    content: str
    kind: MemoryKind = MemoryKind.CONTEXT
    source_module: str | None = None
    source_ref: str | None = None
    embedding_id: str | None = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None


class EnterpriseMemoryStore(ABC):
    """Memoria persistente (Qdrant + metadatos) — Fase 7."""

    @abstractmethod
    async def remember(self, tenant_id: str, record: MemoryRecord) -> str:
        pass

    @abstractmethod
    async def recall(self, tenant_id: str, query: str, *, limit: int = 10) -> list[MemoryRecord]:
        pass
