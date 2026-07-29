"""InvestigationStateManager — create/update/persist active investigations."""

from __future__ import annotations

from typing import Any

from app.lottery.ai.active_investigation.evidence_aggregator import EvidenceAggregator
from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecision
from app.lottery.ai.active_investigation.session import (
    TTL_SECONDS,
    ActiveInvestigationSession,
)
from app.lottery.ai.active_investigation.session_expiration import SessionExpirationManager


class InvestigationStateManager:
    def __init__(self, *, ttl_seconds: int = TTL_SECONDS):
        self.ttl = SessionExpirationManager(ttl_seconds=ttl_seconds)

    def begin_or_continue(
        self,
        state: Any,
        *,
        decision: HermesDecision,
        message: str,
        conversation_id: str | None = None,
    ) -> ActiveInvestigationSession | None:
        state, inv, _meta = self.ttl.apply_on_turn_start(state)
        if decision.turn_type == "topic_switch" or (
            decision.turn_type == "new_investigation" and decision.reason_code in {
                "explicit_pair_or_topic",
                "EXPLICIT_NEW_RESEARCH",
            }
        ):
            inv = ActiveInvestigationSession(
                conversation_id=conversation_id,
                subjects=list(decision.inherited_subjects or [])[:8],
                relation=decision.inherited_relation,
                metric=decision.inherited_metric or decision.inherited_relation,
                topic=self._topic_label(decision),
                last_user_question=message,
            )
            state.active_investigation = inv.to_store()
            # Explicit new topic: replace sticky subjects and drop prior operable asset
            state.active_numbers = list(decision.inherited_subjects or [])[:8]
            state.active_pair = (
                list(state.active_numbers[:2]) if len(state.active_numbers) >= 2 else []
            )
            if decision.inherited_relation:
                state.active_relation = decision.inherited_relation
            else:
                state.active_relation = None
                filters = dict(state.active_filters or {})
                filters.pop("relation", None)
                state.active_filters = filters
            try:
                from app.lottery.ai.investigation_workspace.store import clear_assets

                clear_assets(state)
            except Exception:  # noqa: BLE001
                state.workspace_assets = {}
                state.active_asset_id = None
            return inv

        if inv is None and decision.inherited_subjects:
            inv = ActiveInvestigationSession(
                conversation_id=conversation_id,
                subjects=list(decision.inherited_subjects)[:8],
                relation=decision.inherited_relation,
                metric=decision.inherited_metric or decision.inherited_relation,
                topic=self._topic_label(decision),
                last_user_question=message,
            )
            state.active_investigation = inv.to_store()
            return inv

        if inv is not None:
            # Preserve compound subjects on contextual turns
            if decision.inherited_subjects and len(decision.inherited_subjects) >= 2:
                inv.subjects = list(decision.inherited_subjects)[:8]
            elif decision.inherited_subjects and not inv.subjects:
                inv.subjects = list(decision.inherited_subjects)[:8]
            if decision.inherited_relation:
                inv.relation = decision.inherited_relation
            if decision.inherited_metric:
                inv.metric = decision.inherited_metric
            inv.follow_up_kind = decision.requested_attribute or decision.turn_type
            inv.last_user_question = message
            self.ttl.renew(inv)
            state.active_investigation = inv.to_store()
            # Mirror into classic sticky fields for legacy classifiers
            if len(inv.subjects) >= 2:
                state.active_numbers = list(inv.subjects[:8])
                state.active_pair = list(inv.subjects[:2])
            if inv.relation:
                state.active_relation = inv.relation
                filters = dict(state.active_filters or {})
                filters["relation"] = inv.relation
                state.active_filters = filters
            return inv
        return None

    def update_after_research(
        self,
        state: Any,
        *,
        investigation: ActiveInvestigationSession | None,
        summary: dict[str, Any] | None,
        template: str | None,
        tools: list[str] | None,
        intent: str | None,
    ) -> ActiveInvestigationSession | None:
        if investigation is None:
            # Bootstrap from same-day summary when research created a new pair
            nums = list((summary or {}).get("numbers") or state.active_numbers or [])[:8]
            if (summary or {}).get("relation") == "same_day" or (
                str(intent or "").lower() in {"coincidences_only", "same_day_coincidence"}
                and len(nums) >= 2
            ):
                investigation = ActiveInvestigationSession(
                    subjects=nums[:2],
                    relation="same_day",
                    metric="same_day",
                    event_type="same_day_coincidence",
                    topic=f"coincidencia {'+'.join(nums[:2])}",
                )
            else:
                return None

        if summary:
            ev = EvidenceAggregator.from_same_day_summary(summary)
            investigation.evidence = {**dict(investigation.evidence or {}), **ev}
            investigation.last_event = EvidenceAggregator.build_last_event(ev)
            investigation.results = {
                "total": ev.get("total"),
                "type": ev.get("type"),
            }
            if ev.get("numbers"):
                investigation.subjects = list(ev["numbers"])[:8]
            investigation.lotteries = list(ev.get("lotteries") or investigation.lotteries)
            investigation.positions = list(ev.get("positions") or investigation.positions)
            investigation.date_anchor = (investigation.last_event or {}).get("date")
            investigation.relation = investigation.relation or "same_day"
            investigation.metric = investigation.metric or "same_day"
            investigation.event_type = "same_day_coincidence"

        if template:
            investigation.last_answer = template[:4000]
            investigation.summary = (template or "")[:500]
        if tools:
            investigation.tools_used = EvidenceAggregator.merge_tool_trace(
                investigation.tools_used, tools
            )
        if intent:
            investigation.last_intent = str(intent)
        self.ttl.renew(investigation)

        # Persist sticky pair — never collapse on same_day
        if len(investigation.subjects) >= 2:
            state.active_numbers = list(investigation.subjects[:8])
            state.active_pair = list(investigation.subjects[:2])
            state.active_relation = investigation.relation or "same_day"
            filters = dict(state.active_filters or {})
            filters["relation"] = state.active_relation
            state.active_filters = filters
            state.last_analysis = {
                **dict(state.last_analysis or {}),
                "type": "same_day_coincidence",
                "numbers": list(investigation.subjects[:2]),
                "relation": "same_day",
                "last_coincidence_date": investigation.date_anchor,
                "total": (investigation.results or {}).get("total"),
                "items": (investigation.evidence or {}).get("items"),
                "last": investigation.last_event,
            }
        state.active_investigation = investigation.to_store()
        return investigation

    @staticmethod
    def _topic_label(decision: HermesDecision) -> str:
        subs = decision.inherited_subjects or []
        if len(subs) >= 2 and (decision.inherited_relation or decision.inherited_metric) == "same_day":
            return f"coincidencia {'+'.join(subs[:2])}"
        if subs:
            return f"número {subs[0]}"
        return "investigación"
