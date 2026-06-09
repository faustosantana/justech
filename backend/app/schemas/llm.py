from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    DEEPSEEK_HUAWEI = "deepseek_huawei"
    HERMES_LOCAL = "hermes_local"


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMCompletionRequest(BaseModel):
    messages: list[LLMMessage]
    provider: LLMProvider | None = None
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMCompletionResponse(BaseModel):
    provider: LLMProvider
    model: str
    content: str
    usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: float | None = None
