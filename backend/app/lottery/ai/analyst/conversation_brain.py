"""Conversation Brain — structured conversational memory updates (Fase A.1)."""

from __future__ import annotations

from typing import Any

from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult


class ConversationBrain:
    """Keep long conversations coherent without re-asking known slots."""

    def __init__(self, state: ConversationState):
        self.state = state

    def apply_resolution(
        self,
        *,
        understanding: UnderstandingResult,
        resolution: dict[str, Any],
    ) -> ConversationState:
        st = self.state.model_copy(deep=True)
        filters = dict(st.active_filters or {})

        # Return / focus switch
        if resolution.get("return_to_number"):
            n = str(resolution["return_to_number"])
            st.active_numbers = [n]
            st = self._push_focus(st, n)

        nums = list(resolution.get("numbers") or understanding.numbers or [])
        if nums:
            normed = [
                str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n)
                for n in nums
            ]
            st.active_numbers = normed
            for n in normed:
                st = self._push_focus(st, n)
            # Explicit subject(s) in this turn replace stale pair memory unless pair is requested
            if not resolution.get("use_active_pair"):
                if len(normed) >= 2:
                    st.active_pair = list(normed[:2])
                else:
                    st.active_pair = []
                    if resolution.get("follow_up_kind") in {
                        "last_occurrence",
                        "first_occurrence",
                        "frequency",
                        "last_n_occurrences",
                    } or resolution.get("inherit_active_number") is False:
                        st.active_relation = None
                        st.last_analysis = {}
                        st.current_primary_candidate = None

        lots = list(resolution.get("lotteries") or understanding.lotteries or [])
        if resolution.get("lottery_filter"):
            lots = [str(resolution["lottery_filter"])]
            filters["lottery"] = lots[0]
        from app.lottery.ai.turn_policy import asks_all_lotteries, asks_all_positions

        # Clear lottery filter when user asks for all lotteries
        raw_msg = str(
            resolution.get("raw_message")
            or ((understanding.params or {}).get("raw_message") if understanding.params else None)
            or ""
        )
        if asks_all_lotteries(raw_msg) or (
            resolution.get("lottery_explicit") is False and resolution.get("clear_lottery")
        ):
            filters.pop("lottery_explicit", None)
            filters.pop("lottery", None)
            # Keep subject; drop sticky lottery list for "all" scope
            if asks_all_lotteries(raw_msg):
                st.active_lotteries = []
        elif lots:
            st.active_lotteries = list(
                dict.fromkeys([*lots, *[x for x in st.active_lotteries if x not in lots]])
            )
            if resolution.get("lottery_explicit") or resolution.get("lottery_filter"):
                filters["lottery_explicit"] = True
                filters["lottery"] = lots[0]

        if resolution.get("year_filter") is not None:
            filters["year"] = int(resolution["year_filter"])

        if asks_all_positions(raw_msg) or resolution.get("position_scope") in {
            "all",
            "any",
            "any_position",
        }:
            from app.lottery.ai.turn_policy import position_label_es

            st.active_position = "all"
            st.last_position_scope = "all"
            st.position_scope = "all"
            filters["position"] = "all"
            filters["position_explicit"] = True
            filters["position_label"] = position_label_es("all")
        elif resolution.get("position_scope") is not None:
            from app.lottery.ai.turn_policy import canonicalize_position_scope, position_label_es

            canon = canonicalize_position_scope(resolution["position_scope"])
            st.active_position = str(canon) if canon is not None else str(resolution["position_scope"])
            st.last_position_scope = st.active_position
            st.position_scope = st.active_position
            filters["position"] = st.active_position
            if resolution.get("position_explicit"):
                filters["position_explicit"] = True
            filters["position_label"] = position_label_es(canon)

        # Fase X.2 — compound relation memory
        if resolution.get("active_relation") or resolution.get("relation") == "same_day":
            st.active_relation = str(
                resolution.get("active_relation") or resolution.get("relation") or "same_day"
            )
            filters["relation"] = st.active_relation
        if resolution.get("preferred_position") is not None:
            st.preferred_position = int(resolution["preferred_position"])
        if resolution.get("position") is not None or resolution.get("position_scope") == "any_position":
            st.position_scope = str(
                resolution.get("position_scope")
                or ("specific_position" if resolution.get("position") else st.position_scope)
            )

        if resolution.get("compare_with") or (
            resolution.get("follow_up_kind") == "compare" and len(st.active_numbers or []) >= 2
        ):
            filters["compare_active"] = True
            if resolution.get("compare_with"):
                filters["compare_with"] = str(resolution["compare_with"])
                rival = str(resolution["compare_with"])
                if rival not in (st.active_numbers or []):
                    st.active_numbers = list(dict.fromkeys([*(st.active_numbers or []), rival]))[:2]
                try:
                    riv_i = int(rival) if rival.isdigit() else None
                except (TypeError, ValueError):
                    riv_i = None
                if riv_i is not None:
                    st.current_alternatives = list(
                        dict.fromkeys([riv_i, *[int(a) for a in st.current_alternatives if str(a).isdigit()]])
                    )[:8]
        elif len(st.active_numbers or []) >= 2 and resolution.get("follow_up_kind") in {
            None,
            "compare",
        }:
            # Two subjects named in a compare turn
            if resolution.get("numbers") and len(resolution.get("numbers") or []) >= 2:
                filters["compare_active"] = True

        # Pair memory
        if len(st.active_numbers) >= 2:
            st.active_pair = [st.active_numbers[0], st.active_numbers[1]]
            if resolution.get("relation") == "same_day" or resolution.get("active_relation") == "same_day":
                st.active_relation = "same_day"
                st.position_scope = st.position_scope or resolution.get("position_scope") or "any_position"
                st.preferred_position = int(resolution.get("preferred_position") or 1)
        elif resolution.get("use_active_pair") and st.active_pair:
            st.active_numbers = list(st.active_pair)

        if understanding.query_date:
            st.active_date = understanding.query_date.isoformat()
            st.date_context = understanding.query_date

        if understanding.intent:
            st.last_intent = str(understanding.intent)

        st.active_filters = filters

        note = self._compact_note(understanding, resolution)
        recent = list(st.recent_memory or [])
        if note:
            recent = [*recent[-11:], note]
        st.recent_memory = recent

        self.state = st
        return st

    def remember_research(self, plan_summary: dict[str, Any]) -> ConversationState:
        st = self.state.model_copy(deep=True)
        st.current_research = dict(plan_summary or {})
        self.state = st
        return st

    def remember_trace(self, trace: dict[str, Any]) -> ConversationState:
        st = self.state.model_copy(deep=True)
        research = dict(st.current_research or {})
        research["last_trace"] = {
            "intent": trace.get("intent"),
            "tools": trace.get("tools_used"),
            "steps": trace.get("steps_executed"),
            "duration_ms": trace.get("duration_ms"),
            "filters": trace.get("filters"),
        }
        st.current_research = research
        self.state = st
        return st

    def remember_analysis(self, summary: dict[str, Any]) -> ConversationState:
        st = self.state.model_copy(deep=True)
        # Fase X.2 — never collapse a compound active pair to a single observed number
        if summary.get("numbers") and isinstance(summary["numbers"], list) and len(summary["numbers"]) >= 2:
            st.active_numbers = [
                str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n)
                for n in summary["numbers"]
            ][:8]
            st.active_pair = list(st.active_numbers[:2])
            for n in st.active_numbers:
                st = self._push_focus(st, n)
        elif summary.get("observed") is not None and not (
            st.active_relation == "same_day" and len(st.active_numbers or []) >= 2
        ):
            obs = str(summary["observed"]).zfill(2)
            st.active_numbers = [obs]
            st = self._push_focus(st, obs)
        if summary.get("confirmer") is not None:
            st.active_pair = [
                str(summary.get("observed") or (st.active_numbers[0] if st.active_numbers else "")),
                str(summary["confirmer"]),
            ]
            if st.active_relation != "same_day":
                # Keep both in active_numbers when confirmer present
                pair = [str(x).zfill(2) if str(x).isdigit() else str(x) for x in st.active_pair if x]
                if len(pair) >= 2:
                    st.active_numbers = pair
        if summary.get("active_relation"):
            st.active_relation = str(summary["active_relation"])
        if summary.get("position_scope"):
            st.position_scope = str(summary["position_scope"])
            st.last_position_scope = st.position_scope
        if summary.get("primary") is not None:
            st.current_primary_candidate = int(summary["primary"])
        if summary.get("alternatives"):
            st.current_alternatives = [
                int(x) for x in summary["alternatives"] if x is not None
            ][:8]
        if summary.get("date"):
            st.active_date = str(summary["date"])[:10]
        st.last_analysis = {
            "type": summary.get("type") or "complete_analysis",
            "observed": summary.get("observed"),
            "primary": summary.get("primary"),
            "confirmer": summary.get("confirmer"),
            "date": summary.get("date"),
            "lottery": summary.get("lottery"),
        }
        bits = []
        if summary.get("observed") is not None:
            bits.append(f"observado {summary['observed']}")
        if summary.get("primary") is not None:
            bits.append(f"principal {summary['primary']}")
        if summary.get("confirmer") is not None:
            bits.append(f"confirmador {summary['confirmer']}")
        if bits:
            st.conversation_summary = "Análisis activo: " + "; ".join(bits) + "."
        self.state = st
        return st

    def should_skip_number_clarify(self) -> bool:
        return bool(self.state.active_numbers or self.state.current_primary_candidate)

    def context_snapshot(self) -> dict[str, Any]:
        st = self.state
        return {
            "active_numbers": list(st.active_numbers or []),
            "active_pair": list(st.active_pair or []),
            "active_lotteries": list(st.active_lotteries or []),
            "active_filters": dict(st.active_filters or {}),
            "active_position": st.active_position or st.last_position_scope,
            "active_date": st.active_date,
            "primary": st.current_primary_candidate,
            "alternatives": list(st.current_alternatives or []),
            "focus_stack": list(getattr(st, "focus_stack", None) or []),
            "summary": st.conversation_summary,
        }

    @staticmethod
    def _push_focus(st: ConversationState, number: str) -> ConversationState:
        stack = list(getattr(st, "focus_stack", None) or [])
        n = str(number)
        if not stack or stack[-1] != n:
            stack.append(n)
        st.focus_stack = stack[-12:]
        return st

    @staticmethod
    def _compact_note(
        understanding: UnderstandingResult, resolution: dict[str, Any]
    ) -> str | None:
        parts: list[str] = []
        if understanding.intent:
            parts.append(str(understanding.intent))
        nums = resolution.get("numbers") or understanding.numbers
        if nums:
            parts.append("nums=" + ",".join(str(n) for n in nums[:3]))
        if resolution.get("follow_up_kind"):
            parts.append("fu=" + str(resolution["follow_up_kind"]))
        if resolution.get("year_filter"):
            parts.append(f"year={resolution['year_filter']}")
        if resolution.get("compare_with"):
            parts.append(f"vs={resolution['compare_with']}")
        if resolution.get("lottery_filter"):
            parts.append(f"lot={resolution['lottery_filter']}")
        if resolution.get("resolved_refs"):
            parts.append("refs=" + ",".join(str(x) for x in resolution["resolved_refs"][:6]))
        return " | ".join(parts) if parts else None
