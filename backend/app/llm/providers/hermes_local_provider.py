import httpx

from app.config import settings
from app.llm.providers.base import BaseLLMProvider, ProviderResult
from app.schemas.llm import LLMCompletionRequest, LLMProvider


class HermesLocalProvider(BaseLLMProvider):
    """Local inference via Ollama-compatible API (Hermes models)."""

    provider = LLMProvider.HERMES_LOCAL

    async def complete(self, request: LLMCompletionRequest) -> ProviderResult:
        model = request.model or settings.hermes_local_default_model
        base_url = settings.hermes_local_base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [m.model_dump() for m in request.messages],
                    "stream": False,
                    "options": {"temperature": request.temperature},
                },
            )
            response.raise_for_status()
            data = response.json()
            return ProviderResult(
                content=data["message"]["content"],
                model=model,
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                },
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.hermes_local_base_url.rstrip('/')}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False
