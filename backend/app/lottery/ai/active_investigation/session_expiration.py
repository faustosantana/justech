"""SessionExpirationManager — 10-minute investigation TTL."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.lottery.ai.active_investigation.session import (
    TTL_SECONDS,
    ActiveInvestigationSession,
)


def _is_official_or_empty(name: str | None) -> bool:
    from app.lottery.ai.official_lottery_scope import is_official_lottery

    if not name or not str(name).strip():
        return True
    return is_official_lottery(str(name))


class SessionExpirationManager:
    """Load/expire/renew active investigation without relying on LLM memory."""

    def __init__(self, *, ttl_seconds: int = TTL_SECONDS):
        self.ttl_seconds = int(ttl_seconds)

    def load_from_state(self, state: Any) -> ActiveInvestigationSession | None:
        raw = getattr(state, "active_investigation", None) or {}
        if isinstance(raw, ActiveInvestigationSession):
            inv = raw
        else:
            inv = ActiveInvestigationSession.from_store(raw if isinstance(raw, dict) else None)
        if inv is None:
            return None
        if inv.is_expired():
            inv.mark_expired()
            return inv
        return inv

    def apply_on_turn_start(self, state: Any) -> tuple[Any, ActiveInvestigationSession | None, dict[str, Any]]:
        """Expire silently-stale investigations; do not reuse without a fresh topic."""
        from app.lottery.ai.official_lottery_scope import evidence_uses_non_official_lotteries

        meta: dict[str, Any] = {"ttl_seconds": self.ttl_seconds}
        inv = self.load_from_state(state)
        if inv is None:
            meta["status"] = "none"
            return state, None, meta
        if inv.is_expired():
            inv.mark_expired()
            state.active_investigation = {}
            # Drop sticky same_day so expired context cannot silently drive tools
            if str(getattr(state, "active_relation", "") or "") == "same_day":
                state.active_relation = None
                filters = dict(getattr(state, "active_filters", None) or {})
                filters.pop("relation", None)
                state.active_filters = filters
            meta["status"] = "expired_cleared"
            meta["expired_investigation_id"] = inv.investigation_id
            return state, None, meta
        # Invalidate pre-hotfix / global-catalog evidence so answers are recalculated
        if evidence_uses_non_official_lotteries(dict(inv.evidence or {})) or evidence_uses_non_official_lotteries(
            dict(inv.last_event or {})
        ) or any(not _is_official_or_empty(x) for x in (inv.lotteries or [])):
            inv.mark_expired()
            state.active_investigation = {}
            if str(getattr(state, "active_relation", "") or "") == "same_day":
                # Keep subjects sticky but force research with official scope
                pass
            meta["status"] = "invalidated_out_of_scope"
            meta["expired_investigation_id"] = inv.investigation_id
            return state, None, meta
        meta["status"] = "active"
        meta["investigation_id"] = inv.investigation_id
        meta["expires_at"] = inv.expires_at.isoformat()
        return state, inv, meta

    def renew(self, inv: ActiveInvestigationSession) -> ActiveInvestigationSession:
        return inv.touch(ttl_seconds=self.ttl_seconds)

    @staticmethod
    def seconds_remaining(inv: ActiveInvestigationSession, *, now: datetime | None = None) -> float:
        ts = now or datetime.now(timezone.utc)
        exp = inv.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return max(0.0, (exp - ts).total_seconds())
