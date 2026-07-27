"""Research Planner — internal multi-step investigation plans (never shown to user)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.lottery.ai.analyst.config import AnalystRuntimeConfig
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.planner import PlanStep, QueryPlan, build_plan
from app.services.lottery_ai_contracts import LotteryToolName


@dataclass
class ResearchPlan:
    mode: str  # quick | deep | none
    is_research: bool
    steps: list[PlanStep] = field(default_factory=list)
    rationale: str = ""
    investigating_message: str = "Estoy investigando…"
    user_visible_status: str | None = None
    question_kind: str | None = None
    research_meta: dict[str, Any] = field(default_factory=dict)

    def to_summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "is_research": self.is_research,
            "rationale": self.rationale,
            "steps": [s.purpose or s.tool for s in self.steps],
            "step_count": len(self.steps),
            "question_kind": self.question_kind,
            "research_meta": self.research_meta,
        }


class ResearchPlanner:
    """Build an internal research plan before answering.

    Fase B: prefers ResearchEngine dynamic plans for open investigations,
    then falls back to Fase A heuristic deep steps.
    """

    _PAIR_HISTORY = re.compile(
        r"(ultimas?\s+veces|qu[eé]\s+pas[oó].{0,40}salieron|"
        r"casos?\s+(equivalentes|similares)|comportamiento\s+hist|"
        r"cuando\s+salieron|pareja|con\s+el\s+\d+)",
        re.I,
    )
    _DEEP_MARKERS = re.compile(
        r"(d\s*\+\s*[137]|hasta\s+d\s*\+|evidencia\s+hist|"
        r"confirma\s+m[aá]s|loter[ií]a\s+confirm|"
        r"tabla\s*1|tabla\s*2|compa[nñ]eros|vecinos|"
        r"investiga|profund|compara(r)?\s+(estos|dos)\s+an[aá]lisis|"
        r"diferencias?\s+entre)",
        re.I,
    )

    @classmethod
    def plan(
        cls,
        *,
        message: str,
        understanding: UnderstandingResult,
        state: ConversationState,
        config: AnalystRuntimeConfig,
        resolution: dict[str, Any] | None = None,
    ) -> ResearchPlan:
        resolution = resolution or {}

        # Clarifications / refuses → no research (unless engine can inherit)
        if understanding.params.get("refuse_message") or understanding.intent in {
            "out_of_domain",
            "restricted_technical",
            "prediction_request",
            "harmful_or_illegal",
        }:
            return ResearchPlan(mode="none", is_research=False, steps=[], rationale="refuse_or_clarify")

        # Fase B — dynamic Research Engine first
        try:
            from app.lottery.ai.analyst.research_engine import get_research_engine

            engine_plan = get_research_engine().build_plan(
                message=message,
                understanding=understanding,
                state=state,
                config=config,
                resolution=resolution,
            )
            if engine_plan is not None:
                return engine_plan
        except Exception:  # noqa: BLE001 — never break chat on planner errors
            pass

        base = build_plan(understanding)

        if understanding.needs_clarification or not understanding.tool:
            return ResearchPlan(
                mode="none",
                is_research=False,
                steps=list(base.steps),
                rationale=base.rationale or "clarify",
            )

        wants_deep = bool(cls._DEEP_MARKERS.search(message or "")) or bool(
            cls._PAIR_HISTORY.search(message or "")
        )
        follow = resolution.get("follow_up_kind")
        if follow in {
            "d_plus_1",
            "d_plus_3",
            "d_plus_7",
            "after",
            "before",
            "lotteries",
            "positions",
            "compare",
            "first_occurrence",
            "last_occurrence",
        }:
            wants_deep = True

        # Mode + depth from Admin runtime
        mode = config.research_mode
        if mode == "quick" or config.analysis_depth == "light":
            is_research = False
        elif mode == "deep" or config.analysis_depth == "deep":
            is_research = True
        else:
            is_research = wants_deep or len(understanding.numbers or state.active_numbers or []) >= 2

        if not is_research:
            return ResearchPlan(
                mode="quick",
                is_research=False,
                steps=list(base.steps)[: config.effective_max_tools()],
                rationale=base.rationale or "single_query",
            )

        steps = cls._build_deep_steps(understanding, state, resolution, base)
        # Bound by admin runtime config
        steps = steps[: config.effective_max_steps()][: config.effective_max_tools()]
        return ResearchPlan(
            mode="deep",
            is_research=True,
            steps=steps,
            rationale="multi_step_research",
            investigating_message=config.investigating_message,
            user_visible_status=config.investigating_message,
        )

    @classmethod
    def _build_deep_steps(
        cls,
        understanding: UnderstandingResult,
        state: ConversationState,
        resolution: dict[str, Any],
        base: QueryPlan,
    ) -> list[PlanStep]:
        nums = list(understanding.numbers or state.active_numbers or resolution.get("numbers") or [])
        nums = [str(n) for n in nums if n is not None]
        observed = nums[0] if nums else None
        confirmer = nums[1] if len(nums) > 1 else None
        if not confirmer and state.active_pair and len(state.active_pair) >= 2:
            confirmer = str(state.active_pair[1])
            if not observed:
                observed = str(state.active_pair[0])
        lottery = (
            (understanding.lotteries[0] if understanding.lotteries else None)
            or (state.active_lotteries[0] if state.active_lotteries else None)
            or resolution.get("lottery_filter")
        )
        year = resolution.get("year_filter") or (state.active_filters or {}).get("year")
        primary = state.current_primary_candidate

        steps: list[PlanStep] = []

        # 1) Occurrences / last time for active number
        follow = resolution.get("follow_up_kind")
        if observed and (
            follow
            in {
                "lotteries",
                "last_occurrence",
                "first_occurrence",
                "positions",
                "compare",
            }
            or understanding.tool
            in {
                LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                LotteryToolName.GET_LAST_OCCURRENCE.value,
                LotteryToolName.GET_POSITION_DISTRIBUTION.value,
                LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                LotteryToolName.CALCULATE_FREQUENCIES.value,
                LotteryToolName.GET_COINCIDENCES.value,
                LotteryToolName.COMPARE_NUMBER_PERIODS.value,
            }
        ):
            if follow == "lotteries" or understanding.scope == "all":
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                        params={"number": observed, "lotteries": list(state.active_lotteries or [])[:8]},
                        purpose="occurrences_by_lottery",
                    )
                )
            elif follow == "positions":
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_POSITION_DISTRIBUTION.value,
                        params={
                            "number": observed,
                            "lottery": lottery,
                            **({"year": year} if year else {}),
                        },
                        purpose="position_distribution",
                    )
                )
            elif follow == "last_occurrence":
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_LAST_OCCURRENCE.value,
                        params={"number": observed, "lottery": lottery},
                        purpose="last_occurrence",
                    )
                )
            elif follow == "first_occurrence":
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                        params={
                            "number": observed,
                            "lottery": lottery,
                            "occurrence_mode": "all",
                            "order": "asc",
                        },
                        purpose="first_occurrence",
                    )
                )
            elif follow == "compare" or resolution.get("compare_with"):
                rival = resolution.get("compare_with") or (
                    str(state.current_alternatives[0]) if state.current_alternatives else None
                )
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                        params={
                            "number": observed,
                            "lotteries": list(state.active_lotteries or [])[:8],
                        },
                        purpose="compare_subject_lotteries",
                    )
                )
                if rival:
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                            params={
                                "number": rival,
                                "lotteries": list(state.active_lotteries or [])[:8],
                            },
                            purpose="compare_rival_lotteries",
                        )
                    )
            else:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                        params={
                            "number": observed,
                            "lottery": lottery,
                            **({"year": year} if year else {}),
                        },
                        purpose="number_occurrences",
                    )
                )

        # Frequency / period / coincidences when historical depth requested
        if observed and (
            re.search(r"frecuen|periodo|coinciden|secuencia", str(understanding.intent or ""), re.I)
            or understanding.tool
            in {
                LotteryToolName.CALCULATE_FREQUENCIES.value,
                LotteryToolName.COMPARE_NUMBER_PERIODS.value,
                LotteryToolName.GET_COINCIDENCES.value,
            }
        ):
            if lottery:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.CALCULATE_FREQUENCIES.value,
                        params={
                            "lottery": lottery,
                            "number": observed,
                            **({"year": year} if year else {}),
                        },
                        purpose="frequency",
                    )
                )
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.COMPARE_NUMBER_PERIODS.value,
                        params={
                            "lottery": lottery,
                            "number": observed,
                            "period_a": "current_year",
                            "period_b": "previous_year",
                        },
                        purpose="period_comparison",
                    )
                )
            if len(state.active_lotteries or []) >= 2:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_COINCIDENCES.value,
                        params={
                            "lotteries": list(state.active_lotteries)[:4],
                            "number": observed,
                        },
                        purpose="cross_lottery_coincidences",
                    )
                )

        # 2) Complete analysis when pair / analyze intent
        if understanding.tool == LotteryToolName.RUN_COMPLETE_ANALYSIS.value:
            ca_params = dict(understanding.params or {})
            if not ca_params and base.steps:
                ca_params = dict(base.steps[0].params or {})
            steps.append(
                PlanStep(
                    tool=LotteryToolName.RUN_COMPLETE_ANALYSIS.value,
                    params=ca_params,
                    purpose="complete_analysis_t1_t2",
                )
            )
        elif observed and confirmer:
            steps.append(
                PlanStep(
                    tool=LotteryToolName.RUN_COMPLETE_ANALYSIS.value,
                    params={
                        "observed_number": int(observed)
                        if str(observed).isdigit()
                        else observed,
                        "confirmer": int(confirmer) if str(confirmer).isdigit() else confirmer,
                        "lottery": lottery,
                        "date": state.active_date or understanding.params.get("date"),
                        "include_historical": True,
                    },
                    purpose="complete_analysis_t1_t2",
                )
            )

        # 3) Historical relation tools (D windows / equivalent cases) — read-only
        if observed and (
            confirmer
            or primary is not None
            or str(follow or "").startswith("d_plus")
            or understanding.tool
            in {
                LotteryToolName.HISTORICAL_RELATION_CONDITIONS.value,
                LotteryToolName.CANDIDATE_RESPONSE_SUMMARY.value,
                LotteryToolName.CONFIRMER_COMBINATIONS.value,
            }
        ):
            cand = primary
            if cand is None and understanding.params.get("candidate"):
                cand = understanding.params.get("candidate")
            hist_params: dict[str, Any] = {
                "origin_x": int(observed) if str(observed).isdigit() else observed,
            }
            if confirmer is not None:
                hist_params["confirmer_y"] = (
                    int(confirmer) if str(confirmer).isdigit() else confirmer
                )
            if cand is not None:
                hist_params["candidate_c"] = int(cand)
            steps.append(
                PlanStep(
                    tool=LotteryToolName.HISTORICAL_RELATION_CONDITIONS.value,
                    params=hist_params,
                    purpose="historical_equivalent_cases",
                )
            )
            if cand is not None:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.CANDIDATE_RESPONSE_SUMMARY.value,
                        params={**hist_params, "candidate_c": int(cand)},
                        purpose="d1_d3_d7_summary",
                    )
                )
            if confirmer is not None:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.CONFIRMER_COMBINATIONS.value,
                        params=hist_params,
                        purpose="cross_confirmations",
                    )
                )

        # 4) After / before windows
        if follow == "after" and observed:
            steps.append(
                PlanStep(
                    tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                    params={
                        "number": observed,
                        "lottery": lottery,
                        "days": state.calendar_window or 7,
                        "base_date": state.active_date or state.date_context,
                    },
                    purpose="what_happened_after",
                )
            )
        if follow == "before" and observed:
            steps.append(
                PlanStep(
                    tool=LotteryToolName.GET_PREVIOUS_DAYS.value,
                    params={
                        "number": observed,
                        "lottery": lottery,
                        "days": state.calendar_window or 7,
                        "base_date": state.active_date or state.date_context,
                    },
                    purpose="what_happened_before",
                )
            )

        # Fallback to base plan if nothing matched
        if not steps:
            steps = list(base.steps)

        # Deduplicate by tool+purpose keeping order
        seen: set[str] = set()
        unique: list[PlanStep] = []
        for s in steps:
            key = f"{s.tool}:{s.purpose}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(s)
        return unique
