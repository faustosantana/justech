"""Conversation Brain — structured conversational memory updates (Fase A)."""

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

        nums = list(resolution.get("numbers") or understanding.numbers or [])
        if nums:
            st.active_numbers = [str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n) for n in nums]

        lots = list(resolution.get("lotteries") or understanding.lotteries or [])
        if resolution.get("lottery_filter"):
            lots = [str(resolution["lottery_filter"])]
        if lots:
            st.active_lotteries = list(dict.fromkeys([*lots, *[x for x in st.active_lotteries if x not in lots]]))

        if resolution.get("year_filter") is not None:
            filters = dict(getattr(st, "active_filters", None) or {})
            filters["year"] = int(resolution["year_filter"])
            st.active_filters = filters  # type: ignore[attr-defined]

        if resolution.get("position_scope"):
            st.active_position = str(resolution["position_scope"])
            st.last_position_scope = str(resolution["position_scope"])

        # Pair memory
        if len(st.active_numbers) >= 2:
            st.active_pair = [st.active_numbers[0], st.active_numbers[1]]  # type: ignore[attr-defined]
        elif resolution.get("use_active_pair") and getattr(st, "active_pair", None):
            st.active_numbers = list(st.active_pair)  # type: ignore[attr-defined]

        if understanding.query_date:
            st.active_date = understanding.query_date.isoformat()
            st.date_context = understanding.query_date

        if understanding.intent:
            st.last_intent = str(understanding.intent)

        # Recent memory (short rolling notes — not full transcript)
        note = self._compact_note(understanding, resolution)
        recent = list(getattr(st, "recent_memory", None) or [])
        if note:
            recent = [*recent[-7:], note]
        st.recent_memory = recent  # type: ignore[attr-defined]

        self.state = st
        return st

    def remember_research(self, plan_summary: dict[str, Any]) -> ConversationState:
        st = self.state.model_copy(deep=True)
        st.current_research = dict(plan_summary or {})  # type: ignore[attr-defined]
        self.state = st
        return st

    def remember_analysis(self, summary: dict[str, Any]) -> ConversationState:
        st = self.state.model_copy(deep=True)
        if summary.get("observed") is not None:
            st.active_numbers = [str(summary["observed"]).zfill(2)]
        if summary.get("confirmer") is not None:
            st.active_pair = [  # type: ignore[attr-defined]
                str(summary.get("observed") or (st.active_numbers[0] if st.active_numbers else "")),
                str(summary["confirmer"]),
            ]
        if summary.get("primary") is not None:
            st.current_primary_candidate = int(summary["primary"])
        if summary.get("alternatives"):
            st.current_alternatives = [int(x) for x in summary["alternatives"] if x is not None][:8]
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
        # Update rolling summary (compact — not full chat dump)
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

    @staticmethod
    def _compact_note(understanding: UnderstandingResult, resolution: dict[str, Any]) -> str | None:
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
        return " | ".join(parts) if parts else None
