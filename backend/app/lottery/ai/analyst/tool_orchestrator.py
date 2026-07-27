"""Tool Orchestrator — execute research plans via authorized tools only."""

from __future__ import annotations

import time
from typing import Any

from app.lottery.ai.analyst.config import AnalystRuntimeConfig
from app.lottery.ai.analyst.guardrails import AnalystGuardrails
from app.lottery.ai.analyst.research_planner import ResearchPlan
from app.lottery.ai.analyst.research_trace import ResearchTrace
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.planner import PlanStep
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext, merge_context_after_tool
from app.services.lottery_tools import LotteryToolExecutor


class ToolOrchestrator:
    """Never invents data — only runs LotteryToolExecutor steps."""

    def __init__(
        self,
        executor: LotteryToolExecutor,
        config: AnalystRuntimeConfig,
        guardrails: AnalystGuardrails | None = None,
        trace: ResearchTrace | None = None,
    ):
        self.executor = executor
        self.config = config
        self.guardrails = guardrails or AnalystGuardrails()
        self.trace = trace

    async def run(
        self,
        plan: ResearchPlan,
        *,
        ctx: LotterySessionContext,
        state: ConversationState,
    ) -> tuple[
        dict[str, Any] | None,
        str,
        list[dict[str, Any]],
        LotterySessionContext,
        ConversationState,
        ResearchTrace | None,
    ]:
        tool_trace: list[dict[str, Any]] = []
        templates: list[str] = []
        structured: dict[str, Any] | None = None
        evidence_bundle: list[dict[str, Any]] = []
        working_ctx = ctx
        working_state = state
        trace = self.trace or ResearchTrace(
            investigating=bool(plan.is_research),
            research_mode=plan.mode,
            analysis_depth=self.config.analysis_depth,
        )
        trace.investigating = bool(plan.is_research)
        trace.research_mode = plan.mode
        trace.analysis_depth = self.config.analysis_depth
        trace.config_snapshot = {
            "max_tools": self.config.effective_max_tools(),
            "max_steps": self.config.effective_max_steps(),
            "timeout_seconds": self.config.timeout_seconds,
            "max_tokens": self.config.max_tokens,
            "research_mode": self.config.research_mode,
            "analysis_depth": self.config.analysis_depth,
        }

        limit = min(self.config.effective_max_tools(), self.config.effective_max_steps())
        steps = plan.steps[:limit]
        t0 = time.monotonic()

        for step in steps:
            if (time.monotonic() - t0) > self.config.timeout_seconds:
                tool_trace.append(
                    {
                        "tool": step.tool,
                        "status": "timeout_skipped",
                        "purpose": step.purpose,
                    }
                )
                trace.mark_step(tool=step.tool, purpose=step.purpose, status="timeout_skipped")
                break

            if not self.guardrails.allow_tool(step.tool):
                tool_trace.append(
                    {
                        "tool": step.tool,
                        "status": "blocked_by_guardrail",
                        "purpose": step.purpose,
                    }
                )
                trace.mark_step(tool=step.tool, purpose=step.purpose, status="blocked_by_guardrail")
                continue

            try:
                tool_enum = LotteryToolName(step.tool)
            except ValueError:
                tool_trace.append(
                    {
                        "tool": step.tool,
                        "status": "unknown_tool",
                        "purpose": step.purpose,
                    }
                )
                trace.mark_step(tool=step.tool, purpose=step.purpose, status="unknown_tool")
                continue

            params = self._normalize_params(step, working_state)
            result = await self.executor.execute(
                tool_enum,
                params,
                structured_type=self._structured_type(step.tool),
                session_context=working_ctx.to_store(),
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
            trace.mark_step(
                tool=result.tool,
                purpose=step.purpose,
                status=result.status,
                duration_ms=result.duration_ms,
                summary=result.summary_for_context if result.status == "success" else None,
            )

            if result.status != "success":
                continue

            working_ctx = merge_context_after_tool(
                working_ctx,
                tool=result.tool,
                params=params,
                result_summary=result.summary_for_context,
            )
            data = result.data if isinstance(result.data, dict) else {"payload": result.data}
            safe_data = self.guardrails.sanitize_tool_payload(data)
            evidence_bundle.append(
                {
                    "purpose": step.purpose,
                    "tool": result.tool,
                    "summary": result.summary_for_context or {},
                }
            )
            structured = {
                "type": result.structured_type or self._structured_type(step.tool),
                "data": safe_data,
                "research": {
                    "mode": plan.mode,
                    "status": plan.user_visible_status or "Estoy investigando…",
                    "investigating": True,
                    "steps_completed": [
                        t.get("purpose") for t in tool_trace if t.get("status") == "success"
                    ],
                    "evidence": evidence_bundle[-6:],
                },
            }
            summary = result.summary_for_context or {}
            primary = summary.get("primary")
            observed = summary.get("observed_number") or params.get("observed_number")
            if primary is not None:
                templates.append(
                    f"Conclusión: el número más fortalecido es {primary}."
                    + (f" Observado: {observed}." if observed is not None else "")
                )
            elif summary.get("count") is not None:
                templates.append(
                    f"Conclusión: encontré {summary.get('count')} apariciones "
                    f"para el número consultado."
                )
            elif summary.get("last_occurrence_date"):
                templates.append(
                    f"Conclusión: la última aparición registrada es {summary.get('last_occurrence_date')}."
                )
            elif step.purpose:
                templates.append(f"Consulté {step.purpose.replace('_', ' ')} con datos del motor.")

            if step.tool == LotteryToolName.RUN_COMPLETE_ANALYSIS.value:
                summary = result.summary_for_context or {}
                if summary.get("primary") is not None:
                    working_state.current_primary_candidate = int(summary["primary"])
                if params.get("observed_number") is not None:
                    working_state.active_numbers = [str(params["observed_number"]).zfill(2)]
                if params.get("confirmer") is not None:
                    working_state.active_pair = [
                        str(params.get("observed_number") or "").zfill(2),
                        str(params["confirmer"]).zfill(2),
                    ]

        template = "\n\n".join(t for t in templates if t).strip()
        if not template and evidence_bundle:
            template = (
                "Conclusión: consulté las herramientas autorizadas y organicé la evidencia disponible. "
                "Si falta algún dato, indícalo y continúo la investigación."
            )
        if not template:
            template = "No encontré suficiente evidencia con las herramientas disponibles."

        if structured and isinstance(structured.get("research"), dict):
            structured["research"]["trace_id"] = trace.trace_id
            structured["research"]["duration_ms"] = int((time.monotonic() - t0) * 1000)

        return structured, template, tool_trace, working_ctx, working_state, trace

    def _normalize_params(self, step: PlanStep, state: ConversationState) -> dict[str, Any]:
        params = dict(step.params or {})
        # Fill from memory when omitted
        if not params.get("number") and state.active_numbers:
            params.setdefault("number", state.active_numbers[0])
        if not params.get("observed_number") and state.active_numbers:
            try:
                params.setdefault("observed_number", int(state.active_numbers[0]))
            except (TypeError, ValueError):
                params.setdefault("observed_number", state.active_numbers[0])
        if not params.get("lottery") and state.active_lotteries:
            params.setdefault("lottery", state.active_lotteries[0])
        if not params.get("date") and state.active_date:
            params.setdefault("date", state.active_date)
        if not params.get("base_date") and state.date_context:
            params.setdefault("base_date", state.date_context)
        year = (state.active_filters or {}).get("year")
        if year and "year" not in params and "from_date" not in params:
            params["year"] = year
        return params

    @staticmethod
    def _structured_type(tool: str) -> str:
        if tool == LotteryToolName.RUN_COMPLETE_ANALYSIS.value:
            return "lottery_complete_analysis"
        if "historical" in tool or "candidate_response" in tool or "confirmer" in tool:
            return "lottery_historical"
        if "compare" in tool:
            return "lottery_comparison"
        return "lottery_result"
