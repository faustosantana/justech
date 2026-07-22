"""Servicio de chat Lotería IA — sesiones, contexto, tools y síntesis vía LLMRouter."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import LLMProviderError, forbidden, not_found
from app.llm.router import LLMRouter
from app.models.lottery import LotteryChatMessage, LotteryChatSession, LotterySavedQuery
from app.schemas.llm import LLMCompletionRequest, LLMMessage, LLMProvider
from app.services.lottery_ai_contracts import LOTTERY_SYSTEM_PROMPT
from app.services.lottery_chat_context import (
    LotterySessionContext,
    merge_context_after_tool,
)
from app.services.lottery_intent import resolve_intent
from app.services.lottery_tools import LotteryToolExecutor, ToolExecutionResult


DISCLAIMER = (
    "Los resultados históricos y las estadísticas son únicamente informativos. "
    "No garantizan resultados futuros."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LotteryChatService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str | None = None,
        is_superadmin: bool = False,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role
        self.is_superadmin = is_superadmin
        self.llm = LLMRouter(db)

    async def create_session(self, *, title: str | None = None) -> LotteryChatSession:
        await self._enforce_session_limit()
        session = LotteryChatSession(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            title=title or "Nueva consulta",
            context={},
            last_message_at=_utcnow(),
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def list_sessions(self, *, limit: int = 50) -> list[LotteryChatSession]:
        q = await self.db.execute(
            select(LotteryChatSession)
            .where(
                LotteryChatSession.tenant_id == self.tenant_id,
                LotteryChatSession.user_id == self.user_id,
            )
            .order_by(LotteryChatSession.last_message_at.desc().nullslast())
            .limit(min(limit, 100))
        )
        return list(q.scalars().all())

    async def get_session(self, session_id: uuid.UUID) -> LotteryChatSession:
        session = await self.db.get(LotteryChatSession, session_id)
        if not session or session.tenant_id != self.tenant_id or session.user_id != self.user_id:
            raise not_found("Sesión no encontrada")
        return session

    async def delete_session(self, session_id: uuid.UUID) -> None:
        session = await self.get_session(session_id)
        await self.db.delete(session)
        await self.db.flush()

    async def clear_context(self, session_id: uuid.UUID) -> LotterySessionContext:
        session = await self.get_session(session_id)
        session.context = {}
        await self.db.flush()
        return LotterySessionContext()

    async def list_messages(
        self, session_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[LotteryChatMessage], int]:
        await self.get_session(session_id)
        total = await self.db.scalar(
            select(func.count())
            .select_from(LotteryChatMessage)
            .where(LotteryChatMessage.session_id == session_id)
        )
        q = await self.db.execute(
            select(LotteryChatMessage)
            .where(LotteryChatMessage.session_id == session_id)
            .order_by(LotteryChatMessage.created_at.asc())
            .offset(offset)
            .limit(min(limit, settings.lottery_chat_max_history_messages))
        )
        return list(q.scalars().all()), int(total or 0)

    async def send_message(self, session_id: uuid.UUID, content: str) -> dict[str, Any]:
        session = await self.get_session(session_id)
        ctx = LotterySessionContext.from_store(session.context or {})

        user_msg = LotteryChatMessage(
            session_id=session.id,
            role="user",
            content=content.strip(),
            tool_name=None,
            tool_payload=None,
        )
        self.db.add(user_msg)
        await self.db.flush()

        t0 = time.perf_counter()
        intent = resolve_intent(content, ctx)
        tool_trace: list[dict[str, Any]] = []
        structured: dict[str, Any] | None = None
        template = ""
        synthesis_fallback = False
        model_name: str | None = None

        if intent.kind in ("injection_refused", "prediction_refused", "refuse"):
            template = intent.refuse_message or "No puedo ayudar con esa solicitud."
            structured = {
                "type": intent.structured_type or "lottery_error",
                "warnings": [{"code": intent.kind.upper(), "message": template}],
                "disclaimer": DISCLAIMER,
            }
        elif intent.kind == "clarify":
            template = intent.clarify_message or "Necesito más información."
            structured = {
                "type": intent.structured_type or "lottery_ambiguity",
                "warnings": [{"code": "CLARIFY", "message": template}],
                "disclaimer": DISCLAIMER,
                **(intent.params or {}),
            }
            if intent.params.get("pending_ambiguity"):
                ctx.pending_ambiguity = intent.params["pending_ambiguity"]
        else:
            assert intent.tool is not None
            executor = LotteryToolExecutor(
                self.db,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                role=self.role,
                is_superadmin=self.is_superadmin,
            )
            result = await executor.execute(
                intent.tool,
                intent.params,
                structured_type=intent.structured_type or "lottery_result",
                session_context=ctx.to_store(),
            )
            tool_trace.append(
                {
                    "tool": result.tool,
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "error_code": result.error_code,
                }
            )
            structured, template = self._build_structured(result, intent.params)
            if result.status == "success":
                ctx = merge_context_after_tool(
                    ctx,
                    tool=result.tool,
                    params=intent.params,
                    result_summary=result.summary_for_context,
                )

        # LLM synthesis only for successful tool results
        final_text = template
        synthesis_fallback = False
        model_name = None
        if (
            intent.kind == "tool"
            and structured
            and structured.get("type")
            not in ("lottery_error", "lottery_ambiguity", "lottery_no_results")
        ):
            final_text, synthesis_fallback, model_name = await self._synthesize(
                question=content,
                template=template,
                facts=structured,
                context=ctx.to_store(),
            )

        if not final_text.endswith(DISCLAIMER.split(".")[0]) and intent.kind != "injection_refused":
            if DISCLAIMER not in final_text:
                final_text = f"{final_text.rstrip()}\n\n{DISCLAIMER}"

        latency_ms = int((time.perf_counter() - t0) * 1000)
        assistant_payload = {
            "structured_content": structured,
            "tool_trace": tool_trace,
            "intent": intent.kind,
            "tool": intent.tool.value if intent.tool else None,
            "params": _jsonable(intent.params),
            "synthesis_fallback": synthesis_fallback,
            "model": model_name,
            "latency_ms": latency_ms,
        }
        assistant_msg = LotteryChatMessage(
            session_id=session.id,
            role="assistant",
            content=final_text,
            tool_name=intent.tool.value if intent.tool else intent.kind,
            tool_payload=assistant_payload,
        )
        self.db.add(assistant_msg)
        session.context = ctx.to_store()
        session.last_message_at = _utcnow()
        if session.title in (None, "Nueva consulta") and content.strip():
            session.title = content.strip()[:80]
        await self.db.flush()

        return {
            "message": {
                "id": str(assistant_msg.id),
                "role": "assistant",
                "content": final_text,
                "structured_content": structured,
                "tool_trace": tool_trace,
                "created_at": assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
            },
            "user_message_id": str(user_msg.id),
            "context": ctx.to_store(),
            "suggestions": self._suggestions(ctx, intent.kind),
            "synthesis_fallback": synthesis_fallback,
            "latency_ms": latency_ms,
        }

    async def retry_last(self, session_id: uuid.UUID) -> dict[str, Any]:
        messages, _ = await self.list_messages(session_id, limit=50)
        last_user = None
        for m in reversed(messages):
            if m.role == "user":
                last_user = m
                break
        if not last_user:
            raise not_found("No hay mensaje de usuario para reintentar")
        # Remove trailing assistant error if present
        if messages and messages[-1].role == "assistant":
            await self.db.delete(messages[-1])
            await self.db.flush()
        return await self.send_message(session_id, last_user.content)

    def _build_structured(
        self, result: ToolExecutionResult, params: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        if result.status == "forbidden":
            return (
                {
                    "type": "lottery_error",
                    "warnings": [{"code": "FORBIDDEN", "message": result.error_message}],
                    "disclaimer": DISCLAIMER,
                },
                result.error_message or "No autorizado.",
            )
        if result.status != "success":
            return (
                {
                    "type": result.structured_type,
                    "warnings": [{"code": result.error_code or "ERROR", "message": result.error_message}],
                    "data": result.data,
                    "disclaimer": DISCLAIMER,
                },
                result.error_message or "Sin resultados.",
            )

        data = result.data
        st = result.structured_type
        template = self._template_from_tool(result.tool, data, params)
        return (
            {
                "type": st,
                "tool": result.tool,
                "query": _jsonable(params),
                "data": data,
                "disclaimer": DISCLAIMER,
                "warnings": (data.get("meta") or {}).get("warnings")
                if isinstance(data, dict)
                else [],
            },
            template,
        )

    def _template_from_tool(self, tool: str, data: Any, params: dict[str, Any]) -> str:
        if tool == "lottery_get_result_by_date" and isinstance(data, dict):
            lot = ((data.get("meta") or {}).get("resolved_lottery") or {}).get("name") or params.get("lottery")
            draws = data.get("draws") or []
            parts = [f"En {lot} el {data.get('date')} encontré {data.get('total', len(draws))} sorteo(s)."]
            for d in draws[:5]:
                nums = ", ".join(n.get("number_raw") or n.get("number_value") for n in (d.get("numbers") or []))
                ref = d.get("source_reference") or ""
                parts.append(f"- Sorteo {ref}: {nums}" if ref else f"- {nums}")
            return "\n".join(parts)

        if tool == "lottery_get_following_days" and isinstance(data, dict):
            return (
                f"Días calendario siguientes (semántica calendar_days): "
                f"{data.get('calendar_from')} → {data.get('calendar_to')}. "
                f"Días con sorteo: {len(data.get('days_with_draws') or [])}; "
                f"sin sorteo: {len(data.get('days_without_draws') or [])}; "
                f"sorteos en la ventana: {data.get('total_draws')}."
            )

        if tool == "lottery_get_following_draws" and isinstance(data, dict):
            dates = [d.get("draw_date") for d in (data.get("draws") or [])]
            return (
                f"Siguientes {data.get('count_requested')} sorteos (semántica next_n_draws, "
                f"no días calendario). Fechas: {', '.join(str(x) for x in dates)}."
            )

        if tool == "lottery_find_repetitions" and isinstance(data, dict):
            items = data.get("items") or []
            if not items:
                return "No encontré números repetidos en ese rango."
            bits = [f"{i.get('number')} (×{i.get('count')})" for i in items[:10]]
            return f"Repeticiones en {data.get('from_date')}–{data.get('to_date')}: " + ", ".join(bits) + "."

        if tool == "lottery_compare_lotteries" and isinstance(data, dict):
            mode = data.get("mode")
            items = (data.get("data") or {}).get("items") or []
            return (
                f"Comparación modo {mode} entre "
                f"{', '.join(l.get('name') for l in (data.get('lotteries') or []))}. "
                f"Coincidencias: {len(items)}."
            )

        if tool == "lottery_find_next_occurrences" and isinstance(data, dict):
            items = data.get("items") or []
            note = data.get("note") or "Próxima aparición histórica — no es predicción."
            if not items:
                return f"No hay apariciones históricas posteriores. {note}"
            first = items[0]
            return (
                f"Próxima aparición histórica de {data.get('number')} tras {data.get('after_date')}: "
                f"{first.get('draw_date')} (pos. {first.get('position_label')}). {note}"
            )

        if tool == "lottery_save_query" and isinstance(data, dict):
            return f"Consulta guardada como «{data.get('name')}»."

        if isinstance(data, dict) and data.get("draws_count") is not None:
            return (
                f"Cobertura: {data.get('lotteries_count')} loterías, "
                f"{data.get('draws_count')} sorteos."
            )

        return "Consulta histórica completada con datos estructurados."

    async def _synthesize(
        self,
        *,
        question: str,
        template: str,
        facts: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[str, bool, str | None]:
        if not settings.assistant_synthesis_enabled:
            return template, False, None
        provider = None
        if settings.assistant_synthesis_provider:
            try:
                provider = LLMProvider(settings.assistant_synthesis_provider)
            except ValueError:
                provider = None
        payload = {
            "pregunta": question,
            "plantilla": template,
            "hechos": facts,
            "contexto": context,
        }
        request = LLMCompletionRequest(
            messages=[
                LLMMessage(role="system", content=LOTTERY_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=(
                        "Redacta la respuesta final en español usando SOLO estos hechos. "
                        "No inventes números. Incluye el disclaimer si falta.\n"
                        f"{json.dumps(payload, ensure_ascii=False, default=str)[:6000]}"
                    ),
                ),
            ],
            provider=provider,
            temperature=0.2,
            max_tokens=512,
        )
        try:
            response = await self.llm.complete(request, tenant_id=self.tenant_id)
            text = (response.content or "").strip()
            if len(text) < 20:
                return template, True, getattr(response, "model", None)
            return text, False, getattr(response, "model", None)
        except LLMProviderError:
            return (
                f"{template}\n\n"
                "La consulta fue procesada, pero el servicio de redacción no está disponible. "
                "Estos son los resultados estructurados.",
                True,
                None,
            )

    def _suggestions(self, ctx: LotterySessionContext, kind: str) -> list[str]:
        out: list[str] = []
        if ctx.base_date and ctx.last_lottery:
            out.append("Ver siete días siguientes.")
            out.append("Ver siete sorteos siguientes.")
            out.append("Buscar repeticiones.")
            out.append("Comparar con Nacional Noche.")
            if ctx.last_numbers:
                out.append(f"Buscar próxima aparición histórica de {ctx.last_numbers[0]}.")
            out.append('Guardar consulta como "Real marzo 2022".')
        if kind in ("clarify", "injection_refused"):
            out = [
                "¿Qué salió en Real el 15 de marzo de 2022?",
                "Listar loterías disponibles.",
            ]
        return out[:6]

    async def _enforce_session_limit(self) -> None:
        count = await self.db.scalar(
            select(func.count())
            .select_from(LotteryChatSession)
            .where(
                LotteryChatSession.tenant_id == self.tenant_id,
                LotteryChatSession.user_id == self.user_id,
            )
        )
        if (count or 0) >= settings.lottery_chat_max_sessions_per_user:
            raise forbidden("Límite de sesiones de chat alcanzado")

    # --- saved queries CRUD ---

    async def list_saved_queries(self) -> list[LotterySavedQuery]:
        q = await self.db.execute(
            select(LotterySavedQuery)
            .where(
                LotterySavedQuery.tenant_id == self.tenant_id,
                LotterySavedQuery.user_id == self.user_id,
            )
            .order_by(LotterySavedQuery.updated_at.desc())
            .limit(100)
        )
        return list(q.scalars().all())

    async def rename_saved_query(self, query_id: uuid.UUID, name: str) -> LotterySavedQuery:
        row = await self._get_saved(query_id)
        row.name = name[:255]
        await self.db.flush()
        return row

    async def delete_saved_query(self, query_id: uuid.UUID) -> None:
        row = await self._get_saved(query_id)
        await self.db.delete(row)
        await self.db.flush()

    async def _get_saved(self, query_id: uuid.UUID) -> LotterySavedQuery:
        row = await self.db.get(LotterySavedQuery, query_id)
        if not row or row.tenant_id != self.tenant_id or row.user_id != self.user_id:
            raise not_found("Consulta guardada no encontrada")
        return row


def _jsonable(obj: Any) -> Any:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(x) for x in obj]
    return obj
