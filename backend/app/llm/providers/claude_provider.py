import httpx

from app.config import settings
from app.llm.providers.base import BaseLLMProvider, ProviderResult
from app.schemas.llm import LLMCompletionRequest, LLMProvider


class ClaudeProvider(BaseLLMProvider):
    provider = LLMProvider.CLAUDE

    async def complete(self, request: LLMCompletionRequest) -> ProviderResult:
        model = request.model or settings.anthropic_default_model
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": request.max_tokens or 4096,
                    "messages": [m.model_dump() for m in request.messages if m.role != "system"],
                    "temperature": request.temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            return ProviderResult(
                content=content,
                model=model,
                usage={
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                },
            )

    async def health_check(self) -> bool:
        return bool(settings.anthropic_api_key)
