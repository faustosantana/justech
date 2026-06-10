"""Síntesis LLM para respuestas del Copiloto — facts-only, sin alucinaciones."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import LLMProviderError
from app.llm.router import LLMRouter
from app.schemas.llm import LLMCompletionRequest, LLMMessage, LLMProvider


COPILOT_SYSTEM_PROMPT = """Eres JAIOS Copiloto Empresarial para Justech (República Dominicana).
Reglas estrictas:
- Solo usa los HECHOS del JSON provisto. No inventes cifras, clientes ni fechas.
- Responde en español, tono ejecutivo y directo (Director Comercial + Analista Financiero).
- Incluye cifras cuando existan en los hechos.
- Máximo 6 oraciones para respuestas; 3 párrafos cortos para briefing.
- Si los hechos son insuficientes, dilo y sugiere una pregunta concreta.
- Modo solo lectura: no prometas modificar Odoo ni DGCP."""


class AssistantSynthesisService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.router = LLMRouter(db)

    @property
    def enabled(self) -> bool:
        return settings.assistant_synthesis_enabled

    async def synthesize_answer(
        self,
        *,
        question: str,
        template_answer: str,
        query_type: str,
        sources: list[str],
        facts: dict[str, Any] | None = None,
        conversation_context: dict[str, Any] | None = None,
    ) -> str:
        if not self.enabled:
            return template_answer
        if query_type in ("empty", "not_connected", "write_blocked", "ambiguous"):
            return template_answer
        payload = {
            "pregunta": question,
            "tipo": query_type,
            "fuentes": sources,
            "respuesta_plantilla": template_answer,
            "hechos": facts or {},
            "contexto_conversacion": conversation_context or {},
        }
        provider = None
        if settings.assistant_synthesis_provider:
            try:
                provider = LLMProvider(settings.assistant_synthesis_provider)
            except ValueError:
                provider = None
        request = LLMCompletionRequest(
            messages=[
                LLMMessage(role="system", content=COPILOT_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=(
                        "Redacta la respuesta final usando SOLO estos hechos:\n"
                        f"{json.dumps(payload, ensure_ascii=False, default=str)[:8000]}"
                    ),
                ),
            ],
            provider=provider,
            temperature=0.2,
            max_tokens=512,
        )
        try:
            response = await self.router.complete(request, tenant_id=self.tenant_id)
            text = (response.content or "").strip()
            return text if len(text) >= 20 else template_answer
        except LLMProviderError:
            return template_answer

    async def synthesize_briefing_greeting(
        self,
        *,
        template_greeting: str,
        facts: dict[str, Any],
        mode: str,
        user_first_name: str,
    ) -> str:
        if not self.enabled:
            return template_greeting
        request = LLMCompletionRequest(
            messages=[
                LLMMessage(role="system", content=COPILOT_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=(
                        f"Modo: {mode}. Usuario: {user_first_name}. "
                        f"Hechos del día:\n{json.dumps(facts, ensure_ascii=False, default=str)[:6000]}\n"
                        "Redacta saludo proactivo estilo copiloto (bullets con •). "
                        "Termina preguntando si desea ver el resumen."
                    ),
                ),
            ],
            temperature=0.3,
            max_tokens=400,
        )
        try:
            response = await self.router.complete(request, tenant_id=self.tenant_id)
            text = (response.content or "").strip()
            return text if len(text) >= 40 else template_greeting
        except LLMProviderError:
            return template_greeting

    async def synthesize_retrieval_summary(
        self,
        *,
        question: str,
        template_summary: str,
        hits: list[dict[str, Any]],
        entities: list[dict[str, Any]] | None = None,
    ) -> str:
        facts = {
            "total": len(hits),
            "entidades": entities or [],
            "resultados": hits[:12],
        }
        return await self.synthesize_answer(
            question=question,
            template_answer=template_summary,
            query_type="enterprise_search_query",
            sources=["hermes_retrieval", "enterprise_search"],
            facts=facts,
        )
