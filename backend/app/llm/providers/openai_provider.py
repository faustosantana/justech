import time

import httpx

from app.config import settings
from app.llm.providers.base import BaseLLMProvider, ProviderResult
from app.schemas.llm import LLMCompletionRequest, LLMProvider


class OpenAIProvider(BaseLLMProvider):
    provider = LLMProvider.OPENAI

    async def complete(self, request: LLMCompletionRequest) -> ProviderResult:
        model = request.model or settings.openai_default_model
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": model,
                    "messages": [m.model_dump() for m in request.messages],
                    "temperature": request.temperature,
                    **({"max_tokens": request.max_tokens} if request.max_tokens else {}),
                },
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            return ProviderResult(
                content=data["choices"][0]["message"]["content"],
                model=model,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )

    async def health_check(self) -> bool:
        return bool(settings.openai_api_key)
