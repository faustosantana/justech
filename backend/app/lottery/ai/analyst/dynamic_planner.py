"""Dynamic Research Planner — builds investigation plans at runtime (Fase B).

Plans are composed from existing LotteryToolName steps. No motor mutation.
"""

from __future__ import annotations

from typing import Any

from app.lottery.ai.analyst.case_search import case_search_steps, describe_case_criteria
from app.lottery.ai.analyst.historical_comparator import (
    compare_lotteries_steps,
    compare_numbers_steps,
    compare_positions_steps,
)
from app.lottery.ai.analyst.question_classifier import ResearchQuestion
from app.lottery.ai.analyst.temporal_analysis import (
    period_compare_steps,
    temporal_after_steps,
    temporal_before_steps,
)
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.planner import PlanStep
from app.services.lottery_ai_contracts import LotteryToolName


class DynamicResearchPlanner:
    """Compose multi-step research plans dynamically from the question kind."""

    @classmethod
    def build(
        cls,
        question: ResearchQuestion,
        state: ConversationState,
        *,
        max_steps: int = 24,
    ) -> tuple[list[PlanStep], dict[str, Any]]:
        p = dict(question.params or {})
        nums = [str(n) for n in (p.get("numbers") or state.active_numbers or [])]
        pair = list(p.get("active_pair") or getattr(state, "active_pair", None) or [])
        if len(nums) < 2 and len(pair) >= 2:
            nums = [str(pair[0]), str(pair[1])]
        lottery = (p.get("lotteries") or state.active_lotteries or [None])[0]
        lotteries = list(p.get("lotteries") or state.active_lotteries or [])
        year = p.get("year_filter")
        windows = list(p.get("windows") or [1, 3, 7])
        primary = p.get("primary") or state.current_primary_candidate
        observed = nums[0] if nums else None
        confirmer = nums[1] if len(nums) > 1 else (pair[1] if len(pair) >= 2 else None)
        base_date = state.active_date or (
            str(state.date_context)[:10] if state.date_context else None
        )
        kind = question.kind
        meta: dict[str, Any] = {
            "kind": kind,
            "case_criteria": [],
            "subjects": nums[:4],
            "lotteries": lotteries[:4],
        }

        steps: list[PlanStep] = []

        if kind in {"what_usually_happens_after", "temporal_after", "temporal_windows", "open_investigation"}:
            if observed:
                steps.extend(
                    temporal_after_steps(
                        number=observed,
                        lottery=lottery,
                        base_date=base_date,
                        windows=windows if kind == "temporal_windows" else [1, 3, 7],
                        year=year,
                    )
                )
                steps.extend(
                    case_search_steps(
                        observed=observed,
                        confirmer=confirmer,
                        candidate=int(primary) if primary is not None else None,
                        lottery=lottery,
                        mode="all",
                    )
                )
                meta["case_criteria"] = describe_case_criteria("all")

        elif kind == "temporal_before":
            if observed:
                steps.extend(
                    temporal_before_steps(
                        number=observed, lottery=lottery, base_date=base_date, windows=windows
                    )
                )

        elif kind == "compare_numbers":
            a = nums[0] if nums else None
            b = nums[1] if len(nums) > 1 else None
            if a and b:
                steps.extend(
                    compare_numbers_steps(
                        a=a, b=b, lotteries=lotteries, lottery=lottery, year=year
                    )
                )
            meta["dimension"] = "numbers"

        elif kind == "compare_lotteries":
            if len(lotteries) >= 2:
                steps.extend(
                    compare_lotteries_steps(
                        lottery_a=lotteries[0],
                        lottery_b=lotteries[1],
                        number=observed,
                    )
                )
            meta["dimension"] = "lotteries"

        elif kind == "compare_positions":
            if observed:
                steps.extend(compare_positions_steps(number=observed, lottery=lottery))
            meta["dimension"] = "positions"

        elif kind == "compare_periods":
            if observed:
                steps.extend(
                    period_compare_steps(
                        number=observed, lottery=lottery, years=list(p.get("years") or [])
                    )
                )
            meta["dimension"] = "periods"

        elif kind == "compare_groups":
            if observed:
                steps.extend(
                    case_search_steps(
                        observed=observed,
                        confirmer=confirmer,
                        candidate=int(primary) if primary is not None else None,
                        mode="all",
                    )
                )
                if confirmer:
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.COMPARE_HISTORICAL_PATTERNS.value,
                            params={
                                "origin_x": int(observed) if str(observed).isdigit() else observed,
                                "confirmer_y": int(confirmer)
                                if str(confirmer).isdigit()
                                else confirmer,
                            },
                            purpose="group_pattern_compare",
                        )
                    )
            meta["dimension"] = "groups"
            meta["case_criteria"] = describe_case_criteria("all")

        elif kind in {"case_search", "equivalents_only", "recent_cases_only"}:
            mode = {
                "equivalents_only": "equivalent",
                "recent_cases_only": "recent",
            }.get(kind, "all")
            steps.extend(
                case_search_steps(
                    observed=observed,
                    confirmer=confirmer,
                    candidate=int(primary) if primary is not None else None,
                    lottery=lottery,
                    mode=mode,
                )
            )
            meta["case_criteria"] = describe_case_criteria(mode if mode != "recent" else "equivalent")

        elif kind == "confirmations_only":
            if observed:
                hist: dict[str, Any] = {
                    "origin_x": int(observed) if str(observed).isdigit() else observed,
                }
                if confirmer is not None:
                    hist["confirmer_y"] = (
                        int(confirmer) if str(confirmer).isdigit() else confirmer
                    )
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.CONFIRMER_COMBINATIONS.value,
                        params=hist,
                        purpose="confirmations_only",
                    )
                )

        elif kind == "coincidences_only":
            if len(lotteries) >= 2:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_COINCIDENCES.value,
                        params={"lotteries": lotteries[:4], "number": observed},
                        purpose="coincidences_only",
                    )
                )

        elif kind in {"which_lottery_confirms_first", "which_confirms_most"}:
            if observed:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                        params={"number": observed, "lotteries": lotteries[:8]},
                        purpose="confirm_lottery_scan",
                    )
                )
                hist = {"origin_x": int(observed) if str(observed).isdigit() else observed}
                if confirmer is not None:
                    hist["confirmer_y"] = (
                        int(confirmer) if str(confirmer).isdigit() else confirmer
                    )
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.CONFIRMER_COMBINATIONS.value,
                        params=hist,
                        purpose="confirm_combinations",
                    )
                )
                if primary is not None:
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.CANDIDATE_RESPONSE_SUMMARY.value,
                            params={**hist, "candidate_c": int(primary)},
                            purpose="confirm_d_windows",
                        )
                    )

        elif kind in {"related_numbers", "best_historical_group"}:
            if observed:
                steps.extend(
                    case_search_steps(
                        observed=observed,
                        confirmer=confirmer,
                        candidate=int(primary) if primary is not None else None,
                        mode="related" if kind == "related_numbers" else "all",
                    )
                )
                meta["case_criteria"] = describe_case_criteria(
                    "related" if kind == "related_numbers" else "all"
                )

        elif kind == "last_times":
            if observed:
                if confirmer:
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.RUN_COMPLETE_ANALYSIS.value,
                            params={
                                "observed_number": int(observed)
                                if str(observed).isdigit()
                                else observed,
                                "confirmer": int(confirmer)
                                if str(confirmer).isdigit()
                                else confirmer,
                                "lottery": lottery,
                                "include_historical": True,
                            },
                            purpose="complete_analysis_t1_t2",
                        )
                    )
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_LAST_OCCURRENCE.value,
                        params={"number": observed, "lottery": lottery},
                        purpose="last_occurrence",
                    )
                )
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                        params={
                            "number": observed,
                            "lottery": lottery,
                            **({"year": year} if year else {}),
                        },
                        purpose="recent_occurrences",
                    )
                )
                steps.extend(
                    temporal_after_steps(
                        number=observed,
                        lottery=lottery,
                        base_date=base_date,
                        windows=[1, 3, 7],
                    )
                )

        elif kind == "frequency_behavior":
            if observed and lottery:
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
                steps.extend(period_compare_steps(number=observed, lottery=lottery, years=list(p.get("years") or [])))
            elif observed:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                        params={"number": observed, "lotteries": lotteries[:8]},
                        purpose="frequency_across_lotteries",
                    )
                )

        elif kind == "filtered_follow_up":
            follow = p.get("follow_up_kind")
            if observed and follow == "lotteries":
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                        params={"number": observed, "lotteries": lotteries[:8]},
                        purpose="filtered_lotteries",
                    )
                )
            elif observed and follow == "positions":
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_POSITION_DISTRIBUTION.value,
                        params={
                            "number": observed,
                            "lottery": lottery,
                            **({"year": year} if year else {}),
                        },
                        purpose="filtered_positions",
                    )
                )
            elif observed and str(follow or "").startswith("d_plus"):
                days = int(str(follow).split("_")[-1] or 7)
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                        params={
                            "number": observed,
                            "lottery": lottery,
                            "days": days,
                            "base_date": base_date,
                        },
                        purpose=follow,
                    )
                )
            elif observed:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                        params={
                            "number": observed,
                            "lottery": lottery,
                            **({"year": year} if year else {}),
                            **(
                                {"position_scope": p.get("position_scope")}
                                if p.get("position_scope")
                                else {}
                            ),
                        },
                        purpose="filtered_occurrences",
                    )
                )

        # Deduplicate by tool+purpose+stable params signature
        unique: list[PlanStep] = []
        seen: set[str] = set()
        for s in steps:
            key = f"{s.tool}:{s.purpose}:{sorted((s.params or {}).items())}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(s)
        return unique[: max(1, max_steps)], meta
