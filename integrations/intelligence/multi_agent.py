"""Multi-Agent Operations — orquestación futura (Fase 7)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class AgentRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentRunRequest:
    agent_name: str
    operation: str
    modules: list[str] = field(default_factory=list)
    input_data: dict = field(default_factory=dict)


@dataclass
class AgentRunResult:
    status: AgentRunStatus
    output: dict = field(default_factory=dict)
    modules_used: list[str] = field(default_factory=list)
    error: str | None = None


class AgentOrchestrator(ABC):
    """Coordina agentes sobre centros de inteligencia sin acceso directo a credenciales."""

    @abstractmethod
    async def run(self, tenant_id: str, request: AgentRunRequest) -> AgentRunResult:
        pass
