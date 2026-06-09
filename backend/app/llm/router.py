import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import LLMProviderError
from app.llm.providers import PROVIDER_REGISTRY
from app.llm.providers.base import BaseLLMProvider
from app.models.llm_config import LLMProviderConfig
from app.schemas.llm import LLMCompletionRequest, LLMCompletionResponse, LLMProvider


class LLMRouter:
    """Unified LLM routing with tenant-aware provider selection and fallback."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def complete(
        self,
        request: LLMCompletionRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> LLMCompletionResponse:
        providers = await self._resolve_providers(request, tenant_id)
        last_error: Exception | None = None

        for provider_name in providers:
            provider_cls = PROVIDER_REGISTRY.get(provider_name)
            if not provider_cls:
                continue
            provider: BaseLLMProvider = provider_cls()
            start = time.perf_counter()
            try:
                result = await provider.complete(request)
                latency_ms = (time.perf_counter() - start) * 1000
                return LLMCompletionResponse(
                    provider=LLMProvider(provider_name),
                    model=result.model,
                    content=result.content,
                    usage=result.usage,
                    latency_ms=round(latency_ms, 2),
                )
            except Exception as exc:
                last_error = exc
                continue

        raise LLMProviderError(
            f"All LLM providers failed. Last error: {last_error}"
        ) from last_error

    async def _resolve_providers(
        self,
        request: LLMCompletionRequest,
        tenant_id: uuid.UUID,
    ) -> list[str]:
        if request.provider:
            return [request.provider.value]

        result = await self.db.execute(
            select(LLMProviderConfig)
            .where(
                LLMProviderConfig.tenant_id == tenant_id,
                LLMProviderConfig.is_enabled.is_(True),
            )
            .order_by(LLMProviderConfig.is_default.desc(), LLMProviderConfig.priority.desc())
        )
        configs = result.scalars().all()
        if configs:
            return [c.provider for c in configs]

        default = settings.llm_default_provider
        fallback = settings.llm_fallback_provider
        providers = [default]
        if fallback != default:
            providers.append(fallback)
        return providers
