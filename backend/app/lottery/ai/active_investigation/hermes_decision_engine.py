"""HermesDecisionEngine — structured turn decisions (deterministic orchestrator).

This is NOT the Huawei ModelArts HTTP synthesizer. It records a safe, compact
decision before research/tools run. Chain-of-thought is never exposed.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.lottery.ai.active_investigation.contextual_follow_up import (
    ContextualFollowUpResolver,
)
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession

TurnType = Literal[
    "new_investigation",
    "contextual_follow_up",
    "attribute_of_last_event",
    "filter_refine",
    "topic_switch",
    "clarify",
    "meta",
    "reuse_evidence",
]


class HermesDecision(BaseModel):
    model_config = {"extra": "ignore"}

    hermes_decision_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    turn_type: TurnType = "new_investigation"
    refers_to: str | None = None
    requested_attribute: str | None = None
    inherited_subjects: list[str] = Field(default_factory=list)
    inherited_metric: str | None = None
    inherited_relation: str | None = None
    requires_research: bool = True
    reuse_evidence: bool = False
    confidence: Literal["high", "medium", "low"] = "medium"
    reason_code: str | None = None
    ambiguous: bool = False
    user_query: str | None = None

    def to_trace(self) -> dict[str, Any]:
        """Safe summary for diagnostics — no chain-of-thought."""
        return {
            "hermes_decision_id": self.hermes_decision_id,
            "turn_type": self.turn_type,
            "refers_to": self.refers_to,
            "requested_attribute": self.requested_attribute,
            "inherited_subjects": list(self.inherited_subjects),
            "inherited_metric": self.inherited_metric,
            "inherited_relation": self.inherited_relation,
            "requires_research": self.requires_research,
            "reuse_evidence": self.reuse_evidence,
            "confidence": self.confidence,
            "reason_code": self.reason_code,
            "ambiguous": self.ambiguous,
        }


class HermesDecisionEngine:
    """Decide continuation vs new research vs evidence reuse."""

    @classmethod
    def decide(
        cls,
        message: str,
        *,
        state: Any,
        investigation: ActiveInvestigationSession | None,
        resolution: dict[str, Any] | None = None,
    ) -> HermesDecision:
        raw = message or ""
        res = resolution or {}
        decision = HermesDecision(user_query=raw)

        # Explicit topic reset
        if re_search_nueva(raw):
            decision.turn_type = "new_investigation"
            decision.reason_code = "explicit_reset"
            decision.confidence = "high"
            return decision

        # Meta / correction
        from app.lottery.ai.turn_policy import (
            ConversationPolicy,
            extract_subject_numbers,
            is_correction_or_meta_request,
        )

        if ConversationPolicy.is_meta_continuity(raw) or is_correction_or_meta_request(raw):
            decision.turn_type = "meta"
            decision.requires_research = False
            decision.inherited_subjects = list(
                getattr(investigation, "subjects", None)
                or getattr(state, "active_numbers", None)
                or []
            )[:8]
            decision.confidence = "high"
            decision.reason_code = "meta_continuity"
            return decision

        msg_nums = extract_subject_numbers(raw)
        active_pair = list(
            getattr(investigation, "subjects", None)
            or getattr(state, "active_pair", None)
            or getattr(state, "active_numbers", None)
            or []
        )[:8]
        inv_active = investigation is not None and not investigation.is_expired()
        relation = (
            (getattr(investigation, "relation", None) if inv_active else None)
            or getattr(state, "active_relation", None)
            or (state.active_filters or {}).get("relation")
        )

        # Clear subject switch away from active pair
        if (
            inv_active
            and len(msg_nums) == 1
            and active_pair
            and msg_nums[0] not in active_pair
            and not ContextualFollowUpResolver.is_short_contextual_follow_up(raw)
        ):
            decision.turn_type = "topic_switch"
            decision.inherited_subjects = msg_nums[:1]
            decision.requires_research = True
            decision.confidence = "high"
            decision.reason_code = "new_single_subject"
            return decision

        # Two new numbers → new/continue investigation
        if len(msg_nums) >= 2 and (
            not inv_active or sorted(msg_nums[:2]) != sorted(active_pair[:2])
        ):
            decision.turn_type = "new_investigation"
            decision.inherited_subjects = msg_nums[:2]
            decision.requires_research = True
            decision.confidence = "high"
            decision.reason_code = "explicit_pair_or_topic"
            return decision

        follow = ContextualFollowUpResolver.resolve(
            raw, investigation=investigation if inv_active else None, state=state
        )
        if follow and inv_active:
            attr = follow.get("requested_attribute")
            decision.turn_type = (
                "attribute_of_last_event"
                if attr in {"lotteries", "positions", "date", "order", "explain", "details"}
                else "contextual_follow_up"
            )
            if attr in {"filter_lottery", "filter_position"}:
                decision.turn_type = "filter_refine"
            decision.refers_to = follow.get("refers_to")
            decision.requested_attribute = attr
            decision.inherited_subjects = list(follow.get("inherited_subjects") or active_pair)[:8]
            decision.inherited_metric = follow.get("inherited_metric") or relation
            decision.inherited_relation = follow.get("inherited_relation") or relation
            # Evidence reuse for attribute asks when last_event is populated
            last_event = follow.get("last_event") or {}
            evidence = follow.get("evidence") or {}
            can_reuse = cls._can_answer_from_evidence(attr, last_event, evidence)
            decision.reuse_evidence = can_reuse
            decision.requires_research = not can_reuse
            decision.confidence = "high"
            decision.reason_code = f"attr:{attr}:{'reuse' if can_reuse else 'research'}"
            return decision

        # IntentResolver already marked lotteries/positions with sticky same_day
        if inv_active and res.get("follow_up_kind") in {"lotteries", "positions"} and relation == "same_day":
            attr = "lotteries" if res.get("follow_up_kind") == "lotteries" else "positions"
            decision.turn_type = "attribute_of_last_event"
            decision.requested_attribute = attr
            decision.inherited_subjects = active_pair[:2]
            decision.inherited_metric = "same_day"
            decision.inherited_relation = "same_day"
            decision.refers_to = "active_investigation.last_event"
            last_event = dict(getattr(investigation, "last_event", None) or {})
            can_reuse = cls._can_answer_from_evidence(attr, last_event, {})
            decision.reuse_evidence = can_reuse
            decision.requires_research = not can_reuse
            decision.confidence = "high"
            decision.reason_code = f"resolver_follow:{attr}"
            return decision

        if inv_active and not msg_nums and ContextualFollowUpResolver.is_short_contextual_follow_up(raw):
            decision.turn_type = "contextual_follow_up"
            decision.inherited_subjects = active_pair[:8]
            decision.inherited_relation = relation
            decision.inherited_metric = relation
            decision.requires_research = True
            decision.confidence = "medium"
            decision.reason_code = "short_deictic"
            return decision

        decision.turn_type = "new_investigation" if not inv_active else "contextual_follow_up"
        decision.inherited_subjects = msg_nums or active_pair[:8]
        decision.inherited_relation = relation
        decision.inherited_metric = relation
        decision.requires_research = True
        decision.confidence = "medium"
        decision.reason_code = "default_research"
        return decision

    @staticmethod
    def _can_answer_from_evidence(
        attr: str | None,
        last_event: dict[str, Any],
        evidence: dict[str, Any],
    ) -> bool:
        if not attr:
            return False
        if attr == "lotteries":
            lots = last_event.get("lotteries") or evidence.get("lotteries")
            appearances = last_event.get("appearances") or last_event.get("entries")
            return bool(lots or appearances)
        if attr in {"positions", "order"}:
            appearances = last_event.get("appearances") or last_event.get("entries")
            return bool(appearances)
        if attr == "date":
            return bool(last_event.get("date") or last_event.get("draw_date"))
        if attr in {"explain", "details"}:
            return bool(last_event or evidence.get("summary"))
        if attr == "count":
            return evidence.get("total") is not None
        return False


def re_search_nueva(text: str) -> bool:
    import re

    return bool(re.search(r"^\s*nueva\s+conversaci[oó]n\s*$", text or "", re.I))
