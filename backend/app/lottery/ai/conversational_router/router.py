"""Conversational Router 3.0 — high-priority intent routing.

Mandatory order (never invert):
1. social_chitchat
2. workspace_action
3. explicit_new_investigation
4. analytical_clarification
5. contextual_follow_up
6. default_research
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.lottery.ai.conversational_router.social_chitchat import detect_social_chitchat
from app.lottery.ai.investigation_workspace.schemas import WorkspaceActionDecision
from app.lottery.ai.investigation_workspace.speech_acts import WorkspaceSpeechActDetector
from app.lottery.ai.investigation_workspace.store import get_active_asset
from app.lottery.ai.turn_policy import extract_subject_numbers


PathKind = Literal[
    "social_chitchat",
    "workspace_action",
    "explicit_new_investigation",
    "analytical_clarification",
    "contextual_follow_up",
    "default_research",
    # legacy aliases kept for Path A/B callers
    "new_investigation",
    "asset_operation",
]


class ConversationalRoute(BaseModel):
    model_config = {"extra": "ignore"}

    path: PathKind
    workspace_action: WorkspaceActionDecision | None = None
    reason_code: str = ""
    can_materialize: bool = False
    has_active_asset: bool = False
    social_reply: str | None = None
    inherited_subjects: list[str] = Field(default_factory=list)

    def to_trace(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "reason_code": self.reason_code,
            "can_materialize": self.can_materialize,
            "has_active_asset": self.has_active_asset,
            "inherited_subjects": list(self.inherited_subjects or []),
            "social_reply": self.social_reply,
            "workspace_action": (
                self.workspace_action.to_trace() if self.workspace_action else None
            ),
        }


class ConversationalRouter:
    """High-priority router before clarification / follow-up / research."""

    @classmethod
    def route(
        cls,
        message: str,
        *,
        state: Any,
        investigation: Any | None = None,
        pending_clarification: bool | None = None,
    ) -> ConversationalRoute:
        raw = (message or "").strip()
        inv_active = investigation is not None and not investigation.is_expired()
        active_pair = list(
            getattr(investigation, "subjects", None)
            or getattr(state, "active_pair", None)
            or getattr(state, "active_numbers", None)
            or []
        )[:8]
        relation = (
            (getattr(investigation, "relation", None) if inv_active else None)
            or getattr(state, "active_relation", None)
            or (getattr(state, "active_filters", None) or {}).get("relation")
        )
        asset = get_active_asset(state)
        has_asset = asset is not None and not asset.is_expired()
        can_materialize = bool(
            has_asset
            or (
                inv_active
                and relation == "same_day"
                and len(active_pair) >= 2
            )
            or (
                getattr(state, "active_relation", None) == "same_day"
                and len(active_pair) >= 2
            )
        )
        has_pending = (
            pending_clarification
            if pending_clarification is not None
            else bool(
                getattr(state, "pending_intent", None)
                and getattr(state, "pending_slots", None)
            )
        )

        # 1) social_chitchat — before inheritance / clarification / research
        social = detect_social_chitchat(raw)
        if social is not None:
            return ConversationalRoute(
                path="social_chitchat",
                reason_code=social.reason_code,
                can_materialize=can_materialize,
                has_active_asset=has_asset,
                social_reply=social.reply,
                inherited_subjects=[],
            )

        # 2) workspace_action — operable asset / materializable same-day
        if can_materialize:
            if not cls._is_new_investigation(raw, active_pair=active_pair, inv_active=inv_active):
                ws = WorkspaceSpeechActDetector.detect(
                    raw,
                    has_active_asset=True,
                    has_active_investigation=True,
                )
                if ws is not None:
                    return ConversationalRoute(
                        path="workspace_action",
                        workspace_action=ws,
                        reason_code=ws.reason_code or "WORKSPACE_ACTION_MATCH",
                        can_materialize=can_materialize,
                        has_active_asset=has_asset,
                        inherited_subjects=list(active_pair[:8]),
                    )

        # 3) explicit_new_investigation
        if cls._is_new_investigation(raw, active_pair=active_pair, inv_active=inv_active):
            return ConversationalRoute(
                path="explicit_new_investigation",
                reason_code="EXPLICIT_NEW_RESEARCH",
                can_materialize=can_materialize,
                has_active_asset=has_asset,
                inherited_subjects=extract_subject_numbers(raw)[:8] or list(active_pair[:8]),
            )

        # 4) analytical_clarification — only with explicit pending_clarification
        if has_pending and cls._looks_like_slot_fill(raw):
            return ConversationalRoute(
                path="analytical_clarification",
                reason_code="PENDING_CLARIFICATION_MATCH",
                can_materialize=can_materialize,
                has_active_asset=has_asset,
                inherited_subjects=list(active_pair[:8]),
            )

        # 5) contextual_follow_up (analytical continuity — not social)
        from app.lottery.ai.active_investigation.contextual_follow_up import (
            ContextualFollowUpResolver,
        )

        if inv_active or can_materialize:
            if ContextualFollowUpResolver.is_short_contextual_follow_up(raw):
                return ConversationalRoute(
                    path="contextual_follow_up",
                    reason_code="CONTEXTUAL_ANALYTICAL_FOLLOWUP",
                    can_materialize=can_materialize,
                    has_active_asset=has_asset,
                    inherited_subjects=list(active_pair[:8]),
                )

        # 6) default_research
        return ConversationalRoute(
            path="default_research",
            reason_code="default_research",
            can_materialize=can_materialize,
            has_active_asset=has_asset,
            inherited_subjects=list(active_pair[:8]) if inv_active else [],
        )

    # --- legacy Path A / Path B surface (Hermes callers) ---
    @classmethod
    def route_path_ab(
        cls,
        message: str,
        *,
        state: Any,
        investigation: Any | None,
    ) -> ConversationalRoute:
        """Binary Path A (research) vs Path B (asset) for Hermes wiring."""
        r = cls.route(message, state=state, investigation=investigation)
        if r.path == "social_chitchat":
            return r
        if r.path == "workspace_action":
            return ConversationalRoute(
                path="asset_operation",
                workspace_action=r.workspace_action,
                reason_code=r.reason_code or "WORKSPACE_ACTION_MATCH",
                can_materialize=r.can_materialize,
                has_active_asset=r.has_active_asset,
                inherited_subjects=list(r.inherited_subjects or []),
            )
        return ConversationalRoute(
            path="new_investigation",
            reason_code=r.reason_code or "new_investigation_intent",
            can_materialize=r.can_materialize,
            has_active_asset=r.has_active_asset,
            inherited_subjects=list(r.inherited_subjects or []),
        )

    @classmethod
    def _looks_like_slot_fill(cls, raw: str) -> bool:
        """User supplies a requested param (lottery / number), not social ack."""
        from app.lottery.ai.official_lottery_scope import canonicalize_lottery_name

        text = (raw or "").strip()
        if not text or len(text) > 60:
            return False
        if detect_social_chitchat(text):
            return False
        nums = extract_subject_numbers(text)
        if nums:
            return True
        # lottery name fill: "Gana Más", "Loteka", "Solo Gana Más"
        if canonicalize_lottery_name(text) or re_lottery_token(text):
            return True
        return False

    @classmethod
    def _is_new_investigation(
        cls,
        raw: str,
        *,
        active_pair: list[str],
        inv_active: bool,
    ) -> bool:
        import re

        from app.lottery.ai.investigation_workspace.speech_acts import (
            _EXPORT,
            _FACTUAL_BLOCK,
            _FILTER_VERB,
            _PAGE,
            _SHOW,
            _SOLO_LOTTERY,
            _SORT,
            _bare_en_lottery,
            _is_explicit_boot,
        )

        if re.search(r"^\s*nueva\s+conversaci[oó]n\s*$", raw or "", re.I):
            return True
        if _FACTUAL_BLOCK.search(raw):
            return True
        if _bare_en_lottery(raw):
            return True

        msg_nums = extract_subject_numbers(raw)
        if len(msg_nums) >= 2 and (
            not inv_active
            or sorted(msg_nums[:2]) != sorted([str(x) for x in active_pair[:2]])
        ):
            if _is_explicit_boot(raw):
                return False
            return True

        if (
            inv_active
            and len(msg_nums) == 1
            and active_pair
            and msg_nums[0] not in {str(x) for x in active_pair}
        ):
            if (
                _PAGE.search(raw)
                or _SHOW.search(raw)
                or _SORT.search(raw)
                or _EXPORT.search(raw)
                or _FILTER_VERB.search(raw)
                or _SOLO_LOTTERY.search(raw)
            ):
                return False
            from app.lottery.ai.active_investigation.contextual_follow_up import (
                ContextualFollowUpResolver,
            )

            if ContextualFollowUpResolver.is_short_contextual_follow_up(raw):
                return False
            # "Ahora analiza el 35" / topic switch
            return True

        return False


def re_lottery_token(text: str) -> bool:
    import re

    return bool(
        re.search(
            r"\b(loteka|nacional|leidsa|real|gana\s*m[aá]s|anguila|florida|cash\s*4\s*life)\b",
            text or "",
            re.I,
        )
    )
