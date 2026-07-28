"""Tool Orchestrator — execute research plans via authorized tools only."""

from __future__ import annotations

import time
from typing import Any

from app.lottery.ai.analyst.config import AnalystRuntimeConfig
from app.lottery.ai.analyst.evidence_engine import EvidenceEngine
from app.lottery.ai.analyst.guardrails import AnalystGuardrails
from app.lottery.ai.analyst.research_cache import get_research_cache
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
        self.cache = get_research_cache()

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
        seen_keys: set[str] = set()
        cache_hits = 0
        trace = self.trace or ResearchTrace(
            investigating=bool(plan.is_research),
            research_mode=plan.mode,
            analysis_depth=self.config.analysis_depth,
        )
        trace.investigating = bool(plan.is_research)
        trace.research_mode = plan.mode
        trace.analysis_depth = self.config.analysis_depth
        if plan.question_kind:
            trace.intent = plan.question_kind
        trace.config_snapshot = {
            "max_tools": self.config.effective_max_tools(),
            "max_steps": self.config.effective_max_steps(),
            "timeout_seconds": self.config.timeout_seconds,
            "max_tokens": self.config.max_tokens,
            "research_mode": self.config.research_mode,
            "analysis_depth": self.config.analysis_depth,
            "question_kind": plan.question_kind,
        }

        limit = min(self.config.effective_max_tools(), self.config.effective_max_steps())
        steps = plan.steps[:limit]
        t0 = time.monotonic()

        for step in steps:
            step_started = time.monotonic()
            if (time.monotonic() - t0) > self.config.timeout_seconds:
                tool_trace.append(
                    {
                        "tool": step.tool,
                        "status": "timeout_skipped",
                        "purpose": step.purpose,
                        "started_at": step_started,
                        "ended_at": time.monotonic(),
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
            # Skip duplicate identical steps within the same investigation
            dedupe_key = self.cache.make_key(step.tool, params)
            if dedupe_key in seen_keys:
                tool_trace.append(
                    {
                        "tool": step.tool,
                        "status": "skipped_duplicate",
                        "purpose": step.purpose,
                        "cached": True,
                    }
                )
                trace.mark_step(tool=step.tool, purpose=step.purpose, status="skipped_duplicate")
                continue
            seen_keys.add(dedupe_key)

            cached = self.cache.get(step.tool, params)
            if cached is not None:
                result = cached
                cache_hits += 1
                duration_ms = int((time.monotonic() - step_started) * 1000)
                tool_trace.append(
                    {
                        "tool": getattr(result, "tool", step.tool),
                        "status": getattr(result, "status", "success"),
                        "duration_ms": duration_ms,
                        "purpose": step.purpose,
                        "cached": True,
                        "started_at": step_started,
                        "ended_at": time.monotonic(),
                    }
                )
                trace.mark_step(
                    tool=step.tool,
                    purpose=step.purpose,
                    status="success",
                    duration_ms=duration_ms,
                    summary=getattr(result, "summary_for_context", None),
                )
            else:
                result = await self.executor.execute(
                    tool_enum,
                    params,
                    structured_type=self._structured_type(step.tool),
                    session_context=working_ctx.to_store(),
                )
                if result.status == "success":
                    self.cache.set(step.tool, params, result)
                tool_trace.append(
                    {
                        "tool": result.tool,
                        "status": result.status,
                        "duration_ms": result.duration_ms,
                        "error_code": result.error_code,
                        "purpose": step.purpose,
                        "cached": False,
                        "started_at": step_started,
                        "ended_at": time.monotonic(),
                    }
                )
                trace.mark_step(
                    tool=result.tool,
                    purpose=step.purpose,
                    status=result.status,
                    duration_ms=result.duration_ms,
                    summary=result.summary_for_context if result.status == "success" else None,
                )

            if getattr(result, "status", None) != "success":
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
                    "question_kind": plan.question_kind,
                    "steps_completed": [
                        t.get("purpose")
                        for t in tool_trace
                        if t.get("status") in {"success", "skipped_duplicate"} or t.get("cached")
                    ],
                    "evidence": evidence_bundle[-8:],
                },
            }
            summary = result.summary_for_context or {}
            primary = summary.get("primary")
            observed = summary.get("observed_number") or params.get("observed_number")
            from app.lottery.ai.turn_policy import position_label_es, purpose_label_es

            if primary is not None:
                templates.append(
                    f"El número más fortalecido reportado por el motor es {primary}."
                    + (f" Observado: {observed}." if observed is not None else "")
                )
            elif summary.get("semantics") == "same_day_coincidence":
                from app.lottery.ai.same_day_coincidence import (
                    format_coincidence_list,
                    format_coincidence_narrative,
                    summarize_coincidences,
                )

                nums = summary.get("numbers") or params.get("numbers") or []
                payload = result.data if isinstance(getattr(result, "data", None), dict) else {}
                items = []
                if isinstance(payload, dict):
                    items = (
                        payload.get("dates")
                        or payload.get("items")
                        or payload.get("coincidences")
                        or []
                    )
                if not items:
                    items = list(summary.get("items") or [])
                summ = summarize_coincidences(
                    {"items": items, "total": summary.get("total") or summary.get("count")},
                    numbers=[str(n) for n in nums[:2]],
                    preferred_position=int(params.get("preferred_position") or 1),
                    position_filter=params.get("position"),
                )
                list_mode = bool(params.get("list_mode") or summary.get("list_mode"))
                lim = params.get("limit") or summary.get("limit")
                if list_mode:
                    templates.append(
                        format_coincidence_list(
                            {**summ, "items": items, "limit": lim},
                            limit=lim,
                        )
                    )
                else:
                    bit = format_coincidence_narrative(
                        summ,
                        report_mode=bool(params.get("report_mode")),
                        want_last_only=bool(params.get("want_last_only")),
                    )
                    if bit:
                        templates.append(bit)
                    else:
                        total = summary.get("total")
                        if total is None:
                            total = summary.get("count")
                        last = summary.get("last_occurrence_date") or summary.get("last_date")
                        pair = (
                            " y ".join(str(n) for n in nums[:2])
                            if nums
                            else "los números consultados"
                        )
                        if total is not None and int(total) > 0:
                            bit2 = f"Encontré {total} coincidencia(s) el mismo día para {pair}."
                            if last:
                                bit2 += f" La más reciente fue el {last}."
                            templates.append(bit2)
                        else:
                            templates.append(
                                f"No encontré coincidencias el mismo día para {pair} "
                                "en el alcance consultado."
                            )
            elif summary.get("semantics") == "last_n_occurrences":
                items = summary.get("items") or []
                num = summary.get("number") or params.get("number")
                if items:
                    lines = []
                    for i, row in enumerate(items[: int(summary.get("limit") or 10)], 1):
                        pos = row.get("position")
                        pos_s = (
                            position_label_es(pos)
                            if pos not in (None, "", "all")
                            else "posición no indicada"
                        )
                        lines.append(
                            f"{i}. {row.get('date') or '—'} — {row.get('lottery') or '—'} — {pos_s}."
                        )
                    templates.append(
                        f"Las {len(items)} apariciones más recientes del {num} fueron:\n"
                        + "\n".join(lines)
                    )
                else:
                    templates.append(
                        f"No encontré apariciones del {num} dentro del alcance solicitado."
                    )
            elif summary.get("count") is not None:
                label = purpose_label_es(step.purpose)
                templates.append(
                    f"Encontré {summary.get('count')} registros en {label}."
                )
            elif summary.get("last_occurrence_date"):
                templates.append(
                    f"La última aparición registrada es {summary.get('last_occurrence_date')}."
                )
            elif step.purpose:
                templates.append(
                    f"Consulté {purpose_label_es(step.purpose)} con datos históricos."
                )

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
            elif summary.get("number") and (
                summary.get("last_occurrence_date")
                or summary.get("semantics")
                in {"last_occurrence", "compare_across_lotteries", "last_n_occurrences"}
            ):
                purpose = str(step.purpose or "")
                compare_turn = (
                    plan.question_kind == "compare_numbers"
                    or purpose.startswith("compare_")
                ) and not str(plan.question_kind or "").startswith("last_")
                # Sticky compare_active alone must not hijack last_n / last_times.
                if (
                    not compare_turn
                    and (working_state.active_filters or {}).get("compare_active")
                    and plan.question_kind == "compare_numbers"
                ):
                    compare_turn = True
                subjects = [
                    str(x).zfill(2) if str(x).isdigit() else str(x)
                    for x in (
                        (plan.research_meta or {}).get("subjects")
                        or working_state.active_pair
                        or working_state.active_numbers
                        or []
                    )
                    if x is not None
                ]
                if compare_turn and len(subjects) >= 2:
                    # D.2–D.4: never collapse 54/94 to the last tool's single number
                    working_state.active_numbers = subjects[:2]
                    working_state.active_pair = subjects[:2]
                    filters = dict(working_state.active_filters or {})
                    filters["compare_active"] = True
                    working_state.active_filters = filters
                    working_state.last_intent = "compare_numbers"
                    working_state.last_analysis = {
                        "observed": subjects[0],
                        "compare_with": subjects[1],
                        "numbers": subjects[:2],
                        "lottery": summary.get("lottery"),
                        "date": summary.get("last_occurrence_date"),
                        "position": summary.get("position"),
                        "total": summary.get("total") or summary.get("count"),
                        "type": "compare_numbers",
                    }
                else:
                    # Bind conversation subject to THIS turn's tool result (not stale pair)
                    num = (
                        str(summary["number"]).zfill(2)
                        if str(summary["number"]).isdigit()
                        else str(summary["number"])
                    )
                    working_state.active_numbers = [num]
                    working_state.active_pair = []
                    working_state.active_relation = None
                    # Drop sticky same_day/compare so filter refinements stay on this ball.
                    filters = dict(working_state.active_filters or {})
                    filters.pop("relation", None)
                    filters.pop("compare_active", None)
                    filters.pop("compare_with", None)
                    working_state.active_filters = filters
                    # Result lottery/position are NOT filters (rule: found ≠ active filter)
                    working_state.last_analysis = {
                        "observed": num,
                        "lottery": summary.get("lottery"),
                        "date": summary.get("last_occurrence_date"),
                        "position": summary.get("position"),
                        "total": summary.get("total") or summary.get("count"),
                        "limit": summary.get("limit")
                        or (plan.research_meta or {}).get("limit")
                        or (step.params or {}).get("limit"),
                        "items": summary.get("items"),
                    }
                    working_state.last_intent = str(
                        plan.question_kind
                        or summary.get("semantics")
                        or working_state.last_intent
                        or "last_occurrence"
                    )
        evidence_pkg = EvidenceEngine.assemble(
            kind=plan.question_kind or plan.rationale or "research",
            tool_trace=tool_trace,
            evidence_bundle=evidence_bundle,
            context={
                "numbers": list(working_state.active_numbers or []),
                "year_filter": (working_state.active_filters or {}).get("year"),
                "active_date": working_state.active_date,
                **(plan.research_meta or {}),
            },
            case_criteria=(plan.research_meta or {}).get("case_criteria"),
        )

        lead = " ".join(templates[:2]).strip() if templates else (
            "Consulté el histórico autorizado y organicé la evidencia disponible."
            if evidence_bundle
            else "No pude completar la consulta en este momento."
        )
        from app.lottery.ai.turn_policy import scrub_internal_jargon

        template = scrub_internal_jargon(lead)

        duration_ms = int((time.monotonic() - t0) * 1000)
        if structured is None and evidence_bundle:
            structured = {
                "type": "lottery_research",
                "data": {"evidence": evidence_bundle[-8:]},
            }
        if structured is not None:
            research_block = dict(structured.get("research") or {})
            research_block.update(
                {
                    "mode": plan.mode,
                    "status": "completed",
                    "investigating": False,
                    "question_kind": plan.question_kind,
                    "trace_id": trace.trace_id,
                    "duration_ms": duration_ms,
                    "cache_hits": cache_hits,
                    "evidence_package": evidence_pkg.to_dict(),
                    "confidence": evidence_pkg.evidence_level,
                    "steps_completed": [
                        t.get("purpose") for t in tool_trace if t.get("status") == "success"
                    ],
                    "evidence": evidence_bundle[-8:],
                    "plan": [s.purpose or s.tool for s in plan.steps],
                }
            )
            structured["research"] = research_block

        return structured, template, tool_trace, working_ctx, working_state, trace

    def _normalize_params(self, step: PlanStep, state: ConversationState) -> dict[str, Any]:
        params = dict(step.params or {})
        tool = str(step.tool or "")
        purpose = str(step.purpose or "")
        # Fill from memory when omitted
        if not params.get("number") and state.active_numbers:
            params.setdefault("number", state.active_numbers[0])
        if not params.get("observed_number") and state.active_numbers:
            try:
                params.setdefault("observed_number", int(state.active_numbers[0]))
            except (TypeError, ValueError):
                params.setdefault("observed_number", state.active_numbers[0])
        # Map base_date → date when date missing
        if not params.get("date") and params.get("base_date"):
            params["date"] = params["base_date"]
        # Critical: found lottery from a previous result is NOT an active filter.
        # Only fill lottery when the step did not already declare multi-lottery / last_n.
        mode = str(params.get("mode") or purpose)
        following_or_previous = tool in {
            LotteryToolName.GET_FOLLOWING_DAYS.value,
            LotteryToolName.GET_PREVIOUS_DAYS.value,
            LotteryToolName.GET_FOLLOWING_DRAWS.value,
            LotteryToolName.GET_PREVIOUS_DRAWS.value,
        }
        if (
            not params.get("lottery")
            and not params.get("lotteries")
            and mode not in {"last_n", "last_n_occurrences", "last_occurrence_all_lotteries"}
            and "across" not in mode
            and state.active_lotteries
            and (state.active_filters or {}).get("lottery_explicit")
        ):
            params.setdefault("lottery", state.active_lotteries[0])
        # Following/previous days: recover lottery from last analysis when missing
        if following_or_previous and not params.get("lottery"):
            la = state.last_analysis or {}
            if isinstance(la, dict):
                if la.get("lottery"):
                    params["lottery"] = la["lottery"]
                else:
                    items = la.get("items")
                    if isinstance(items, list) and items:
                        first = items[0]
                        if isinstance(first, dict) and first.get("lottery"):
                            params["lottery"] = first["lottery"]
        if not params.get("date") and state.active_date and mode not in {"last_n", "last_n_occurrences"}:
            params.setdefault("date", state.active_date)
        if not params.get("base_date") and state.date_context:
            params.setdefault("base_date", state.date_context)
        if not params.get("date") and params.get("base_date"):
            params["date"] = params["base_date"]
        year = (state.active_filters or {}).get("year")
        if year and "year" not in params and "from_date" not in params:
            params["year"] = year
        # last_times / compare path: pass explicit position from state
        if (
            params.get("position") is None
            and (state.active_filters or {}).get("position_explicit")
            and state.active_position not in (None, "", "all")
        ):
            if purpose.startswith("compare_") or purpose in {
                "last_n_occurrences",
                "last_occurrence",
                "last_occurrence_all_lotteries",
                "compare_across_lotteries",
            }:
                try:
                    params["position"] = int(state.active_position)
                except (TypeError, ValueError):
                    params["position"] = state.active_position
        # Drop None values that confuse tools
        return {k: v for k, v in params.items() if v is not None}

    @staticmethod
    def _structured_type(tool: str) -> str:
        if tool == LotteryToolName.RUN_COMPLETE_ANALYSIS.value:
            return "lottery_complete_analysis"
        if "historical" in tool or "candidate_response" in tool or "confirmer" in tool:
            return "lottery_historical"
        if "compare" in tool:
            return "lottery_comparison"
        return "lottery_result"
