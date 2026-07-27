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
        # Message / resolution numbers take absolute priority over sticky pair memory.
        message_nums = [
            str(n) for n in (p.get("numbers") or []) if n is not None and str(n).strip() != ""
        ]
        from app.lottery.ai.turn_policy import exclude_limit_from_subjects

        message_nums = exclude_limit_from_subjects(message_nums, p.get("limit"))
        pair = list(p.get("active_pair") or getattr(state, "active_pair", None) or [])
        use_pair = bool(p.get("use_active_pair"))
        if message_nums:
            nums = message_nums
        elif use_pair and len(pair) >= 2:
            nums = [str(pair[0]), str(pair[1])]
        else:
            nums = [str(n) for n in (state.active_numbers or []) if n is not None]
            # Only expand empty/single inherited memory to pair when explicitly requested
            if use_pair and len(nums) < 2 and len(pair) >= 2:
                nums = [str(pair[0]), str(pair[1])]

        lottery_explicit = bool(p.get("lottery_explicit") or p.get("lottery_filter"))
        lotteries = list(p.get("lotteries") or [])
        # Inherit explicit lottery filter from conversation state on follow-ups
        if not lotteries and lottery_explicit and state.active_lotteries:
            lotteries = list(state.active_lotteries)[:4]
        if (
            not lotteries
            and not lottery_explicit
            and question.kind not in {"last_times", "last_n_occurrences"}
            and (state.active_filters or {}).get("lottery_explicit")
        ):
            lotteries = list(state.active_lotteries or [])[:4]
            lottery_explicit = bool(lotteries)
        if not lotteries and not lottery_explicit and question.kind != "last_times":
            lotteries = list(state.active_lotteries or [])
        lottery = (lotteries[0] if lotteries else None) or (
            state.active_lotteries[0]
            if state.active_lotteries
            and question.kind not in {"last_times"}
            and lottery_explicit
            else None
        )
        if lottery_explicit and lotteries:
            lottery = lotteries[0]
        year = p.get("year_filter")
        windows = list(p.get("windows") or [1, 3, 7])
        primary = p.get("primary") or state.current_primary_candidate
        observed = nums[0] if nums else None
        confirmer = nums[1] if len(nums) > 1 else None
        # Never invent a confirmer from a stale pair when the user named a single number
        if confirmer is None and use_pair and not message_nums and len(pair) >= 2:
            confirmer = str(pair[1])
        # Position from explicit scope
        pos_scope = p.get("position_scope")
        pos_i = None
        if p.get("position_explicit") or (state.active_filters or {}).get("position_explicit"):
            if isinstance(pos_scope, int) and pos_scope in (1, 2, 3):
                pos_i = pos_scope
            elif str(pos_scope) in {"1", "2", "3"}:
                pos_i = int(pos_scope)
            elif str(pos_scope) in {"first_position", "primera", "1"}:
                pos_i = 1
        base_date = state.active_date or (
            str(state.date_context)[:10] if state.date_context else None
        )
        kind = question.kind
        meta: dict[str, Any] = {
            "kind": kind,
            "case_criteria": [],
            "subjects": nums[:4],
            "lotteries": lotteries[:8],
            "lottery_explicit": lottery_explicit,
            "message_numbers": message_nums[:4],
            "position": pos_i,
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
            # Same-day pair coincidence (preferred) or multi-lottery coincidences
            if p.get("relation") == "same_day" or p.get("active_relation") == "same_day" or (
                observed and confirmer
            ):
                a = observed
                b = confirmer
                if a and b:
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                            params={
                                "numbers": [a, b],
                                "relation": "same_day",
                                "active_relation": "same_day",
                                **({"lottery": lottery} if lottery_explicit and lottery else {}),
                                **(
                                    {"lotteries": lotteries[:4]}
                                    if lottery_explicit and lotteries
                                    else {}
                                ),
                                **({"position": pos_i} if pos_i else {}),
                                "limit": int(p.get("limit") or 200),
                            },
                            purpose="same_day_coincidence",
                        )
                    )
                    meta["relation"] = "same_day"
                    meta["subjects"] = [a, b]
            elif len(lotteries) >= 2:
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
            # Pure last-occurrence: subject = asked number only.
            # Do NOT run complete analysis or temporal windows from stale pair/date.
            if observed:
                from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

                if lottery_explicit and lottery:
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.GET_LAST_OCCURRENCE.value,
                            params={
                                "number": observed,
                                "lottery": lottery,
                                **({"position": pos_i} if pos_i else {}),
                            },
                            purpose="last_occurrence",
                        )
                    )
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                            params={
                                "number": observed,
                                "lottery": lottery,
                                "mode": "last_n",
                                "limit": 1,
                                "page_size": 1,
                                "order": "desc",
                                **({"year": year} if year else {}),
                                **({"position": pos_i} if pos_i else {}),
                            },
                            purpose="recent_occurrences",
                        )
                    )
                else:
                    # Prefer last_n merge across default lotteries (robust to alias gaps
                    # in compare-across). One shared code path with last_n_occurrences.
                    all_lots = list(lotteries) or list(DEFAULT_ALL_HISTORY_LOTTERIES)
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                            params={
                                "number": observed,
                                "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES)[:8]
                                if not lotteries
                                else all_lots[:8],
                                "limit": 1,
                                "page_size": 1,
                                "order": "desc",
                                "mode": "last_n",
                                **({"position": pos_i} if pos_i else {}),
                            },
                            purpose="last_occurrence_all_lotteries",
                        )
                    )
                    # Keep compare-across as secondary evidence for counts per lottery
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                            params={
                                "number": observed,
                                "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES)[:8]
                                if not lotteries
                                else all_lots[:8],
                                **({"position": pos_i} if pos_i else {}),
                            },
                            purpose="frequency_across_lotteries",
                        )
                    )
                meta["subjects"] = [observed]
                meta["lotteries"] = (
                    [lottery] if lottery_explicit and lottery else list(lotteries or DEFAULT_ALL_HISTORY_LOTTERIES)[:8]
                )

        elif kind == "last_n_occurrences":
            if observed:
                from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

                limit = int(p.get("limit") or 3)
                limit = max(1, min(limit, 50))
                result_limit = int(p.get("result_limit") or limit)
                page_offset = int(p.get("page_offset") or p.get("offset") or 0)
                pos = p.get("position_scope")
                pos_n = pos_i
                if pos_n is None:
                    if isinstance(pos, int):
                        pos_n = pos
                    elif str(pos) in {"1", "2", "3"}:
                        pos_n = int(pos)
                all_lots = (
                    [lottery]
                    if lottery_explicit and lottery
                    else (
                        list(lotteries)
                        if lottery_explicit and lotteries
                        else list(DEFAULT_ALL_HISTORY_LOTTERIES)
                    )
                )
                if lottery_explicit and lotteries:
                    all_lots = list(lotteries)[:8]
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                        params={
                            "number": observed,
                            "lotteries": all_lots[:8],
                            "limit": limit,
                            "page_size": limit,
                            "order": "desc",
                            "mode": "last_n",
                            "page_offset": page_offset,
                            "result_limit": result_limit,
                            **({"position": pos_n} if pos_n else {}),
                            **(
                                {"lottery": lottery}
                                if lottery_explicit and lottery
                                else {}
                            ),
                        },
                        purpose="last_n_occurrences",
                    )
                )
                meta["subjects"] = [observed]
                meta["limit"] = result_limit
                meta["lotteries"] = all_lots[:8]

        elif kind == "frequency_behavior":
            from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

            if observed and lottery:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.CALCULATE_FREQUENCIES.value,
                        params={
                            "lottery": lottery,
                            "number": observed,
                            **({"year": year} if year else {}),
                            **({"position": pos_i} if pos_i else {}),
                        },
                        purpose="frequency",
                    )
                )
                steps.extend(period_compare_steps(number=observed, lottery=lottery, years=list(p.get("years") or [])))
            elif observed:
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                        params={
                            "number": observed,
                            "lotteries": (lotteries or list(DEFAULT_ALL_HISTORY_LOTTERIES))[:8],
                            **({"position": pos_i} if pos_i else {}),
                        },
                        purpose="frequency_across_lotteries",
                    )
                )
                if lottery_explicit and lottery:
                    steps.append(
                        PlanStep(
                            tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                            params={
                                "number": observed,
                                "lottery": lottery,
                                "mode": "last_n",
                                "limit": 50,
                                **({"year": year} if year else {}),
                                **({"position": pos_i} if pos_i else {}),
                            },
                            purpose="frequency",
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
