import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Runtime context passed to all agents."""

    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
