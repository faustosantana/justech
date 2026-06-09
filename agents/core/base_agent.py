from abc import ABC, abstractmethod
from typing import Any

from agents.core.context import AgentContext


class BaseAgent(ABC):
    """Abstract agent — extend in Phase 2+ for business agents."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def run(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        ...

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        return True
