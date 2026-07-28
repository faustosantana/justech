"""Servicio de chat Lotería IA — sesiones, contexto, tools y síntesis vía LLMRouter."""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import forbidden, not_found
from app.llm.router import LLMRouter
from app.lottery.ai.analyst import (
    AnalystGuardrails,
    ConversationBrain,
    IntentResolver,
    ResearchPlanner,
    ToolOrchestrator,
    format_analyst_response,
    load_analyst_config_from_payload,
)
from app.lottery.ai.analyst.research_trace import ResearchTrace
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.planner import build_plan
from app.lottery.ai.prompts.lottery_analyst_system_v6 import build_analyst_llm_messages
from app.lottery.ai.prompts.lottery_assistant_system_v1 import (
    get_active_prompt,
)
from app.lottery.ai.runtime import record_runtime_trace
from app.lottery.ai.understanding import understand
from app.models.lottery import LotteryChatMessage, LotteryChatSession, LotterySavedQuery
from app.schemas.llm import LLMCompletionRequest, LLMMessage, LLMProvider
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import (
    LotterySessionContext,
    merge_context_after_tool,
)
from app.services.lottery_tools import LotteryToolExecutor, ToolExecutionResult


DISCLAIMER = (
    "Los resultados históricos y las estadísticas son únicamente informativos. "
    "No garantizan resultados futuros."
)
# Footer-only: do not append into every assistant message body.
APPEND_DISCLAIMER_TO_BODY = False


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
        # Diagnostics (tool names / JSON / traces) off by default even for admins
        self.developer_mode = False
        self.llm = LLMRouter(db)

    def _expose_diagnostics(self) -> bool:
        return bool(self.developer_mode and (self.is_superadmin or self.role in {"admin", "tenant_admin", "superadmin"}))

    def _public_structured(self, structured: dict[str, Any] | None) -> dict[str, Any] | None:
        if not structured:
            return structured
        out = dict(structured)
        if not self._expose_diagnostics():
            out.pop("tool", None)
            out.pop("query", None)
            # Never surface raw technical dumps in data for normal users
            data = out.get("data")
            if isinstance(data, dict):
                cleaned = {
                    k: v
                    for k, v in data.items()
                    if k
                    not in {
                        "sql",
                        "source_id",
                        "raw",
                        "uuid",
                        "tool_payload",
                        "meta_debug",
                    }
                }
                out["data"] = cleaned
        return out

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

    async def rename_session(self, session_id: uuid.UUID, title: str) -> LotteryChatSession:
        session = await self.get_session(session_id)
        session.title = (title or "").strip()[:120] or session.title
        await self.db.flush()
        return session

    async def clear_context(self, session_id: uuid.UUID) -> LotterySessionContext:
        """Fase X — full conversational reset; keep message history only."""
        session = await self.get_session(session_id)
        fresh = ConversationState()
        session.context = {
            "conversation_v4": fresh.to_store(),
            "nlp_reset": True,
            "reset_reason": "clear_context",
        }
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
        raw_ctx = session.context or {}
        ctx = LotterySessionContext.from_store(raw_ctx)
        state = ConversationState.from_store(raw_ctx.get("conversation_v4") or raw_ctx)

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
        # Inject tenant/user position preference (Justech default: first_position)
        try:
            from app.services.lottery_product_service import LotteryProductService

            prefs = await LotteryProductService(
                self.db, tenant_id=self.tenant_id, user_id=self.user_id
            ).get_preferences()
            state.default_number_position_scope = getattr(
                prefs, "default_number_position_scope", None
            ) or "first_position"
            state.default_primary_position = int(
                getattr(prefs, "default_primary_position", None) or 1
            )
        except Exception:  # noqa: BLE001
            state.default_number_position_scope = state.default_number_position_scope or "first_position"
            state.default_primary_position = state.default_primary_position or 1
        ctx.default_number_position_scope = state.default_number_position_scope
        ctx.default_primary_position = state.default_primary_position

        understanding, state = understand(content, state)

        # Fase X — "nueva conversación" phrase resets filters/pending (history kept)
        if re.search(r"^\s*nueva\s+conversaci[oó]n\s*$", content or "", re.I):
            state = ConversationState(
                default_number_position_scope=state.default_number_position_scope,
                default_primary_position=state.default_primary_position,
            )
            final_text = (
                "Listo. Empezamos una conversación nueva. "
                "Conservo el historial de mensajes, pero reinicié filtros, "
                "aclaraciones e investigación activa."
            )
            session.context = {
                **(session.context or {}),
                "conversation_v4": state.to_store(),
            }
            asst = LotteryChatMessage(
                session_id=session.id,
                role="assistant",
                content=final_text,
                tool_name="chat_reset",
                tool_payload={"nlp_intent": "GENERAL_CHAT", "reset": True},
            )
            self.db.add(asst)
            await self.db.flush()
            return {
                "message": {
                    "id": str(asst.id),
                    "role": "assistant",
                    "content": final_text,
                    "structured_content": None,
                    "tool_trace": [],
                    "created_at": asst.created_at.isoformat() if asst.created_at else None,
                },
                "user_message_id": str(user_msg.id),
                "context": session.context,
                "active_context": {},
                "suggestions": self._suggestions(ctx, "chat", state=state),
                "intent": "general_chat",
            }

        # Fase A — Intent Resolver + Conversation Brain
        resolution = IntentResolver.resolve(content, state)
        # Merge same-day / compound slots into resolution for Brain memory
        up = dict(understanding.params or {})
        if up.get("relation") == "same_day" or up.get("intent") == "same_day_coincidence":
            resolution = {
                **resolution,
                "numbers": list(understanding.numbers or up.get("numbers") or resolution.get("numbers") or []),
                "active_relation": "same_day",
                "relation": "same_day",
                "position_scope": up.get("position_scope") or resolution.get("position_scope") or "any_position",
                "preferred_position": int(up.get("preferred_position") or 1),
                "position": up.get("position"),
            }
        elif understanding.numbers and len(understanding.numbers) >= 2:
            from app.lottery.ai.turn_policy import (
                exclude_limit_from_subjects,
                extract_occurrence_limit,
            )

            cleaned_nums = exclude_limit_from_subjects(
                list(understanding.numbers), extract_occurrence_limit(content)
            )
            if len(cleaned_nums) >= 2:
                resolution = {
                    **resolution,
                    "numbers": cleaned_nums,
                }
            elif cleaned_nums:
                resolution = {
                    **resolution,
                    "numbers": cleaned_nums[:1],
                }
        brain = ConversationBrain(state)
        state = brain.apply_resolution(understanding=understanding, resolution=resolution)
        # Correction / subject switch: force factual replay — never leave a menu
        if resolution.get("replay_last_intent") and (
            resolution.get("numbers") or state.active_numbers
        ):
            understanding.needs_clarification = False
            understanding.missing_slots = []
            understanding.clarification_question = None
            if not understanding.numbers:
                understanding.numbers = list(
                    resolution.get("numbers") or state.active_numbers or []
                )[:1]
            understanding.intent = "last_occurrence"  # type: ignore[assignment]
            from app.services.lottery_ai_contracts import LotteryToolName as _LTN
            from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES as _DEF

            n = understanding.numbers[0]
            understanding.tool = _LTN.GET_NUMBER_OCCURRENCES.value
            understanding.params = {
                **dict(understanding.params or {}),
                "number": n,
                "numbers": [n],
                "lotteries": list(_DEF),
                "mode": "last_n",
                "limit": 1,
                "page_size": 1,
                "order": "desc",
                "all_historical": True,
                "run_tools": True,
            }
        if resolution.get("inherit_active_number") and state.active_numbers:
            if not understanding.numbers:
                understanding.numbers = list(state.active_numbers)
            if understanding.needs_clarification and "number" in (understanding.missing_slots or []):
                understanding.missing_slots = [s for s in understanding.missing_slots if s != "number"]
                if not understanding.missing_slots and understanding.tool:
                    understanding.needs_clarification = False
                    understanding.clarification_question = None
        # Deictic last_n / previous occurrences: never ask for number when subject is known
        from app.lottery.ai.turn_policy import (
            is_other_occurrences_request,
            is_previous_occurrences_request,
        )

        if (
            (is_previous_occurrences_request(content) or is_other_occurrences_request(content))
            and state.active_numbers
        ):
            understanding.needs_clarification = False
            understanding.missing_slots = []
            understanding.clarification_question = None
            understanding.numbers = list(state.active_numbers[:1])
            understanding.intent = "last_occurrence"  # type: ignore[assignment]
            from app.services.lottery_ai_contracts import LotteryToolName as _LTN2
            from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES as _DEF2

            lim = int(resolution.get("result_limit") or resolution.get("limit") or 2)
            prior = int(resolution.get("page_offset") or resolution.get("offset") or 0)
            if prior <= 0:
                prior = int((state.last_analysis or {}).get("limit") or 0)
            n = understanding.numbers[0]
            understanding.tool = _LTN2.GET_NUMBER_OCCURRENCES.value
            understanding.params = {
                "number": n,
                "numbers": [n],
                "lotteries": list(_DEF2),
                "mode": "last_n",
                "limit": lim + prior,
                "page_size": lim + prior,
                "page_offset": prior,
                "result_limit": lim,
                "order": "desc",
                "run_tools": True,
            }
        # Preserve compound numbers after brain
        if understanding.numbers and len(understanding.numbers) >= 2:
            state.active_numbers = list(understanding.numbers)[:8]
            state.active_pair = list(state.active_numbers[:2])
        if (understanding.params or {}).get("relation") == "same_day":
            state.active_relation = "same_day"
            state.position_scope = str(
                (understanding.params or {}).get("position_scope") or state.position_scope or "any_position"
            )
            state.preferred_position = int(
                (understanding.params or {}).get("preferred_position") or state.preferred_position or 1
            )
        analyst_cfg = await self._analyst_runtime_config()

        # Fase X — conversational intents never open research/tools
        if understanding.intent in {"greeting", "general_chat", "help"} or (
            (understanding.params or {}).get("run_tools") is False
        ):
            reply = (
                (understanding.params or {}).get("conversational_reply")
                or understanding.clarification_question
                or "¿En qué puedo ayudarte con el histórico de loterías?"
            )
            session.context = {
                **(session.context or {}),
                "conversation_v4": state.to_store(),
            }
            asst = LotteryChatMessage(
                session_id=session.id,
                role="assistant",
                content=reply,
                tool_name="chat",
                tool_payload={
                    "nlp_intent": (understanding.params or {}).get("nlp_intent"),
                    "decision_log": (understanding.params or {}).get("decision_log"),
                },
            )
            self.db.add(asst)
            await self.db.flush()
            return {
                "message": {
                    "id": str(asst.id),
                    "role": "assistant",
                    "content": reply,
                    "structured_content": None,
                    "tool_trace": [],
                    "created_at": asst.created_at.isoformat() if asst.created_at else None,
                },
                "user_message_id": str(user_msg.id),
                "context": session.context,
                "active_context": {},
                "suggestions": self._suggestions(ctx, "chat", state=state),
                "intent": understanding.intent,
            }

        research_plan = ResearchPlanner.plan(
            message=content,
            understanding=understanding,
            state=state,
            config=analyst_cfg,
            resolution=resolution,
        )
        state = brain.remember_research(research_plan.to_summary())
        guardrails = AnalystGuardrails()
        research_meta = research_plan.to_summary() if research_plan.is_research else None
        research_trace = ResearchTrace(
            intent=str(understanding.intent or resolution.get("follow_up_kind") or ""),
            context_used=brain.context_snapshot() if hasattr(brain, "context_snapshot") else {},
            filters_applied=dict(state.active_filters or {}),
            investigating=bool(research_plan.is_research),
            research_mode=research_plan.mode,
            analysis_depth=analyst_cfg.analysis_depth,
            config_snapshot={
                "max_tools": analyst_cfg.effective_max_tools(),
                "max_steps": analyst_cfg.effective_max_steps(),
                "max_tokens": analyst_cfg.max_tokens,
                "timeout_seconds": analyst_cfg.timeout_seconds,
                "research_mode": analyst_cfg.research_mode,
                "analysis_depth": analyst_cfg.analysis_depth,
            },
        )

        plan = build_plan(understanding)
        tool_trace: list[dict[str, Any]] = []
        structured: dict[str, Any] | None = None
        template = ""
        synthesis_fallback = False
        model_name: str | None = None
        provider_used: str | None = None
        provider_requested = (
            getattr(settings, "assistant_synthesis_provider", None)
            or getattr(settings, "hermes_default_provider", None)
            or "huawei_modelarts"
        )
        model_requested = get_active_prompt().recommended_model
        fallback_used = False
        fallback_reason: str | None = None

        refuse_msg = None
        # Fase X.1 — apply Default Research Policy before routing clarify vs tool
        from app.lottery.ai.research_policy import apply_to_understanding, filter_material_slots

        understanding = apply_to_understanding(understanding, state)
        material_pre = filter_material_slots(understanding.missing_slots)
        if understanding.needs_clarification and not material_pre:
            understanding.needs_clarification = False
            understanding.missing_slots = []
            understanding.clarification_question = None
        # D.2/E.2: Research Engine plan must win over soft clarify (even material "query")
        if research_plan.is_research and research_plan.steps:
            understanding.needs_clarification = False
            understanding.missing_slots = []
            understanding.clarification_question = None
            if not understanding.tool:
                understanding.tool = research_plan.steps[0].tool
                understanding.params = {
                    **dict(understanding.params or {}),
                    "run_tools": True,
                    "research_kind": research_plan.question_kind,
                }
        if (
            not understanding.needs_clarification
            and not understanding.tool
            and (understanding.numbers or state.active_numbers)
            and understanding.intent
            not in {
                "greeting",
                "general_chat",
                "help",
                "out_of_domain",
                "restricted_technical",
                "prediction_request",
            }
        ):
            from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES
            from app.lottery.ai.research_policy import default_lotteries

            # Fase X.2 — keep compound same-day investigations intact
            if (
                state.active_relation == "same_day"
                or (understanding.params or {}).get("relation") == "same_day"
                or len(understanding.numbers or state.active_numbers or []) >= 2
            ) and (
                "mismo" in content.lower()
                or "coincid" in content.lower()
                or "juntos" in content.lower()
                or state.active_relation == "same_day"
            ):
                nums = list(understanding.numbers or state.active_numbers or [])[:8]
                understanding.tool = LotteryToolName.GET_NUMBER_OCCURRENCES.value
                understanding.params = {
                    **dict(understanding.params or {}),
                    "numbers": nums,
                    "relation": "same_day",
                    "active_relation": "same_day",
                    "position_scope": state.position_scope or "any_position",
                    "position": None if (state.position_scope or "any_position") == "any_position" else 1,
                    "preferred_position": state.preferred_position or 1,
                    "all_historical": True,
                    "intent": "same_day_coincidence",
                    "nlp_policy": "2.3.3",
                }
                understanding.scope = "all"
            else:
                n = (understanding.numbers or state.active_numbers)[0]
                from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

                # F.2: bare number after «¿cuándo salió?» must be last_n across defaults,
                # never compare_lotteries (which ordered asc and could surface obscure lots).
                understanding.tool = LotteryToolName.GET_NUMBER_OCCURRENCES.value
                understanding.params = {
                    **dict(understanding.params or {}),
                    "number": n,
                    "numbers": [n],
                    "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                    "mode": "last_n",
                    "limit": 1,
                    "page_size": 1,
                    "order": "desc",
                    "all_historical": True,
                    "intent": "last_occurrence",
                    "nlp_policy": "2.4.5",
                }
                understanding.intent = "last_occurrence"
                understanding.scope = "all"

        intent_kind = "clarify" if understanding.needs_clarification else "tool"
        tool_name: str | None = understanding.tool
        params = dict(understanding.params or {})

        if understanding.intent in {
            "out_of_domain",
            "restricted_technical",
            "prediction_request",
            "harmful_or_illegal",
            "unsupported",
        }:
            refuse_msg = (understanding.params or {}).get("refuse_message") or understanding.clarification_question
        if understanding.params.get("refuse"):
            refuse_msg = refuse_msg or (understanding.params or {}).get("message")
        if refuse_msg or understanding.params.get("refuse"):
            intent_kind = "refuse"
            template = refuse_msg or "No puedo ayudar con esa solicitud."
            structured = {
                "type": "lottery_error",
                "warnings": [{"code": "REFUSE", "message": template}],
            }
        elif research_plan.is_research and research_plan.steps:
            # Safety: never soft-clarify when a factual research plan exists (D.2/E.2)
            intent_kind = "tool"
            if not understanding.tool:
                understanding.tool = research_plan.steps[0].tool
            tool_name = understanding.tool
            params = dict(understanding.params or {})
        elif understanding.needs_clarification or not understanding.tool:
            intent_kind = "clarify"
            material = filter_material_slots(understanding.missing_slots)
            template = (
                understanding.clarification_question
                or "¿Puedes precisar un poco más la consulta?"
            )
            if material == ["number"] or (
                "number" in material and "lottery" not in material and "date" not in material
            ):
                if re.search(r"ultima|última|cu[aá]ndo", content or "", re.I):
                    template = "¿La última vez de cuál número?"
                else:
                    template = "¿De qué número?"
            elif brain.should_skip_number_clarify() and re.search(
                r"qu[eé]\s+n[uú]mero", template or "", re.I
            ):
                # Have active number — investigate last occurrence instead of asking filters
                understanding.needs_clarification = False
                understanding.missing_slots = []
                from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

                n = state.active_numbers[0]
                understanding.tool = LotteryToolName.GET_NUMBER_OCCURRENCES.value
                understanding.params = {
                    "number": n,
                    "numbers": [n],
                    "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                    "mode": "last_n",
                    "limit": 1,
                    "page_size": 1,
                    "order": "desc",
                    "all_historical": True,
                    "intent": "last_occurrence",
                    "nlp_policy": "2.4.5",
                }
                understanding.intent = "last_occurrence"
                intent_kind = "tool"
                tool_name = understanding.tool
                params = dict(understanding.params)
            if intent_kind == "clarify":
                structured = {
                    "type": "lottery_ambiguity",
                    "warnings": [{"code": "CLARIFY", "message": template}],
                    "missing_slots": material,
                    "intent": understanding.intent,
                    "numbers": understanding.numbers,
                    "lotteries": understanding.lotteries,
                }
                if understanding.numbers:
                    state.active_numbers = list(understanding.numbers)
                if understanding.lotteries:
                    state.active_lotteries = list(understanding.lotteries)
                # Persist last_occurrence so «El 44.» resumes the correct tool path (F.2)
                if material == ["number"] and re.search(
                    r"ultima|última|cu[aá]ndo\s+sali", content or "", re.I
                ):
                    state.last_intent = "last_occurrence"
                    state.pending_intent = "last_occurrence"
                else:
                    state.last_intent = str(understanding.intent)
                    state.pending_intent = str(understanding.intent)
                state.pending_slots = list(material)
                if understanding.intent and material:
                    # Keep last_occurrence pending when clarifying the number for «cuándo salió»
                    if state.pending_intent != "last_occurrence":
                        state.pending_intent = str(understanding.intent)
                    state.pending_params = {
                        **params,
                        **({"number": understanding.numbers[0]} if understanding.numbers else {}),
                    }
                state.clarification_question = template
            if intent_kind == "tool":
                # fall into tool execution path below via duplicated executor — use goto-style
                pass
        else:
            pass  # tool path continues below

        if intent_kind == "tool" and understanding.tool and not refuse_msg:
            executor = LotteryToolExecutor(
                self.db,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                role=self.role,
                is_superadmin=self.is_superadmin,
            )
            phase_a_handled = False
            if research_plan.is_research and research_plan.steps:
                (
                    structured,
                    template,
                    tool_trace,
                    ctx,
                    state,
                    research_trace,
                ) = await ToolOrchestrator(
                    executor, analyst_cfg, guardrails, trace=research_trace
                ).run(research_plan, ctx=ctx, state=state)
                intent_kind = "tool"
                tool_name = tool_trace[-1].get("tool") if tool_trace else understanding.tool
                state.last_plan = [s.purpose or s.tool for s in research_plan.steps]
                state.last_intent = str(understanding.intent)
                state.pending_slots = []
                state.pending_intent = None
                if structured and isinstance(structured.get("research"), dict):
                    research_meta = structured.get("research")
                phase_a_handled = True
            # Multi-tool / specialized plans
            multi_qs = (understanding.params or {}).get("multi_queries")
            if (not phase_a_handled) and (
                understanding.intent == "multi_last_occurrence"
                or (isinstance(multi_qs, list) and len(multi_qs) >= 1
                    and (understanding.params or {}).get("intent") == "multi_last_occurrence")
                or (isinstance(multi_qs, list) and len(multi_qs) >= 2)
            ):
                structured, template, tool_trace = await self._execute_multi_last_occurrence(
                    executor, understanding, plan, ctx
                )
                tool_name = "lottery_get_last_occurrence_multi"
                nums = [
                    str(q.get("number"))
                    for q in (multi_qs or [])
                    if isinstance(q, dict) and q.get("number")
                ] or list(understanding.numbers or [])
                if nums:
                    state.active_numbers = nums
                named_lots: list[str] = []
                for q in multi_qs or []:
                    if isinstance(q, dict):
                        named_lots.extend(list(q.get("lotteries") or []))
                        named_lots.extend(list(q.get("excluded_lotteries") or []))
                if named_lots:
                    state.active_lotteries = list(dict.fromkeys([*named_lots, *state.active_lotteries]))
                state.last_multi_queries = list(multi_qs or [])
                state.last_position_scope = (understanding.params or {}).get("position_scope") or "first_position"
                state.last_intent = "multi_last_occurrence"
                state.last_plan = ["multi_last_occurrence"]
                state.pending_slots = []
                state.pending_intent = None
                state.last_tool = tool_name
            elif (not phase_a_handled) and (
                understanding.intent == "post_occurrence_window"
                or understanding.tool == "lottery_analyze_post_occurrence_window"
            ):
                structured, template, tool_trace = await self._execute_post_occurrence_window(
                    executor, understanding, ctx
                )
                tool_name = "lottery_analyze_post_occurrence_window"
                if understanding.numbers:
                    state.active_numbers = list(understanding.numbers)
                if understanding.lotteries:
                    state.active_lotteries = list(
                        dict.fromkeys([*understanding.lotteries, *state.active_lotteries])
                    )
                if understanding.calendar_days:
                    state.calendar_window = int(understanding.calendar_days)
                state.last_intent = "post_occurrence_window"
                state.last_plan = ["post_occurrence_per_lottery", "insights"]
                state.pending_slots = []
                state.pending_intent = None
                state.last_analysis = {
                    "type": "post_occurrence_window",
                    "params": dict(understanding.params or {}),
                }
            elif (not phase_a_handled) and (
                understanding.tool == "lottery_compare_last_occurrence_all"
                or (
                    understanding.scope == "all"
                    and understanding.intent == "last_occurrence"
                    and (understanding.params or {}).get("mode") != "last_n"
                )
                or (
                    understanding.intent == "compare_numbers"
                    and understanding.numbers
                )
                or (
                    understanding.intent == "last_occurrence"
                    and len(understanding.lotteries or []) > 1
                    and (understanding.params or {}).get("mode") != "last_n"
                )
            ):
                # Prefer dedicated across-lotteries tool when lotteries known
                lots = list(understanding.lotteries or state.active_lotteries)
                number = (understanding.numbers or state.active_numbers or [None])[0]
                if lots and number and (
                    understanding.tool
                    in {
                        LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                        LotteryToolName.COMPARE_LOTTERIES.value,
                    }
                    or understanding.intent == "compare_numbers"
                ):
                    result = await executor.execute(
                        LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES,
                        {"lotteries": lots[:8], "number": number},
                        structured_type="lottery_comparison",
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
                    structured, template = self._build_structured(result, {"lotteries": lots, "number": number})
                    tool_name = result.tool
                else:
                    structured, template, tool_trace = await self._execute_multi_last_occurrence(
                        executor, understanding, plan, ctx
                    )
                    tool_name = understanding.tool or "lottery_compare_last_occurrence"
                if understanding.numbers:
                    state.active_numbers = list(understanding.numbers)
                if lots:
                    state.active_lotteries = list(dict.fromkeys([*state.active_lotteries, *lots]))
                # Persist per-lottery occurrence dates for follow-ups ("7 días después")
                rows = ((structured or {}).get("data") or {}).get("rows") or []
                number = (understanding.numbers or state.active_numbers or [None])[0]
                for row in rows:
                    if isinstance(row, dict) and row.get("found") and row.get("last_date"):
                        state.remember_occurrence(
                            lottery=str(row.get("lottery")),
                            number=str(row.get("number") or number or ""),
                            draw_date=row.get("last_date"),
                            position=row.get("position"),
                        )
                state.last_intent = str(understanding.intent)
                state.last_plan = [s.purpose or s.tool for s in plan.steps]
                state.pending_slots = []
                state.pending_intent = None
                state.last_tool_results = [{"tool": tool_name, "rows": rows[:8]}]
                state.metric_context = understanding.metric or understanding.intent
                # Chain: after multi last-occurrence, optionally run post window
                if (understanding.params or {}).get("then_post_window"):
                    per_dates = {
                        k: v.date
                        for k, v in state.last_occurrences.items()
                        if v and v.date
                    }
                    count = int(
                        (understanding.params or {}).get("count")
                        or state.calendar_window
                        or 7
                    )
                    unit = (understanding.params or {}).get("unit") or "days"
                    chained = UnderstandingResult(
                        intent="post_occurrence_window",
                        lotteries=lots,
                        numbers=[str(number)] if number else [],
                        calendar_days=count if unit == "days" else None,
                        draw_count=count if unit == "draws" else None,
                        tool="lottery_analyze_post_occurrence_window",
                        params={
                            "number": number,
                            "lotteries": lots,
                            "per_lottery_dates": per_dates,
                            "unit": unit,
                            "count": count,
                            "direction": "after",
                        },
                        per_lottery_dates=per_dates,
                        confidence=0.9,
                        source="follow_up",
                    )
                    post_structured, post_template, post_trace = (
                        await self._execute_post_occurrence_window(executor, chained, ctx)
                    )
                    structured = post_structured
                    template = (
                        (template or "")
                        + "\n\n---\n\n"
                        + (post_template or "")
                    ).strip()
                    tool_trace.extend(post_trace)
                    tool_name = "lottery_analyze_post_occurrence_window"
                    state.last_intent = "post_occurrence_window"
                    state.calendar_window = count if unit == "days" else state.calendar_window
                    state.last_analysis = {
                        "type": "post_occurrence_window",
                        "params": dict(chained.params or {}),
                    }
            elif not phase_a_handled:
                tool_enum = self._tool_enum(understanding.tool)
                exec_params = self._normalize_tool_params(understanding.tool, params, state)
                result = await executor.execute(
                    tool_enum,
                    exec_params,
                    structured_type=(
                        "lottery_complete_analysis"
                        if understanding.tool == "lottery_run_complete_analysis"
                        else (
                            "lottery_numeric_relations"
                            if understanding.intent == "numeric_relations"
                            else "lottery_result"
                        )
                    ),
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
                structured, template = self._build_structured(result, exec_params)
                if result.status == "success":
                    ctx = merge_context_after_tool(
                        ctx,
                        tool=result.tool,
                        params=exec_params,
                        result_summary=result.summary_for_context,
                    )
                    if exec_params.get("lottery"):
                        lot = str(exec_params["lottery"])
                        if lot not in state.active_lotteries:
                            state.active_lotteries = [lot, *[x for x in state.active_lotteries if x != lot]]
                    if exec_params.get("number"):
                        # Fase X.2 — do not collapse compound same-day pairs
                        if (
                            exec_params.get("relation") == "same_day"
                            or exec_params.get("active_relation") == "same_day"
                        ) and isinstance(exec_params.get("numbers"), list):
                            state.active_numbers = [
                                str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n)
                                for n in exec_params["numbers"]
                            ][:8]
                            state.active_pair = list(state.active_numbers[:2])
                            state.active_relation = "same_day"
                            state.position_scope = str(
                                exec_params.get("position_scope") or "any_position"
                            )
                            state.preferred_position = int(
                                exec_params.get("preferred_position") or 1
                            )
                        else:
                            state.active_numbers = [str(exec_params["number"])]
                    elif (
                        isinstance(exec_params.get("numbers"), list)
                        and len(exec_params.get("numbers") or []) >= 2
                    ):
                        state.active_numbers = [
                            str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n)
                            for n in exec_params["numbers"]
                        ][:8]
                        state.active_pair = list(state.active_numbers[:2])
                        if exec_params.get("relation") == "same_day":
                            state.active_relation = "same_day"
                            state.position_scope = str(
                                exec_params.get("position_scope") or "any_position"
                            )
                            state.preferred_position = int(
                                exec_params.get("preferred_position") or 1
                            )
                    # Fase Final — remember coincidence anchors for continuity
                    if (
                        exec_params.get("relation") == "same_day"
                        or exec_params.get("active_relation") == "same_day"
                    ) and isinstance(result.data, dict):
                        items = list(result.data.get("items") or [])
                        last_item = items[0] if items else None
                        last_date = None
                        if isinstance(last_item, dict):
                            last_date = str(last_item.get("date") or "")[:10] or None
                        if last_date:
                            state.active_date = last_date
                        if exec_params.get("lottery") or exec_params.get("lotteries"):
                            lots = list(exec_params.get("lotteries") or [])
                            if exec_params.get("lottery"):
                                lots = [str(exec_params["lottery"]), *[x for x in lots if x != exec_params["lottery"]]]
                            state.active_lotteries = lots[:8]
                        state.last_analysis = {
                            **dict(state.last_analysis or {}),
                            "type": "same_day_coincidence",
                            "numbers": list(state.active_numbers or []),
                            "last_coincidence_date": last_date,
                            "total": result.data.get("total"),
                            "relation": "same_day",
                            "position_scope": state.position_scope,
                            "lottery": (state.active_lotteries[0] if state.active_lotteries else None),
                        }
                        state.conversation_summary = (
                            f"Investigación activa: coincidencias same_day de "
                            f"{' + '.join(state.active_numbers[:2])}"
                            + (f" · última {last_date}" if last_date else "")
                            + "."
                        )[:500]
                    if exec_params.get("date") or exec_params.get("base_date"):
                        d = exec_params.get("date") or exec_params.get("base_date")
                        state.date_context = d
                    # Persist derived last-occurrence date into conversational memory
                    summary = result.summary_for_context or {}
                    if summary.get("last_occurrence_date") or summary.get("base_date"):
                        lot = str(
                            summary.get("lottery")
                            or exec_params.get("lottery")
                            or (state.active_lotteries[0] if state.active_lotteries else "")
                        )
                        num = str(
                            summary.get("number")
                            or exec_params.get("number")
                            or (state.active_numbers[0] if state.active_numbers else "")
                        )
                        state.remember_occurrence(
                            lottery=lot,
                            number=num,
                            draw_date=summary.get("last_occurrence_date") or summary.get("base_date"),
                            position=summary.get("position"),
                        )
                    if exec_params.get("window_draws") or exec_params.get("count"):
                        state.draw_count_context = int(
                            exec_params.get("window_draws") or exec_params.get("count")
                        )
                    # Complete analysis memory for conversational follow-ups
                    if result.tool == "lottery_run_complete_analysis" and isinstance(
                        structured, dict
                    ):
                        data = structured.get("data") if isinstance(structured.get("data"), dict) else structured
                        primary_n = None
                        if isinstance(data.get("primary"), dict):
                            primary_n = data["primary"].get("number")
                        elif structured.get("primary"):
                            primary_n = (structured.get("primary") or {}).get("number")
                        # Prefer nested payload from tool
                        payload = data if data.get("observed_number") is not None else structured
                        if payload.get("type") == "lottery_result" and isinstance(
                            payload.get("data"), dict
                        ):
                            payload = payload["data"]
                        obs = payload.get("observed_number") or exec_params.get("observed_number")
                        primary_n = primary_n or (payload.get("primary") or {}).get("number")
                        state.current_primary_candidate = (
                            int(primary_n) if primary_n is not None else None
                        )
                        alts = [
                            int(a.get("number"))
                            for a in (payload.get("alternatives") or [])
                            if isinstance(a, dict) and a.get("number") is not None
                        ]
                        state.current_alternatives = alts[:6]
                        state.last_analysis = {
                            "type": "complete_analysis",
                            "observed": obs,
                            "primary": primary_n,
                            "confirmer": payload.get("confirmer") or exec_params.get("confirmer"),
                            "date": payload.get("date") or exec_params.get("date"),
                            "lottery": payload.get("lottery") or exec_params.get("lottery"),
                            "historical_summary": (payload.get("historical") or {}).get("resumen"),
                        }
                        state.historical_summary = (payload.get("historical") or {}).get("resumen")
                        state.active_date = (
                            str(payload.get("date") or "")[:10] or None
                        )
                        if obs is not None and not (
                            state.active_relation == "same_day"
                            and len(state.active_numbers or []) >= 2
                        ):
                            state.active_numbers = [str(obs)]
                        # Short rolling summary
                        bits = [f"Analizado {obs}"]
                        if primary_n is not None:
                            bits.append(f"candidato {primary_n}")
                        if payload.get("date"):
                            bits.append(f"fecha {payload.get('date')}")
                        # Keep confirmer in active pair when present
                        conf = payload.get("confirmer") or exec_params.get("confirmer")
                        if obs is not None and conf is not None:
                            state.active_pair = [str(obs).zfill(2), str(conf).zfill(2)]
                            if len(state.active_numbers or []) < 2:
                                state.active_numbers = list(state.active_pair)
                        prev = (state.conversation_summary or "").strip()
                        state.conversation_summary = (
                            (prev + " · " if prev else "") + "; ".join(bits)
                        )[-500:]
                    # Mirror sticky fields from merged legacy context
                    if ctx.base_date:
                        state.date_context = ctx.base_date
                    if ctx.last_lottery and ctx.last_lottery not in state.active_lotteries:
                        state.active_lotteries = [ctx.last_lottery, *state.active_lotteries]
                    state.last_intent = str(understanding.intent)
                    state.last_tool = result.tool
                    state.last_plan = [s.purpose or s.tool for s in plan.steps]
                    state.pending_slots = []
                    state.pending_intent = None
                    state.clarification_question = None
                    state.metric_context = understanding.metric or understanding.intent
                    state.last_tool_results = [
                        {
                            "tool": result.tool,
                            "summary": {
                                k: summary.get(k)
                                for k in (
                                    "semantics",
                                    "last_occurrence_date",
                                    "lottery",
                                    "number",
                                )
                                if summary.get(k) is not None
                            },
                        }
                    ]
                params = exec_params
                tool_name = result.tool

        # LLM synthesis: tool facts OR soft rewrite of clarifications
        final_text = template
        synthesis_fallback = False
        model_name = None
        recent_msgs = await self._recent_dialogue(session_id, limit=12)
        from app.lottery.ai.turn_policy import ConversationPolicy

        force_template = ConversationPolicy.should_force_local_template(state, content)
        if intent_kind == "tool" and structured and structured.get("type") not in (
            "lottery_error",
            "lottery_no_results",
        ):
            if force_template:
                # H.5–H.9: factual template only — do not let LLM reopen prior subjects
                final_text = template
                synthesis_fallback = True
                provider_used = "local_template"
                fallback_used = True
                fallback_reason = "meta_continuity_local_template"
                state.force_local_template = False
                if isinstance(state.active_filters, dict):
                    state.active_filters.pop("meta_continuity", None)
            else:
                final_text, synthesis_fallback, model_name, provider_used = await self._synthesize(
                    question=content,
                    template=template,
                    facts=structured,
                    context={**ctx.to_store(), "conversation_v4": state.to_store()},
                    recent_messages=recent_msgs,
                    mode="tool",
                    max_tokens=analyst_cfg.max_tokens,
                )
                if synthesis_fallback:
                    fallback_used = True
                    fallback_reason = "synthesis_unavailable_or_failed"
                    provider_used = provider_used or "local_template"
            facts_for_fmt = {
                "primary": state.current_primary_candidate,
                "observed": (state.last_analysis or {}).get("observed")
                or (state.active_numbers[0] if state.active_numbers else None),
                "confirmer": (state.last_analysis or {}).get("confirmer"),
                "historical": (state.last_analysis or {}).get("historical_summary"),
                "lottery": (state.last_analysis or {}).get("lottery")
                or (state.active_lotteries[0] if state.active_lotteries else None),
                "year": (state.active_filters or {}).get("year"),
                "compare_with": (state.active_filters or {}).get("compare_with"),
                "last_occurrence_date": (state.last_analysis or {}).get("date"),
                "total": (state.last_analysis or {}).get("total"),
            }
            # Prefer THIS turn's tool summaries over any leftover analysis memory
            if isinstance(research_meta, dict):
                for ev in (research_meta.get("evidence") or [])[::-1]:
                    sm = ev.get("summary") if isinstance(ev, dict) else None
                    if not isinstance(sm, dict):
                        continue
                    if sm.get("number") is not None:
                        facts_for_fmt["observed"] = sm.get("number")
                    if sm.get("lottery") and (
                        sm.get("last_occurrence_date") or sm.get("semantics") == "last_occurrence"
                    ):
                        facts_for_fmt["lottery"] = sm.get("lottery")
                    if sm.get("last_occurrence_date"):
                        facts_for_fmt["last_occurrence_date"] = sm.get("last_occurrence_date")
                    if sm.get("total") is not None or sm.get("count") is not None:
                        facts_for_fmt["total"] = sm.get("total") if sm.get("total") is not None else sm.get("count")
                    break
            prior_research = bool(state.current_research)
            # Fase D — observational discovery over research evidence (does not touch RE/Planner/Brain)
            if isinstance(research_meta, dict) and research_meta.get("evidence_package"):
                try:
                    from app.lottery.ai.analyst.discovery_engine import (
                        DiscoveryRequest,
                        get_discovery_engine,
                    )

                    disc = get_discovery_engine().discover(
                        DiscoveryRequest(
                            kind="auto_discovery",
                            context={
                                "evidence_package": research_meta.get("evidence_package"),
                                "tools_used": research_meta.get("evidence_package", {}).get("tools_used")
                                or research_meta.get("steps_completed"),
                                "period": (research_meta.get("evidence_package") or {}).get("period"),
                                "investigation_id": research_meta.get("trace_id"),
                                "confirmation_stats": research_meta.get("confirmation_stats") or {},
                                "lottery_counts": research_meta.get("lottery_counts") or {},
                                "year_counts": research_meta.get("year_counts") or {},
                                "position_counts": research_meta.get("position_counts") or {},
                                "charts": research_meta.get("charts") or facts_for_fmt.get("charts") or [],
                            },
                        )
                    )
                    if disc.status == "ok":
                        research_meta = {
                            **research_meta,
                            "discovery": {
                                "finding_count": (disc.payload or {}).get("finding_count"),
                                "findings": (disc.payload or {}).get("findings") or [],
                                "discarded_count": (disc.payload or {}).get("discarded_count"),
                                "message": (disc.payload or {}).get("message"),
                            },
                        }
                except Exception:  # noqa: BLE001 — discovery must not break chat
                    pass
            # Fase E — Knowledge Engine: optional auto-save of verified research (never mutates RE/DE)
            if isinstance(research_meta, dict) and research_meta.get("evidence_package"):
                try:
                    from app.lottery.ai.analyst.knowledge_engine import get_knowledge_engine

                    ep = research_meta.get("evidence_package") or {}
                    evidences = ep.get("evidences") or ep.get("items") or []
                    if not evidences and ep:
                        evidences = [{"evidence_package": ep, "tools_used": ep.get("tools_used") or []}]
                    if evidences and not research_meta.get("discarded") and not research_meta.get("has_errors"):
                        kn = get_knowledge_engine().save_from_research_payload(
                            {
                                "title": (content or "")[:120],
                                "original_question": content,
                                "executive_summary": (final_text or "")[:800],
                                "full_investigation": final_text or "",
                                "evidences": evidences,
                                "tools_used": ep.get("tools_used")
                                or research_meta.get("steps_completed")
                                or [],
                                "evidence_level": research_meta.get("evidence_level") or ep.get("evidence_level"),
                                "confidence": research_meta.get("confidence") or ep.get("confidence"),
                                "finished_ok": True,
                                "discarded": False,
                                "has_errors": False,
                                "period": ep.get("period"),
                                "historical_version": research_meta.get("historical_version")
                                or ep.get("historical_version"),
                            }
                        )
                        if kn.get("saved"):
                            research_meta = {
                                **research_meta,
                                "knowledge": {
                                    "id": (kn.get("investigation") or {}).get("id"),
                                    "saved": True,
                                    "obsolete": (kn.get("investigation") or {}).get("obsolete"),
                                    "obsolescence_notice": kn.get("obsolescence_notice"),
                                },
                            }
                except Exception:  # noqa: BLE001 — knowledge must not break chat
                    pass
            final_text = format_analyst_response(
                guardrails.sanitize_llm_text(final_text or template),
                facts=facts_for_fmt,
                research=research_meta if isinstance(research_meta, dict) else None,
                question=content,
                conversation_context={
                    "has_prior_research": prior_research,
                    "active_numbers": list(state.active_numbers or []),
                    "active_relation": state.active_relation,
                    "focus_stack": list(getattr(state, "focus_stack", None) or []),
                },
            )
        elif intent_kind == "clarify":
            missing = list(understanding.missing_slots or state.pending_slots or [])
            # Never let the LLM rewrite a pure "missing number" ask into lottery/form noise.
            if missing == ["number"] or (
                "number" in missing and "lottery" not in missing and "date" not in missing
            ):
                final_text = template
                provider_used = "local_template"
                synthesis_fallback = True
                fallback_used = True
                fallback_reason = "clarify_number_slot_locked"
            else:
                final_text, synthesis_fallback, model_name, provider_used = await self._synthesize(
                    question=content,
                    template=template,
                    facts={
                        "type": "lottery_ambiguity",
                        "clarify": template,
                        "missing_slots": understanding.missing_slots,
                        "known_numbers": state.active_numbers or understanding.numbers,
                        "known_lotteries": state.active_lotteries or understanding.lotteries,
                        "primary_candidate": state.current_primary_candidate,
                    },
                    context={**ctx.to_store(), "conversation_v4": state.to_store()},
                    recent_messages=recent_msgs,
                    mode="clarify",
                    max_tokens=min(analyst_cfg.max_tokens, 600),
                )
                if synthesis_fallback:
                    fallback_used = True
                    fallback_reason = "clarify_local_template"
                    provider_used = provider_used or "local_template"
                    final_text = template

        if APPEND_DISCLAIMER_TO_BODY and DISCLAIMER not in final_text and intent_kind != "refuse":
            final_text = f"{final_text.rstrip()}\n\n{DISCLAIMER}"
        # Strip accidental duplicated disclaimer from synthesizer
        if final_text.count(DISCLAIMER) > 1:
            final_text = final_text.replace(DISCLAIMER, "", final_text.count(DISCLAIMER) - 1).rstrip()

        research_trace.finish(response=final_text)
        try:
            state = ConversationBrain(state).remember_trace(research_trace.to_dict())
        except Exception:  # noqa: BLE001
            pass

        latency_ms = int((time.perf_counter() - t0) * 1000)
        runtime_trace = {
            "provider_requested": provider_requested,
            "provider_used": provider_used or ("local_template" if synthesis_fallback or intent_kind != "tool" else None),
            "model_requested": model_requested,
            "model_used": model_name,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "llm_latency_ms": latency_ms,
            "tools_executed": [t.get("tool") for t in tool_trace],
            "synthesis_status": (
                "skipped"
                if intent_kind != "tool"
                else ("fallback" if synthesis_fallback else "ok")
            ),
            "intent": understanding.intent,
            "prompt_version": get_active_prompt().version,
            "research_trace": research_trace.to_dict() if self._expose_diagnostics() else {
                "trace_id": research_trace.trace_id,
                "investigating": research_trace.investigating,
                "duration_ms": research_trace.duration_ms,
            },
            "analyst_config": {
                "max_tools": analyst_cfg.effective_max_tools(),
                "max_steps": analyst_cfg.effective_max_steps(),
                "max_tokens": analyst_cfg.max_tokens,
                "timeout_seconds": analyst_cfg.timeout_seconds,
                "research_mode": analyst_cfg.research_mode,
                "analysis_depth": analyst_cfg.analysis_depth,
            },
        }
        state.provider_trace = runtime_trace
        try:
            record_runtime_trace(runtime_trace, success=not fallback_used or intent_kind == "clarify")
        except Exception:  # noqa: BLE001
            pass
        try:
            from app.lottery.ai.usage import estimate_cost_usd, record_ai_usage

            tools_used = [t.get("tool") for t in tool_trace if isinstance(t, dict) and t.get("tool")]
            await record_ai_usage(
                self.db,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                session_id=session.id,
                provider=str(provider_used or model_name or "local"),
                model=model_name,
                latency_ms=latency_ms,
                estimated_cost_usd=estimate_cost_usd(prompt_tokens=0, completion_tokens=0),
                tool_names=[str(x) for x in tools_used if x],
                ok=not synthesis_fallback or bool(final_text),
            )
        except Exception:  # noqa: BLE001 — metrics must not break chat
            pass

        merged_context = _jsonable(
            {
                **ctx.to_store(),
                "conversation_v4": state.to_store(),
                "last_lottery": state.active_lotteries[0] if state.active_lotteries else ctx.last_lottery,
                "last_numbers": state.active_numbers or ctx.last_numbers,
                "last_query_semantics": state.last_intent or ctx.last_query_semantics,
                "last_draw_count": state.draw_count_context or ctx.last_draw_count,
            }
        )
        # Keep sticky LotterySessionContext aligned with ConversationState for suggestions/API.
        ctx = LotterySessionContext(
            last_lottery=state.active_lotteries[0] if state.active_lotteries else ctx.last_lottery,
            compared_lotteries=list(state.active_lotteries[1:] if len(state.active_lotteries) > 1 else ctx.compared_lotteries),
            base_date=state.date_context or ctx.base_date,
            last_draw_count=state.draw_count_context or ctx.last_draw_count,
            last_days=state.calendar_window or ctx.last_days,
            last_numbers=list(state.active_numbers or ctx.last_numbers or []),
            last_tool=state.last_tool or ctx.last_tool,
            last_query_semantics=state.last_intent or ctx.last_query_semantics,
            default_number_position_scope=state.default_number_position_scope,
            default_primary_position=state.default_primary_position,
            last_analysis=dict(state.last_analysis or {}),
            conversation_summary=state.conversation_summary,
            current_primary_candidate=state.current_primary_candidate,
        )

        public_structured = self._public_structured(structured if isinstance(structured, dict) else None)
        from app.lottery.ai.same_day_coincidence import analyzing_label
        from app.lottery.ai.turn_policy import filters_label_es, position_label_es

        nums_ctx = list(state.active_numbers or [])
        # Explicit filters only — never show found result lottery/position as scope
        explicit_lots = None
        if (state.active_filters or {}).get("lottery_explicit") and state.active_lotteries:
            explicit_lots = list(state.active_lotteries[:4])
        pos_scope = state.position_scope or state.last_position_scope
        if not (state.active_filters or {}).get("position_explicit"):
            # Prefer any_position / all when position was only a result
            if pos_scope in {
                "first_position",
                "second_position",
                "third_position",
                "1",
                "2",
                "3",
                1,
                2,
                3,
            } and state.last_intent in {
                "last_occurrence",
                "last_n_occurrences",
                "compare_across_lotteries",
            }:
                pos_scope = "all"
        active_context = {
            "number": (nums_ctx[0] if nums_ctx else None),
            "numbers": nums_ctx[:8],
            "analyzing": analyzing_label(
                nums_ctx, relation=state.active_relation
            ),
            "relation": state.active_relation,
            "position_scope": position_label_es(pos_scope),
            "preferred_position": state.preferred_position or 1,
            "filters_label": filters_label_es(
                lottery_scope=explicit_lots or "all",
                position_scope=pos_scope,
            ),
            # Date/lottery below are last RESULT metadata, not investigation filters
            "date": None,
            "lottery": None,
            "position": None,
            "last_result_date": (state.last_analysis or {}).get("date"),
            "last_result_lottery": (state.last_analysis or {}).get("lottery"),
            "last_result_position": position_label_es(
                (state.last_analysis or {}).get("position")
            )
            if (state.last_analysis or {}).get("position") is not None
            else None,
            "primary_candidate": state.current_primary_candidate
            or ((state.last_analysis or {}).get("primary")),
            "alternatives": list(state.current_alternatives or [])[:4],
            "summary": state.conversation_summary,
        }
        assistant_payload = _jsonable(
            {
                "structured_content": public_structured,
                "tool_trace": tool_trace if self._expose_diagnostics() else [],
                "intent": understanding.intent,
                "entities": {
                    "lotteries": understanding.lotteries or state.active_lotteries,
                    "numbers": understanding.numbers or state.active_numbers,
                },
                "missing_slots": understanding.missing_slots or state.pending_slots,
                "clarification": template if intent_kind == "clarify" else None,
                "plan": [s.model_dump() for s in plan.steps] if self._expose_diagnostics() else [],
                "tool": tool_name if self._expose_diagnostics() else None,
                "params": params if self._expose_diagnostics() else {},
                "synthesis_fallback": synthesis_fallback,
                "model": model_name if self._expose_diagnostics() else None,
                "provider": provider_used if self._expose_diagnostics() else None,
                "latency_ms": latency_ms,
                "runtime_trace": runtime_trace if self._expose_diagnostics() else {},
                "prompt_version": get_active_prompt().version,
                "analysis_params": (
                    (public_structured or {}).get("query")
                    if self._expose_diagnostics() and isinstance(public_structured, dict)
                    else None
                ),
            }
        )
        assistant_msg = LotteryChatMessage(
            session_id=session.id,
            role="assistant",
            content=final_text,
            tool_name=(tool_name or intent_kind) if self._expose_diagnostics() else intent_kind,
            tool_payload=assistant_payload,
        )
        self.db.add(assistant_msg)
        session.context = merged_context
        session.last_message_at = _utcnow()
        if session.title in (None, "Nueva consulta") and content.strip():
            session.title = content.strip()[:80]
        await self.db.flush()

        return {
            "message": {
                "id": str(assistant_msg.id),
                "role": "assistant",
                "content": final_text,
                "structured_content": public_structured,
                "tool_trace": tool_trace if self._expose_diagnostics() else [],
                "created_at": assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
                "runtime_trace": runtime_trace if self._expose_diagnostics() else {},
            },
            "user_message_id": str(user_msg.id),
            "context": merged_context,
            "active_context": active_context,
            "suggestions": self._suggestions(ctx, intent_kind, state=state),
            "synthesis_fallback": synthesis_fallback,
            "latency_ms": latency_ms,
            "research": research_meta,
            "research_trace": research_trace.to_dict() if self._expose_diagnostics() else {
                "trace_id": research_trace.trace_id,
                "investigating": research_trace.investigating,
                "duration_ms": research_trace.duration_ms,
            },
            "research_audit": (
                {
                    "question": content,
                    "kind": (research_meta or {}).get("question_kind") if isinstance(research_meta, dict) else None,
                    "plan": (research_meta or {}).get("plan") if isinstance(research_meta, dict) else None,
                    "tools": [t.get("tool") for t in tool_trace if isinstance(t, dict)],
                    "duration_ms": latency_ms,
                    "confidence": (
                        (research_meta or {}).get("confidence")
                        if isinstance(research_meta, dict)
                        else None
                    ),
                    "errors": [
                        t.get("error_code") or t.get("status")
                        for t in tool_trace
                        if isinstance(t, dict) and t.get("status") not in {"success", "skipped_duplicate"}
                    ],
                }
                if research_meta
                else None
            ),
            "runtime_trace": runtime_trace,
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

    def _tool_enum(self, tool: str | None) -> LotteryToolName:
        if not tool:
            raise ValueError("tool required")
        return LotteryToolName(tool)

    def _normalize_tool_params(
        self, tool: str | None, params: dict[str, Any], state: ConversationState
    ) -> dict[str, Any]:
        out = dict(params or {})
        if tool in {
            LotteryToolName.GET_TOP_NUMBERS.value,
            LotteryToolName.GET_BOTTOM_NUMBERS.value,
            LotteryToolName.CALCULATE_FREQUENCIES.value,
        }:
            if not out.get("from_date") or not out.get("to_date"):
                from datetime import date, timedelta

                n = int(out.get("window_draws") or state.draw_count_context or 30)
                to_d = date.today()
                from_d = to_d - timedelta(days=max(n, 7))
                out.setdefault("from_date", from_d)
                out.setdefault("to_date", to_d)
                out.setdefault("limit", out.get("limit") or 10)
        if tool == LotteryToolName.GET_HOT_COLD.value:
            out.setdefault("window_draws", state.draw_count_context or 30)
        if tool == LotteryToolName.ANALYZE_NUMERIC_RELATIONS.value:
            if not out.get("lotteries") and state.active_lotteries:
                out["lotteries"] = list(state.active_lotteries)
            if out.get("observed_number") is None and out.get("number") is not None:
                out["observed_number"] = int(str(out["number"]).lstrip("0") or "0")
            # Never invent occurrence limit here — intent/UI must be explicit
        return out

    async def _execute_multi_last_occurrence(
        self,
        executor: LotteryToolExecutor,
        understanding,
        plan,
        ctx: LotterySessionContext,
    ) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
        from app.lottery.ai.compound_occurrence import position_label

        params = dict(understanding.params or {})
        multi_queries = params.get("multi_queries")
        tool_trace: list[dict[str, Any]] = []

        async def _list_ai_lotteries() -> list[str]:
            listed = await executor.execute(
                LotteryToolName.LIST_LOTTERIES,
                {"limit": 50, "searchable_only": True},
                structured_type="lottery_result",
                session_context=ctx.to_store(),
            )
            tool_trace.append(
                {
                    "tool": listed.tool,
                    "status": listed.status,
                    "duration_ms": listed.duration_ms,
                    "error_code": listed.error_code,
                }
            )
            items = []
            if isinstance(listed.data, dict):
                items = listed.data.get("items") or listed.data.get("lotteries") or []
            elif isinstance(listed.data, list):
                items = listed.data
            names: list[str] = []
            for item in items:
                name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
                if name:
                    names.append(str(name))
            return list(dict.fromkeys(names))

        def _exclude_match(name: str, excluded: list[str]) -> bool:
            nl = name.lower()
            for ex in excluded:
                el = (ex or "").lower()
                if not el:
                    continue
                if el in nl or nl in el or el.replace("quiniela ", "") in nl:
                    return True
            return False

        async def _last_for(lot: str, number: str, position: int | None) -> dict[str, Any]:
            call_params: dict[str, Any] = {"lottery": lot, "number": number}
            if position is not None:
                call_params["position"] = int(position)
            result = await executor.execute(
                LotteryToolName.GET_LAST_OCCURRENCE,
                call_params,
                structured_type="lottery_result",
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
            d = None
            pos = None
            result_nums = None
            total = None
            resolved_name = lot
            if result.status == "success" and isinstance(result.data, dict):
                items = result.data.get("occurrences") or result.data.get("items") or []
                meta = result.data.get("meta") or {}
                resolved = meta.get("resolved_lottery") or {}
                resolved_name = resolved.get("name") or lot
                total = (result.data.get("pagination") or {}).get("total") or result.data.get("total")
                if items:
                    first = items[0]
                    d = first.get("draw_date") if isinstance(first, dict) else getattr(first, "draw_date", None)
                    pos = (
                        first.get("position_label") or first.get("position")
                        if isinstance(first, dict)
                        else getattr(first, "position_label", None) or getattr(first, "position", None)
                    )
                    # Enrich with full draw when date known
                    if d:
                        try:
                            date_s = d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]
                            by_date = await executor.execute(
                                LotteryToolName.GET_RESULT_BY_DATE,
                                {"lottery": lot, "date": date_s},
                                structured_type="lottery_result",
                                session_context=ctx.to_store(),
                            )
                            tool_trace.append(
                                {
                                    "tool": by_date.tool,
                                    "status": by_date.status,
                                    "duration_ms": by_date.duration_ms,
                                    "error_code": by_date.error_code,
                                }
                            )
                            if by_date.status == "success" and isinstance(by_date.data, dict):
                                draws = by_date.data.get("draws") or []
                                if draws:
                                    nums = draws[0].get("numbers") or []
                                    result_nums = " · ".join(
                                        str(n.get("number_raw") or n.get("number_value") or "")
                                        for n in nums
                                        if n
                                    )
                        except Exception:  # noqa: BLE001
                            pass
            return {
                "lottery": resolved_name,
                "number": number,
                "last_date": str(d)[:10] if d else None,
                "position": pos,
                "position_filter": position,
                "result": result_nums,
                "found": bool(d),
                "draws_reviewed": total,
            }

        # --- Compound independent subqueries ---
        if isinstance(multi_queries, list) and multi_queries:
            sections: list[dict[str, Any]] = []
            all_ai: list[str] | None = None
            lines: list[str] = ["RESPUESTA", ""]
            for q in multi_queries:
                if not isinstance(q, dict) or not q.get("number"):
                    continue
                number = str(q["number"])
                position = q.get("position")
                scope = q.get("lotteries_scope") or "named"
                lots = list(q.get("lotteries") or [])
                excluded = list(q.get("excluded_lotteries") or [])
                if scope == "all_except_previous":
                    if all_ai is None:
                        all_ai = await _list_ai_lotteries()
                    lots = [n for n in all_ai if not _exclude_match(n, excluded)]
                elif scope == "defaults_or_clarify" and not lots:
                    lots = list(understanding.lotteries or [])[:1]

                rows: list[dict[str, Any]] = []
                for lot in lots[:40]:
                    rows.append(await _last_for(lot, number, position))
                rows_sorted = sorted(rows, key=lambda r: r["last_date"] or "", reverse=True)
                found = [r for r in rows_sorted if r["found"]]
                truncated = False
                display = found
                if len(found) > 5 and scope == "all_except_previous":
                    display = found[:5]
                    truncated = True

                pos_txt = position_label(position if position is not None else None)
                if scope == "all_except_previous":
                    title_lot = "otras loterías"
                    if excluded:
                        title_lot = f"otras loterías (excepto {', '.join(excluded)})"
                elif lots:
                    title_lot = lots[0] if len(lots) == 1 else f"{len(lots)} loterías"
                else:
                    title_lot = "loterías consultadas"

                lines.append(f"**{number} en {title_lot}, {pos_txt.lower()}**")
                lines.append("")
                if len(lots) == 1 and found:
                    r0 = found[0]
                    lines.append(f"- Última aparición: {r0['last_date']}")
                    if r0.get("result"):
                        lines.append(f"- Resultado completo: {r0['result']}")
                    if r0.get("draws_reviewed") is not None:
                        lines.append(f"- Sorteos revisados: {r0['draws_reviewed']}")
                elif found:
                    lines.append("| Lotería | Última aparición | Resultado |")
                    lines.append("|---|---:|---|")
                    for r in display:
                        lines.append(
                            f"| {r['lottery']} | {r['last_date']} | {r.get('result') or '—'} |"
                        )
                    if truncated:
                        lines.append("")
                        lines.append(
                            f"Mostrando las 5 apariciones más recientes de {len(found)} loterías con datos. "
                            "Di «Ver todas» si quieres el listado completo."
                        )
                    if found:
                        top = found[0]
                        lines.append("")
                        lines.append(
                            f"La aparición más reciente del {number} fuera de "
                            f"{', '.join(excluded) or 'las mencionadas'} fue en "
                            f"**{top['lottery']}** el **{top['last_date']}**."
                        )
                else:
                    lines.append(f"- No encontré apariciones del {number} con ese criterio.")
                lines.append("")
                sections.append(
                    {
                        "number": number,
                        "lotteries_scope": scope,
                        "excluded_lotteries": excluded,
                        "position": position,
                        "position_label": pos_txt,
                        "rows": rows_sorted,
                        "display_rows": display,
                        "truncated": truncated,
                    }
                )

            template = "\n".join(lines).strip()
            structured = {
                "type": "lottery_comparison",
                "data": {
                    "intent": "multi_last_occurrence",
                    "sections": sections,
                    "rows": [
                        r
                        for s in sections
                        for r in (s.get("display_rows") or s.get("rows") or [])
                    ],
                },
            }
            return structured, template, tool_trace

        # --- Legacy: one number across many lotteries ---
        number = (
            (understanding.numbers[0] if understanding.numbers else None)
            or params.get("number")
        )
        position = params.get("position")
        rows = []
        lotteries = list(understanding.lotteries or [])
        if not lotteries and understanding.scope == "all":
            lotteries = (await _list_ai_lotteries())[:8]

        for lot in lotteries[:8]:
            rows.append(await _last_for(lot, str(number), position))

        rows_sorted = sorted(rows, key=lambda r: r["last_date"] or "", reverse=True)
        found = [r for r in rows_sorted if r["found"]]
        missing = [r["lottery"] for r in rows_sorted if not r["found"]]
        pos_txt = position_label(position if position is not None else None)
        lines = [f"Comparación de la última aparición del {number} ({pos_txt.lower()}):"]
        for r in found:
            bit = f"• {r['lottery']}: {r['last_date']}"
            if r.get("result"):
                bit += f" — {r['result']}"
            lines.append(bit)
        if missing:
            lines.append(f"Sin datos para: {', '.join(missing)}.")
        template = "\n".join(lines)
        structured = {
            "type": "lottery_comparison",
            "data": {"rows": rows_sorted, "missing": missing, "number": number, "position": position},
        }
        return structured, template, tool_trace

    async def _execute_post_occurrence_window(
        self,
        executor: LotteryToolExecutor,
        understanding,
        ctx: LotterySessionContext,
    ) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
        """Per-lottery calendar/draw windows after remembered occurrence dates."""
        from datetime import date as date_cls, timedelta

        params = dict(understanding.params or {})
        lotteries = list(params.get("lotteries") or understanding.lotteries or [])
        per_dates = dict(params.get("per_lottery_dates") or understanding.per_lottery_dates or {})
        number = params.get("number") or (
            understanding.numbers[0] if understanding.numbers else None
        )
        unit = params.get("unit") or ("days" if understanding.calendar_days else "draws")
        count = int(params.get("count") or understanding.calendar_days or understanding.draw_count or 7)
        direction = params.get("direction") or "after"
        tool_trace: list[dict[str, Any]] = []
        sections: list[dict[str, Any]] = []

        for lot in lotteries[:8]:
            raw = per_dates.get(lot)
            if not raw:
                sections.append(
                    {
                        "lottery": lot,
                        "found_base": False,
                        "message": "Sin fecha base de aparición previa.",
                        "draws": [],
                    }
                )
                continue
            try:
                base = date_cls.fromisoformat(str(raw)[:10])
            except ValueError:
                sections.append(
                    {
                        "lottery": lot,
                        "found_base": False,
                        "message": f"Fecha base inválida: {raw}",
                        "draws": [],
                    }
                )
                continue

            if unit == "days":
                if direction == "before":
                    start, end = base - timedelta(days=count), base - timedelta(days=1)
                else:
                    start, end = base + timedelta(days=1), base + timedelta(days=count)
                result = await executor.execute(
                    LotteryToolName.GET_FOLLOWING_DAYS
                    if direction == "after"
                    else LotteryToolName.GET_PREVIOUS_DAYS,
                    {
                        "lottery": lot,
                        "date": base,
                        "days": count,
                        "include_base_date": False,
                    },
                    structured_type="lottery_range",
                    session_context=ctx.to_store(),
                )
            else:
                start = end = base
                result = await executor.execute(
                    LotteryToolName.GET_FOLLOWING_DRAWS
                    if direction == "after"
                    else LotteryToolName.GET_PREVIOUS_DRAWS,
                    {
                        "lottery": lot,
                        "date": base,
                        "count": count,
                        "include_base_date": False,
                    },
                    structured_type="lottery_range",
                    session_context=ctx.to_store(),
                )
            tool_trace.append(
                {
                    "tool": result.tool,
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "error_code": result.error_code,
                    "lottery": lot,
                }
            )
            draws = []
            if result.status == "success" and isinstance(result.data, dict):
                draws = result.data.get("draws") or result.data.get("items") or []
                if result.summary_for_context:
                    if result.summary_for_context.get("calendar_from"):
                        start = result.summary_for_context["calendar_from"]
                    if result.summary_for_context.get("calendar_to"):
                        end = result.summary_for_context["calendar_to"]
            # Collect numbers for insights
            nums: list[str] = []
            for d in draws:
                for n in (d.get("numbers") if isinstance(d, dict) else []) or []:
                    if isinstance(n, dict):
                        nums.append(str(n.get("number_raw") or n.get("number_value") or ""))
            reappeared = bool(number and str(number) in nums)
            sections.append(
                {
                    "lottery": lot,
                    "found_base": True,
                    "base_date": base.isoformat(),
                    "period_from": str(start)[:10],
                    "period_to": str(end)[:10],
                    "unit": unit,
                    "count": count,
                    "draws": draws[:40],
                    "numbers_flat": [x for x in nums if x],
                    "reappeared": reappeared,
                    "draw_count": len(draws),
                }
            )

        # Cross insights
        all_nums = [n for s in sections for n in s.get("numbers_flat") or []]
        freq: dict[str, int] = {}
        for n in all_nums:
            freq[n] = freq.get(n, 0) + 1
        repeated = sorted(
            [{"number": k, "count": v} for k, v in freq.items() if v > 1],
            key=lambda x: -x["count"],
        )[:10]
        top = sorted(freq.items(), key=lambda x: -x[1])[:5]
        lines = [
            f"Números en los {count} {'días calendario' if unit == 'days' else 'sorteos'} "
            f"{'anteriores' if direction == 'before' else 'posteriores'} "
            f"(fecha base = última aparición del {number or 'número'} por lotería):",
            "",
        ]
        focus = params.get("focus")
        if focus == "reappearance" and number:
            re_lots = [s["lottery"] for s in sections if s.get("reappeared")]
            if re_lots:
                lines.insert(
                    0,
                    f"El **{number}** se repitió en: {', '.join(re_lots)}.\n",
                )
            else:
                lines.insert(
                    0,
                    f"El **{number}** **no** se repitió en la ventana analizada "
                    f"({', '.join(lotteries) or 'loterías activas'}).\n",
                )
        for s in sections:
            lines.append(f"**{s['lottery']}**")
            if not s.get("found_base"):
                lines.append(f"- {s.get('message')}")
                lines.append("")
                continue
            lines.append(f"- Fecha base: {s['base_date']}")
            lines.append(f"- Período: {s['period_from']} → {s['period_to']}")
            lines.append(f"- Sorteos en ventana: {s.get('draw_count', 0)}")
            if s.get("reappeared"):
                lines.append(f"- El {number} **reapareció** en esta ventana.")
            sample = s.get("numbers_flat") or []
            if sample:
                lines.append(f"- Números: {', '.join(sample[:24])}{'…' if len(sample) > 24 else ''}")
            lines.append("")
        if repeated:
            lines.append("**Repeticiones entre loterías / ventana:**")
            for r in repeated[:8]:
                lines.append(f"- {r['number']}: {r['count']} veces")
            lines.append("")
        if top:
            lines.append(
                "**Más frecuentes en la ventana:** "
                + ", ".join(f"{n} ({c})" for n, c in top)
            )
            lines.append("")
        lines.append(
            "Nota: cada lotería usa su propia fecha base; los períodos no son necesariamente el mismo calendario."
        )
        template = "\n".join(lines)
        structured = {
            "type": "lottery_comparison",
            "tool": "lottery_analyze_post_occurrence_window",
            "query": {
                "number": number,
                "lotteries": lotteries,
                "unit": unit,
                "count": count,
                "direction": direction,
            },
            "data": {
                "sections": sections,
                "repeated": repeated,
                "top_numbers": [{"number": n, "count": c} for n, c in top],
                "metric": f"{count}_{unit}_{direction}_occurrence_window",
                "limitations": [
                    "Ventana descriptiva histórica; no predice resultados futuros.",
                    "Fechas base distintas por lotería.",
                ],
            },
        }
        return structured, template, tool_trace

    async def _execute_plan(
        self,
        executor: LotteryToolExecutor,
        plan,
        ctx: LotterySessionContext,
        understanding,
    ) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
        """Execute bounded multi-step plan; keep last successful analytical result."""
        tool_trace: list[dict[str, Any]] = []
        last_structured: dict[str, Any] | None = None
        last_template = "Consulta completada."
        lotteries_from_list: list[str] = []
        for step in plan.steps:
            params = dict(step.params or {})
            # Inject lotteries discovered earlier
            if (
                step.tool == LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value
                and not params.get("lotteries")
                and lotteries_from_list
            ):
                params["lotteries"] = lotteries_from_list[:8]
            try:
                tool_enum = LotteryToolName(step.tool)
            except ValueError:
                tool_trace.append(
                    {"tool": step.tool, "status": "error", "duration_ms": 0, "error_code": "UNKNOWN_TOOL"}
                )
                continue
            result = await executor.execute(
                tool_enum,
                self._normalize_tool_params(step.tool, params, ConversationState()),
                structured_type="lottery_result",
                session_context=ctx.to_store(),
            )
            tool_trace.append(
                {
                    "tool": result.tool,
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "error_code": result.error_code,
                    "purpose": step.purpose,
                }
            )
            if result.status != "success":
                continue
            if step.tool == LotteryToolName.LIST_LOTTERIES.value and isinstance(result.data, dict):
                items = result.data.get("items") or result.data.get("lotteries") or []
                for item in items:
                    name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
                    if name:
                        lotteries_from_list.append(str(name))
                continue
            if step.tool == LotteryToolName.RESOLVE_LOTTERY.value:
                continue
            last_structured, last_template = self._build_structured(result, params)
        if last_structured is None:
            last_structured = {
                "type": "lottery_error",
                "warnings": [{"code": "PLAN_PARTIAL", "message": "No se pudieron completar todos los pasos."}],
            }
            last_template = "No pude completar el análisis con los datos disponibles."
        last_structured["plan"] = [s.model_dump() for s in plan.steps]
        last_structured["tool_trace_count"] = len(tool_trace)
        return last_structured, last_template, tool_trace

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
            total = (data.get("pagination") or {}).get("total") or data.get("total")
            meta = data.get("meta") or {}
            resolved = meta.get("resolved_lottery") or {}
            if not items:
                return f"No encontré apariciones del {number} en {lot}."
            first = items[0]
            d = getattr(first, "draw_date", None) or (
                first.get("draw_date") if isinstance(first, dict) else None
            )
            pos = getattr(first, "position_label", None) or (
                first.get("position_label") if isinstance(first, dict) else None
            ) or getattr(first, "position", None) or (
                first.get("position") if isinstance(first, dict) else None
            )
            first_d = resolved.get("first_draw_date") or meta.get("first_draw_date")
            last_d = resolved.get("last_draw_date") or meta.get("last_draw_date")
            draw_count = resolved.get("draw_count") or meta.get("draw_count")
            pos_bit = f", en la posición {pos}" if pos is not None else ""
            sample = ""
            if draw_count or (first_d and last_d):
                sample = (
                    f" Analicé {draw_count or 'los'} sorteos disponibles"
                    + (f" entre {first_d} y {last_d}" if first_d and last_d else "")
                    + "."
                )
            elif total is not None:
                sample = f" Hay {total} aparición(es) históricas del {number} en el historial."
            return (
                f"En {lot}, el {number} apareció por última vez el {d}{pos_bit}.{sample}"
            )

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
            names = [
                f"{x.get('name')} (source {x.get('source_id')})"
                for x in (data.get("sync_lotteries") or [])
                if isinstance(x, dict)
            ]
            lista = ", ".join(names) if names else "ninguna"
            base = (
                f"Sincronización: global={data.get('global_sync_enabled')}, "
                f"auto-write={data.get('global_auto_write_enabled')}, "
                f"modo={data.get('scheduler_mode')}, "
                f"worker_standalone={data.get('worker_standalone')}. "
                f"Loterías con sync habilitado ({data.get('lotteries_sync_enabled')}): {lista}. "
                "Solo esas pueden recibir escritura automática."
            )
            if params.get("explain_auto_write_trio"):
                return (
                    f"{base} En la operación actual de Lottery 3.0 solo se sincronizan "
                    "automáticamente tres fuentes (Leidsa, Loteka y Lotería Nacional / Nacional Noche) "
                    "porque así está configurado el auto-write; el resto del catálogo puede consultarse "
                    "históricamente pero no se escribe en cada corrida de sync. "
                    "Nacional Día sigue fuera de sync definitivo."
                )
            return base

        if tool == "lottery_compare_number_periods" and isinstance(data, dict):
            a = data.get("period_a") or {}
            b = data.get("period_b") or {}
            lot = data.get("lottery")
            number = data.get("number")
            higher = data.get("higher_relative_frequency")
            winner = a.get("label") if higher == "period_a" else (
                b.get("label") if higher == "period_b" else "ninguno (empate)"
            )
            return (
                f"En {lot}, el {number}: "
                f"{a.get('label')} → {a.get('occurrences')} apariciones en {a.get('draws')} sorteos "
                f"({a.get('relative_frequency_pct')}%). "
                f"{b.get('label')} → {b.get('occurrences')} apariciones en {b.get('draws')} sorteos "
                f"({b.get('relative_frequency_pct')}%). "
                f"Mayor frecuencia relativa: {winner}. "
                f"Métrica: {data.get('metric')}. {data.get('definition')} "
                f"Limitaciones: {'; '.join(data.get('limitations') or [])}."
            )

        if tool == "lottery_compare_number_across_lotteries" and isinstance(data, dict):
            rows = data.get("rows") or []
            lines = [f"Última aparición del {data.get('number')} por lotería:"]
            for r in rows:
                if r.get("found"):
                    lines.append(
                        f"• {r.get('lottery')}: {r.get('last_date')} "
                        f"(×{r.get('occurrences')} históricas)"
                    )
                else:
                    lines.append(f"• {r.get('lottery')}: sin registros")
            lines.append(f"Métrica: {data.get('metric')}.")
            return "\n".join(lines)

        if tool == "lottery_get_lottery_summary" and isinstance(data, dict):
            return (
                f"Resumen de {data.get('lottery')}: {data.get('draw_count')} sorteos, "
                f"desde {data.get('first_draw_date')} hasta {data.get('last_draw_date')}. "
                f"Sync={data.get('sync_enabled')}, auto-write={data.get('auto_write_enabled')}. "
                f"Métrica: {data.get('metric')}."
            )

        if tool == "lottery_get_latest_available_date" and isinstance(data, dict):
            if data.get("lottery"):
                return (
                    f"La fecha más reciente disponible en {data.get('lottery')} es "
                    f"{data.get('last_draw_date')} ({data.get('draw_count')} sorteos)."
                )
            top = data.get("most_recent") or {}
            return (
                f"La lotería más actualizada en catálogo es {top.get('lottery')} "
                f"hasta {top.get('last_draw_date')}."
            )

        if tool == "lottery_explain_analysis_method" and isinstance(data, dict):
            return str(data.get("definition") or "Análisis histórico descriptivo.")

        if tool == "lottery_analyze_numeric_relations" and isinstance(data, dict):
            from app.lottery.numeric_relations.chat_narrative import format_numeric_relations_reply

            return format_numeric_relations_reply(data)

        if (
            tool == "lottery_get_number_occurrences"
            and isinstance(data, dict)
            and (data.get("relation") == "same_day" or params.get("relation") == "same_day")
        ):
            from app.lottery.ai.same_day_coincidence import (
                format_coincidence_narrative,
                summarize_coincidences,
            )

            nums = list(data.get("numbers") or params.get("numbers") or [])
            summary = summarize_coincidences(
                data,
                numbers=nums,
                preferred_position=int(params.get("preferred_position") or 1),
                position_filter=params.get("position"),
            )
            if data.get("total_all_positions") is not None:
                summary["total_all_positions"] = data.get("total_all_positions")
            # Persist coincidence anchor for "qué pasó después" continuity (caller may read via params side-channel)
            if summary.get("last") and isinstance(summary["last"], dict):
                params["_last_coincidence_date"] = str(
                    summary["last"].get("date") or summary["last"].get("draw_date") or ""
                )[:10]
                params["_coincidence_total"] = int(summary.get("total") or 0)
                params["_coincidence_first_related"] = int(summary.get("first_related") or 0)
                params["_coincidence_other_only"] = int(summary.get("other_only") or 0)
            return format_coincidence_narrative(
                summary,
                report_mode=bool(params.get("report_mode")),
                want_last_only=bool(params.get("want_last_only")),
            )

        if tool == "lottery_run_complete_analysis" and isinstance(data, dict):
            primary = (data.get("primary") or {}).get("number")
            obs = data.get("observed_number")
            hist = data.get("historical") or {}
            parts = []
            rival = data.get("rival_comparison") or {}
            if rival.get("texto"):
                parts.append(str(rival["texto"]))
            elif primary is not None:
                parts.append(
                    f"Para el {obs}, el resultado principal es el {primary}."
                )
            if data.get("conclusion") and (
                not rival.get("texto") or str(data.get("conclusion")) != str(rival.get("texto"))
            ):
                # Avoid duplicating the same rival sentence
                conc = str(data["conclusion"])
                if not parts or conc not in parts[0]:
                    parts.append(conc)
            t1 = data.get("table1_sources") or []
            t2 = data.get("table2_confirmers") or []
            same = data.get("same_day_cross") or []
            if t1 or t2 or same:
                bits = []
                if t1:
                    bits.append(f"Tabla 1 relaciona {obs} con {primary}" if primary is not None else f"Tabla 1: {', '.join(str(x) for x in t1)}")
                if t2:
                    bits.append(f"Tabla 2 confirma vía {', '.join(str(x) for x in t2)}")
                if same:
                    s0 = same[0]
                    bits.append(
                        f"Cruce del mismo día: {s0.get('origen')} → {s0.get('companero')} "
                        f"confirmado por {s0.get('confirmador')} "
                        f"({s0.get('loteria_origen')} / {s0.get('loteria_confirmador')})"
                    )
                parts.append("Evidencia: " + "; ".join(bits) + ".")
            if hist.get("resumen"):
                parts.append(str(hist["resumen"]))
            elif hist.get("casos_equivalentes") is not None:
                parts.append(
                    f"Histórico: {hist.get('casos_equivalentes')} casos equivalentes, "
                    f"{hist.get('aciertos_exactos')} aciertos exactos "
                    f"(D+1={hist.get('d1')}, D+3={hist.get('d3')}, D+7={hist.get('d7')})."
                )
            if data.get("comparison") and not rival.get("texto"):
                parts.append(str(data["comparison"]))
            if data.get("warning"):
                parts.append(str(data["warning"]))
            return " ".join(parts) if parts else "Análisis completo disponible."

        if tool == "lottery_get_expected_vs_received" and isinstance(data, dict):
            return (
                f"Hoy ({data.get('local_today')}): esperadas {data.get('expected_sync_enabled')} "
                f"loterías con sync; recibidas {data.get('received_today')}; "
                f"pendientes {data.get('pending')}. "
                f"Definición: {data.get('definition')}."
            )

        if tool == "lottery_get_missing_today" and isinstance(data, dict):
            missing = data.get("missing") or []
            names = [m.get("name") for m in missing if isinstance(m, dict)]
            return (
                f"Hoy local ({data.get('local_today')}) faltan resultados en {data.get('count')} "
                f"lotería(s) con sync habilitado: {', '.join(str(n) for n in names) or 'ninguna'}. "
                f"{data.get('explanation') or ''}"
            )

        if tool == "lottery_get_sync_windows" and isinstance(data, dict):
            due = data.get("sync_enabled_due") or []
            bits = []
            for d in due[:5]:
                bits.append(
                    f"source {d.get('source_id')}: fase {d.get('phase')}, "
                    f"cada {d.get('interval_minutes')} min, próximo sorteo {d.get('next_draw_at')}"
                )
            phases = data.get("phases") or {}
            return (
                f"Ventanas de sync (TZ {data.get('timezone')}): fases={phases}. "
                + ("Próximas: " + "; ".join(bits) if bits else "Sin loterías sync en ventana activa.")
            )

        if tool == "lottery_get_source_health" and isinstance(data, dict):
            items = data.get("sources") or []
            if not items:
                return "Aún no hay filas de health multi-fuente registradas (tabla lottery_sources)."
            bits = [
                f"{i.get('source_key')} ({i.get('role')}): {i.get('health_status')}/{i.get('circuit_state')}"
                for i in items[:12]
                if isinstance(i, dict)
            ]
            return "Salud de fuentes: " + "; ".join(bits) + "."

        if tool == "lottery_get_hot_cold" and isinstance(data, dict):
            if data.get("focus") == "definition" or not data.get("window_draws"):
                defs = data.get("definitions") or {}
                if params.get("report_params"):
                    return (
                        f"Parámetros del análisis descriptivo: lotería={data.get('lottery') or params.get('lottery') or 'Leidsa'}, "
                        f"ventana={params.get('window_draws') or 30} sorteos, "
                        "métrica caliente=frecuencia relativa; "
                        "frío por frecuencia=baja frecuencia relativa; "
                        "atrasado=días sin aparecer. "
                        "Es análisis histórico, no predicción."
                    )
                return (
                    "En JAIOS usamos estas definiciones explícitas (análisis histórico, no predicción):\n"
                    f"• Caliente: {defs.get('hot') or data.get('definition')}\n"
                    f"• Frío por frecuencia: {defs.get('cold_frequency') or 'baja frecuencia relativa en la muestra.'}\n"
                    f"• Frío/atrasado por intervalo: {defs.get('cold_interval') or 'días sin aparecer.'}\n"
                    "No mezclamos automáticamente «frío por frecuencia» con «atrasado por intervalo»; "
                    "indicamos cuál métrica se usa en cada respuesta."
                )
            lot = data.get("lottery") or "la lotería"
            hot = ", ".join(
                f"{h.get('number')} ({h.get('relative_frequency_pct', h.get('count'))}"
                f"{'%' if h.get('relative_frequency_pct') is not None else '×'})"
                for h in (data.get("hot") or [])[:10]
            )
            cold_i = ", ".join(
                f"{c.get('number')} ({c.get('days_since')}d)" for c in (data.get("cold") or [])[:10]
            )
            cold_f = ", ".join(
                f"{c.get('number')} ({c.get('relative_frequency_pct')}%)"
                for c in (data.get("cold_by_frequency") or [])[:10]
            )
            parts = [
                f"Análisis descriptivo de {lot}: muestra={data.get('window_draws')} sorteos "
                f"({data.get('sample_numbers')} números), hasta {data.get('as_of')}. "
                f"Métrica: {data.get('metric_used')}."
            ]
            if hot:
                parts.append(f"Calientes (frecuencia relativa): {hot}.")
            if cold_f:
                parts.append(f"Fríos por frecuencia: {cold_f}.")
            if cold_i:
                parts.append(f"Atrasados/fríos por intervalo: {cold_i}.")
            parts.append(str(data.get("definition") or "No es predicción ni recomendación de apuestas."))
            return " ".join(parts)

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

    async def _recent_dialogue(
        self, session_id: uuid.UUID, *, limit: int = 12
    ) -> list[dict[str, str]]:
        # Take the newest N messages (list_messages is ASC + offset from start).
        _, total = await self.list_messages(session_id, limit=1, offset=0)
        offset = max(0, int(total or 0) - limit)
        rows, _ = await self.list_messages(session_id, limit=limit, offset=offset)
        out: list[dict[str, str]] = []
        for m in rows:
            role = "user" if m.role == "user" else "assistant"
            content = (m.content or "").strip()
            if content:
                out.append({"role": role, "content": content[:800]})
        return out

    async def _analyst_runtime_config(self):
        """Load Analista IA research config from Admin agent payload (safe defaults)."""
        try:
            from app.services.lottery_ai_admin_service import LotteryAiAdminService

            svc = LotteryAiAdminService(
                self.db, tenant_id=self.tenant_id, user_id=self.user_id
            )
            await svc.ensure_seeded()
            cfg = await svc.get_active_config()
            payload = (cfg.payload if cfg else None) or {}
            return load_analyst_config_from_payload(payload)
        except Exception:  # noqa: BLE001
            return load_analyst_config_from_payload(None)


    async def _synthesize(
        self,
        *,
        question: str,
        template: str,
        facts: dict[str, Any],
        context: dict[str, Any],
        recent_messages: list[dict[str, str]] | None = None,
        mode: str = "tool",
        max_tokens: int = 1200,
    ) -> tuple[str, bool, str | None, str | None]:
        """Síntesis: LLMRouter → Hermes/ModelArts → plantilla natural (sin mensajes internos)."""
        if not settings.assistant_synthesis_enabled:
            return template, True, None, "local_template"

        token_budget = max(200, min(int(max_tokens or 1200), 4000))

        # Strip bulky internals from context for the model
        ctx_public = {
            k: context.get(k)
            for k in (
                "last_lottery",
                "last_numbers",
                "base_date",
                "conversation_summary",
                "current_primary_candidate",
            )
            if context.get(k) is not None
        }
        v4 = context.get("conversation_v4") if isinstance(context.get("conversation_v4"), dict) else {}
        if v4:
            ctx_public["active_numbers"] = v4.get("active_numbers")
            ctx_public["active_lotteries"] = v4.get("active_lotteries")
            ctx_public["primary"] = v4.get("current_primary_candidate")
            ctx_public["summary"] = v4.get("conversation_summary")
            la = v4.get("last_analysis") or {}
            if la:
                ctx_public["last_analysis"] = {
                    "observed": la.get("observed"),
                    "primary": la.get("primary"),
                    "confirmer": la.get("confirmer"),
                    "date": la.get("date"),
                }

        # Orden oficial V6: guardrails → Analista → contexto → intención → tools → instrucción → usuario
        raw_messages = build_analyst_llm_messages(
            question=question,
            template=template,
            facts=facts,
            context=ctx_public,
            intent=mode,
            mode=mode,
            recent_messages=recent_messages,
        )
        messages = [
            LLMMessage(role=m["role"], content=m["content"]) for m in raw_messages
        ]

        # 1) LLMRouter con reintentos
        provider = None
        provider_name: str | None = None
        if settings.assistant_synthesis_provider:
            try:
                provider = LLMProvider(settings.assistant_synthesis_provider)
                provider_name = provider.value
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
                        max_tokens=token_budget,
                    ),
                    tenant_id=self.tenant_id,
                )
                text = self._sanitize_user_facing((response.content or "").strip())
                if len(text) >= 20 and not self._looks_internal(text):
                    used = getattr(response, "provider", None)
                    used_s = used.value if hasattr(used, "value") else (str(used) if used else provider_name)
                    return text, False, getattr(response, "model", None), used_s
            except Exception as exc:  # noqa: BLE001 — fallback controlado
                last_err = exc
                await asyncio.sleep(0.35 * (attempt + 1))

        # 2) Hermes / ModelArts (credenciales ya usadas por JAIOS)
        hermes_text, hermes_model = await self._synthesize_via_hermes(
            messages, max_tokens=token_budget
        )
        if hermes_text:
            return hermes_text, False, hermes_model, "huawei_modelarts"

        # 3) Fallback natural: plantilla local (nunca mensajes internos)
        _ = last_err
        return template, True, None, "local_template"

    async def _synthesize_via_hermes(
        self, messages: list[LLMMessage], *, max_tokens: int = 1200
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
        token_budget = max(200, min(int(max_tokens or 1200), 4000))
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
                            "max_tokens": token_budget,
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

    def _suggestions(
        self,
        ctx: LotterySessionContext,
        kind: str,
        *,
        state: ConversationState | None = None,
    ) -> list[str]:
        out: list[str] = []
        if kind == "clarify":
            missing = list((state.pending_slots if state else None) or [])
            if "number" in missing:
                return ["Analiza el 35.", "Analiza el 39."]
            if "lottery" in missing:
                return ["En la Real.", "En Leidsa.", "En todas las loterías."]
            return ["Últimos 30 sorteos.", "En todas las loterías."]

        # Fase X.2 — contextual suggestions for active same-day pair
        if state and (
            state.active_relation == "same_day"
            or (len(state.active_numbers or []) >= 2 and state.active_pair)
        ):
            from app.lottery.ai.same_day_coincidence import coincidence_suggestions

            nums = list(state.active_numbers or state.active_pair or [])
            if len(nums) >= 2:
                return coincidence_suggestions(nums)[:6]

        la = dict((state.last_analysis if state else None) or ctx.last_analysis or {})
        obs = la.get("observed") or (ctx.last_numbers[0] if ctx.last_numbers else None)
        primary = la.get("primary") or (
            state.current_primary_candidate if state else None
        ) or ctx.current_primary_candidate
        alts = list(
            (state.current_alternatives if state else None)
            or []
        )
        date_s = la.get("date") or (
            str(state.active_date) if state and state.active_date else None
        ) or (str(ctx.base_date) if ctx.base_date else None)

        if primary is not None and obs is not None:
            rival = next((a for a in alts if int(a) != int(primary)), None)
            if rival is None and int(primary) != 7:
                rival = 7
            if rival is not None:
                out.append(f"Comparar {primary} con {rival}")
            out.append("Ver casos históricos")
            out.append("Explicar Tabla 1")
            if date_s:
                out.append(f"Ver resultados del {date_s}")
            out.append(f"¿Por qué el {primary}?")
            return out[:6]

        if ctx.base_date and ctx.last_lottery:
            out.append("Ver siete días siguientes.")
            out.append("Ver siete sorteos siguientes.")
            if ctx.last_numbers:
                out.append(f"Analiza el {ctx.last_numbers[0]}.")
            return out[:6]
        if ctx.last_numbers:
            if len(ctx.last_numbers) >= 2:
                from app.lottery.ai.same_day_coincidence import coincidence_suggestions

                return coincidence_suggestions(list(ctx.last_numbers))[:6]
            return [
                f"Analiza el {ctx.last_numbers[0]}.",
                "¿Cuántas veces ha salido?",
                "Ver últimos resultados",
            ]
        return ["Analiza el 35.", "¿Cuáles son los resultados de hoy?", "Ver loterías activas."]

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
