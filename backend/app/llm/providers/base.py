from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.schemas.llm import LLMCompletionRequest, LLMProvider


@dataclass
class ProviderResult:
    content: str
    model: str
    usage: dict[str, int]


class BaseLLMProvider(ABC):
    provider: LLMProvider

    @abstractmethod
    async def complete(self, request: LLMCompletionRequest) -> ProviderResult:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
