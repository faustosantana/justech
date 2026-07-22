"""Servicio de chat Lotería IA — sesiones, contexto, tools y síntesis vía LLMRouter."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import forbidden, not_found
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
        """Redacción local natural en español (fallback seguro sin mensajes internos)."""
        if tool == "lottery_get_result_by_date" and isinstance(data, dict):
            lot = ((data.get("meta") or {}).get("resolved_lottery") or {}).get("name") or params.get(
                "lottery"
            )
            draws = data.get("draws") or []
            date_s = data.get("date")
            if not draws:
                return f"No encontré sorteos de {lot} el {date_s}."
            lines = []
            for d in draws[:8]:
                nums = ", ".join(
                    n.get("number_raw") or n.get("number_value") for n in (d.get("numbers") or [])
                )
                lines.append(nums)
            joined = "; ".join(lines)
            if len(draws) == 1:
                return f"El {date_s}, {lot} publicó los números {joined}."
            return f"El {date_s}, {lot} tuvo {len(draws)} sorteo(s): {joined}."

        if tool == "lottery_get_following_days" and isinstance(data, dict):
            lot = params.get("lottery")
            return (
                f"Para {lot}, en los días calendario del {data.get('calendar_from')} al "
                f"{data.get('calendar_to')} hubo {data.get('total_draws')} sorteo(s) "
                f"({len(data.get('days_with_draws') or [])} días con sorteo; "
                f"{len(data.get('days_without_draws') or [])} sin sorteo). "
                f"Esto cuenta días de calendario, no el número de sorteos siguientes."
            )

        if tool == "lottery_get_following_draws" and isinstance(data, dict):
            lot = params.get("lottery")
            draws = data.get("draws") or []
            bits = []
            for d in draws[:10]:
                nums = ", ".join(
                    n.get("number_raw") or n.get("number_value") for n in (d.get("numbers") or [])
                )
                bits.append(f"{d.get('draw_date')}: {nums}")
            return (
                f"Los {data.get('count_requested')} sorteos siguientes de {lot} "
                f"(no días calendario) fueron:\n- " + "\n- ".join(bits)
            )

        if tool == "lottery_get_previous_draws" and isinstance(data, dict):
            draws = data.get("draws") or []
            bits = [f"{d.get('draw_date')}" for d in draws[:10]]
            return f"Sorteos anteriores solicitados ({len(draws)}): {', '.join(bits)}."

        if tool == "lottery_get_number_occurrences" and isinstance(data, dict):
            total = (data.get("pagination") or {}).get("total")
            if total is None:
                total = data.get("total") or len(data.get("items") or data.get("occurrences") or [])
            number = params.get("number")
            lot = params.get("lottery")
            items = data.get("items") or data.get("occurrences") or []
            last = None
            if items:
                first = items[0]
                last = getattr(first, "draw_date", None) or (
                    first.get("draw_date") if isinstance(first, dict) else None
                )
            tail = f" La más reciente en el lote consultado: {last}." if last else ""
            return f"El número {number} apareció {total} vez/veces en {lot}.{tail}"

        if tool == "lottery_get_last_occurrence" and isinstance(data, dict):
            number = params.get("number")
            lot = params.get("lottery")
            items = data.get("items") or data.get("occurrences") or []
            if not items:
                return f"No encontré apariciones del {number} en {lot}."
            first = items[0]
            d = getattr(first, "draw_date", None) or (
                first.get("draw_date") if isinstance(first, dict) else None
            )
            return f"La última aparición registrada del {number} en {lot} fue el {d}."

        if tool == "lottery_find_repetitions" and isinstance(data, dict):
            items = data.get("items") or []
            if not items:
                return (
                    f"No encontré números repetidos entre {data.get('from_date')} y "
                    f"{data.get('to_date')}."
                )
            bits = [f"{i.get('number')} (×{i.get('count')})" for i in items[:10]]
            return (
                f"En {params.get('lottery')} del {data.get('from_date')} al "
                f"{data.get('to_date')}, se repitieron: " + ", ".join(bits) + "."
            )

        if tool == "lottery_compare_lotteries" and isinstance(data, dict):
            if data.get("mode") == "number_compare" or params.get("number"):
                number = data.get("number") or params.get("number")
                items = data.get("items") or []
                bits = [
                    f"{i.get('lottery')}: {i.get('occurrences')} apariciones"
                    + (f" (última {i.get('last_draw_date')})" if i.get("last_draw_date") else "")
                    for i in items
                ]
                return (
                    f"Comparación del número {number}:\n- " + "\n- ".join(bits)
                    if bits
                    else f"Sin apariciones del {number} en el período analizado."
                )
            mode = data.get("mode") or params.get("mode")
            lots = params.get("lotteries") or [
                l.get("name") for l in (data.get("lotteries") or []) if isinstance(l, dict)
            ]
            inner = data.get("data") if isinstance(data.get("data"), dict) else {}
            items = inner.get("items") or data.get("items") or []
            if mode == "frequencies" and isinstance(inner.get("by_lottery"), dict):
                parts = []
                for name, block in list(inner["by_lottery"].items())[:5]:
                    top = block.get("items") or []
                    tops = ", ".join(f"{t.get('number')} (×{t.get('count')})" for t in top[:5])
                    parts.append(f"{name}: {tops}")
                return (
                    f"Comparación de frecuencias ({params.get('from_date')}–{params.get('to_date')}) "
                    f"entre {', '.join(str(x) for x in lots)}:\n- " + "\n- ".join(parts)
                )
            bits = [
                f"{i.get('number')} en {', '.join(i.get('lotteries') or [])}"
                for i in items[:10]
                if isinstance(i, dict)
            ]
            head = f"Entre {', '.join(str(x) for x in lots)} ({params.get('from_date')}–{params.get('to_date')})"
            if not bits:
                return f"{head} no encontré coincidencias de números en el modo {mode}."
            return f"{head} coincidieron: " + "; ".join(bits) + "."

        if tool == "lottery_calculate_frequencies" and isinstance(data, dict):
            items = data.get("items") or data.get("frequencies") or []
            bits = [f"{i.get('number')} (×{i.get('count')})" for i in items[:10] if isinstance(i, dict)]
            return (
                f"Frecuencias de {params.get('lottery')} "
                f"({params.get('from_date')}–{params.get('to_date')}): " + ", ".join(bits) + "."
            )

        if tool == "lottery_get_draw_count" and isinstance(data, dict):
            if data.get("lottery"):
                return (
                    f"{data.get('lottery')} tiene {data.get('lottery_draw_count')} sorteos "
                    f"históricos (desde {data.get('first_draw_date')} hasta "
                    f"{data.get('last_draw_date')})."
                )
            return (
                f"Cobertura global: {data.get('lotteries_count')} loterías y "
                f"{data.get('draws_count')} sorteos."
            )

        if tool == "lottery_get_coverage" and isinstance(data, dict):
            return (
                f"Hay {data.get('lotteries_count')} loterías y {data.get('draws_count')} sorteos "
                f"en el histórico. Los totales reflejan la cobertura almacenada; "
                f"pueden existir fechas sin resultado para loterías específicas."
            )

        if tool == "lottery_list_lotteries" and isinstance(data, dict):
            items = data.get("items") or []
            names = [i.get("name") or i.get("commercial_name") for i in items[:30] if isinstance(i, dict)]
            more = f" (mostrando {len(names)} de {data.get('total') or len(items)})" if items else ""
            return "Puedes consultar: " + ", ".join(str(n) for n in names if n) + more + "."

        if tool == "lottery_get_latest_results" and isinstance(data, dict):
            items = data.get("items") or []
            bits = [
                f"{i.get('lottery_name') or i.get('name')}: {i.get('date') or i.get('draw_date')}"
                for i in items[:15]
                if isinstance(i, dict)
            ]
            return "Últimos resultados disponibles:\n- " + "\n- ".join(bits) if bits else "Sin últimos resultados."

        if tool == "lottery_get_sync_status" and isinstance(data, dict):
            return (
                "Los datos históricos provienen del adaptador oficial de Lotería en JAIOS "
                f"(fuente configurada; sync global={data.get('global_sync_enabled')}; "
                f"loterías con sync habilitado={data.get('lotteries_sync_enabled')}). "
                "No se usa SQL libre: solo herramientas tipadas."
            )

        if tool == "lottery_find_next_occurrences" and isinstance(data, dict):
            items = data.get("items") or []
            note = "Es aparición histórica, no predicción."
            if not items:
                return f"No hay apariciones históricas posteriores. {note}"
            first = items[0]
            return (
                f"Tras {data.get('after_date')}, el {data.get('number')} volvió a aparecer el "
                f"{first.get('draw_date')}. {note}"
            )

        if tool == "lottery_save_query" and isinstance(data, dict):
            return f"Consulta guardada como «{data.get('name')}»."

        if isinstance(data, dict) and data.get("draws_count") is not None:
            return (
                f"Cobertura: {data.get('lotteries_count')} loterías, "
                f"{data.get('draws_count')} sorteos."
            )

        return "Consulta histórica completada con los datos disponibles en JAIOS."

    async def _synthesize(
        self,
        *,
        question: str,
        template: str,
        facts: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[str, bool, str | None]:
        """Síntesis: LLMRouter → Hermes/ModelArts → plantilla natural (sin mensajes internos)."""
        if not settings.assistant_synthesis_enabled:
            return template, True, None

        payload = {
            "pregunta": question,
            "plantilla": template,
            "hechos": facts,
            "contexto": context,
        }
        user_content = (
            "Redacta la respuesta final en español claro usando SOLO estos hechos. "
            "Responde primero la pregunta con cifras concretas. "
            "No inventes números. No predigas ni recomiendes apuestas. "
            "No menciones tools, JSON, errores internos ni 'redacción no disponible'. "
            "Si falta el disclaimer histórico, agrégalo al final.\n"
            f"{json.dumps(payload, ensure_ascii=False, default=str)[:6000]}"
        )
        messages = [
            LLMMessage(role="system", content=LOTTERY_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_content),
        ]

        # 1) LLMRouter con reintentos
        provider = None
        if settings.assistant_synthesis_provider:
            try:
                provider = LLMProvider(settings.assistant_synthesis_provider)
            except ValueError:
                provider = None
        last_err: Exception | None = None
        for attempt in range(2):
            try:
                response = await self.llm.complete(
                    LLMCompletionRequest(
                        messages=messages,
                        provider=provider,
                        temperature=0.2,
                        max_tokens=700,
                    ),
                    tenant_id=self.tenant_id,
                )
                text = self._sanitize_user_facing((response.content or "").strip())
                if len(text) >= 20 and not self._looks_internal(text):
                    return text, False, getattr(response, "model", None)
            except Exception as exc:  # noqa: BLE001 — fallback controlado
                last_err = exc
                await asyncio.sleep(0.35 * (attempt + 1))

        # 2) Hermes / ModelArts (credenciales ya usadas por JAIOS)
        hermes_text, hermes_model = await self._synthesize_via_hermes(messages)
        if hermes_text:
            return hermes_text, False, hermes_model

        # 3) Fallback natural: plantilla local (nunca mensajes internos)
        _ = last_err
        return template, True, None

    async def _synthesize_via_hermes(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, str | None]:
        url = (getattr(settings, "hermes_model_api_url", None) or "").strip()
        key = (getattr(settings, "hermes_model_api_key", None) or "").strip()
        if not url or not key or not getattr(settings, "hermes_enabled", True):
            return None, None
        model = (
            getattr(settings, "hermes_default_model", None)
            or getattr(settings, "hermes_model", None)
            or "DeepSeek-V3.2"
        )
        try:
            import httpx

            async with httpx.AsyncClient(timeout=45.0) as client:
                for attempt in range(2):
                    resp = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [m.model_dump() for m in messages],
                            "temperature": 0.2,
                            "max_tokens": 700,
                        },
                    )
                    if resp.status_code >= 500:
                        await asyncio.sleep(0.4 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    content = (
                        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                    ).strip()
                    content = self._sanitize_user_facing(content)
                    if len(content) >= 20 and not self._looks_internal(content):
                        return content, str(data.get("model") or model)
                    break
        except Exception:
            return None, None
        return None, None

    @staticmethod
    def _looks_internal(text: str) -> bool:
        low = text.lower()
        needles = (
            "redacción no disponible",
            "redaccion no disponible",
            "synthesis failed",
            "tool execution error",
            "servicio de redacción",
            "resultados estructurados",
            "traceback",
            "llmprovidererror",
        )
        return any(n in low for n in needles)

    @classmethod
    def _sanitize_user_facing(cls, text: str) -> str:
        if not text:
            return text
        lines = []
        for line in text.splitlines():
            if cls._looks_internal(line):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

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
