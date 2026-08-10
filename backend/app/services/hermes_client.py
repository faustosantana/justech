"""Cliente HTTP interno — Hermes Service."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.schemas.hermes import HermesAnalysisResult

logger = logging.getLogger(__name__)


class HermesClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_token: str | None = None,
        enabled: bool | None = None,
    ):
        self.base_url = (base_url or settings.hermes_service_url).rstrip("/")
        self.api_token = api_token if api_token is not None else settings.hermes_api_token
        self.enabled = settings.hermes_enabled if enabled is None else enabled

    def is_available(self) -> bool:
        return self.enabled and bool(self.base_url)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def _post(self, path: str, payload: dict[str, Any]) -> HermesAnalysisResult | None:
        if not self.is_available():
            logger.warning("Hermes unavailable: enabled=%s base_url=%s", self.enabled, self.base_url)
            return None
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, json=payload, headers=self._headers())
                response.raise_for_status()
                return HermesAnalysisResult.model_validate(response.json())
        except httpx.TimeoutException:
            logger.error("Hermes timeout path=%s (>90s)", path)
            return None
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Hermes HTTP error path=%s status=%s body=%s",
                path,
                exc.response.status_code,
                exc.response.text[:300],
            )
            return None
        except Exception:
            logger.exception("Hermes call failed path=%s", path)
            return None

    async def analyze_document(
        self,
        *,
        title: str = "",
        content: str = "",
        mime_type: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> HermesAnalysisResult | None:
        return await self._post(
            "/analyze/document",
            {
                "title": title,
                "content": content[:120_000],
                "mime_type": mime_type,
                "context": context or {},
            },
        )

    async def analyze_tender(self, **kwargs: Any) -> HermesAnalysisResult | None:
        return await self._post("/analyze/tender", kwargs)

    async def analyze_email_rfq(self, **kwargs: Any) -> HermesAnalysisResult | None:
        return await self._post("/analyze/email-rfq", kwargs)

    async def analyze_form(self, **kwargs: Any) -> HermesAnalysisResult | None:
        return await self._post("/analyze/form", kwargs)

    async def search_knowledge(self, **kwargs: Any) -> HermesAnalysisResult | None:
        return await self._post("/search/knowledge", kwargs)

    async def summarize(self, **kwargs: Any) -> HermesAnalysisResult | None:
        return await self._post("/summarize", kwargs)

    async def interpret_question(
        self,
        *,
        question: str,
        context: dict[str, Any] | None = None,
        facts: dict[str, Any] | None = None,
    ) -> HermesAnalysisResult | None:
        return await self._post(
            "/interpret/question",
            {
                "question": question,
                "context": context or {},
                "facts": facts or {},
            },
        )

    async def _post_raw(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout: float = 120.0,
    ) -> dict[str, Any] | None:
        if not self.is_available():
            return None
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=self._headers())
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error("Hermes timeout path=%s (>%.0fs)", path, timeout)
            return None
        except Exception:
            logger.exception("Hermes call failed path=%s", path)
            return None

    async def copilot_turn(
        self,
        *,
        system_prompt: str,
        question: str,
        messages: list[dict[str, str]] | None = None,
        model: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return await self._post_raw(
            "/copilot/turn",
            {
                "system_prompt": system_prompt,
                "question": question,
                "messages": messages or [],
                "model": model,
                "context": context or {},
            },
        )

    async def copilot_synthesize(
        self,
        *,
        system_prompt: str,
        question: str,
        messages: list[dict[str, str]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> dict[str, Any] | None:
        return await self._post_raw(
            "/copilot/synthesize",
            {
                "system_prompt": system_prompt,
                "question": question,
                "messages": messages or [],
                "tool_results": tool_results or [],
                "model": model,
            },
        )

    async def chat(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        timeout: float = 120.0,
        max_tokens: int | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {
            "system_prompt": system_prompt,
            "messages": messages,
            "model": model,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return await self._post_raw(
            "/chat",
            payload,
            timeout=timeout,
        )

    async def analyze_observation(
        self,
        *,
        channel: str,
        direction: str = "inbound",
        subject: str = "",
        body: str = "",
        from_address: str | None = None,
        from_name: str | None = None,
        to_addresses: list[str] | None = None,
    ) -> dict[str, Any] | None:
        return await self._post_raw(
            "/analyze/observation",
            {
                "channel": channel,
                "direction": direction,
                "subject": subject,
                "body": body,
                "from_address": from_address,
                "from_name": from_name,
                "to_addresses": to_addresses or [],
            },
        )

    async def health(self) -> dict[str, Any] | None:
        if not self.is_available():
            return {"status": "disabled"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def probe_llm(self) -> dict[str, Any] | None:
        if not self.is_available():
            return None
        url = f"{self.base_url}/probe/llm"
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=self._headers())
                response.raise_for_status()
                return response.json()
        except Exception:
            logger.exception("Hermes LLM probe failed")
            return None
