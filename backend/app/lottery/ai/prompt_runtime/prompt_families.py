"""Prompt version families — active status is scoped per family, never globally.

LOTTERY_ANALYST_SYSTEM_V6 and LOTTERY_ANALYST_REASONING_STUDIO are independent
families and may both be ``active`` at the same time.
"""
from __future__ import annotations

from typing import Any, Protocol

from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7 import REASONING_STUDIO_NAME
from app.lottery.ai.prompts.lottery_analyst_system_v6 import ANALYST_PROMPT_NAME

FAMILY_REASONING_STUDIO = "reasoning_studio"
FAMILY_ANALYST_V6 = "analyst_v6"
FAMILY_MOTOR_V5 = "motor_v5"


class _PromptRow(Protocol):
    id: Any
    name: str | None
    version: str | None
    status: str | None


def prompt_family_key(*, name: str | None, version: str | None) -> str:
    """Return a stable family key for a prompt row."""
    n = (name or "").strip()
    v = (version or "").strip()
    if n == REASONING_STUDIO_NAME:
        return FAMILY_REASONING_STUDIO
    if n == ANALYST_PROMPT_NAME or v == "v6":
        return FAMILY_ANALYST_V6
    if v == "v5" or n in {"lottery_assistant_system_v5", "LOTTERY_ASSISTANT_SYSTEM_V5"}:
        return FAMILY_MOTOR_V5
    if n:
        return f"name:{n}"
    if v:
        return f"version:{v}"
    return "unknown"


def enforce_single_active_in_family(
    rows: list[Any],
    *,
    family: str,
    keep_id: Any,
    demote_to: str = "archived",
) -> list[Any]:
    """Ensure at most one ``active`` row within ``family``; keep ``keep_id`` active.

    Rows belonging to other families are never mutated.
    Returns the list of rows whose status was changed.
    """
    changed: list[Any] = []
    for row in rows:
        if prompt_family_key(name=getattr(row, "name", None), version=getattr(row, "version", None)) != family:
            continue
        rid = getattr(row, "id", None)
        if rid == keep_id:
            if getattr(row, "status", None) != "active":
                row.status = "active"
                changed.append(row)
            continue
        if getattr(row, "status", None) == "active":
            row.status = demote_to
            changed.append(row)
    return changed


def plan_seed_status_mutations(
    rows: list[dict[str, Any]],
    *,
    v6_id: Any,
) -> list[tuple[Any, str, str]]:
    """Pure planner used by tests: (id, old_status, new_status) for ensure_seeded V6 pass.

    - V6 keep_id stays/becomes active within analyst_v6 family.
    - Other active analyst_v6 peers → archived.
    - V5 → motor (motor family special).
    - Reasoning Studio and other families untouched.
    """
    mutations: list[tuple[Any, str, str]] = []

    class _R:
        def __init__(self, d: dict[str, Any]):
            self.id = d["id"]
            self.name = d.get("name")
            self.version = d.get("version")
            self.status = d.get("status")

    objs = [_R(d) for d in rows]
    for o in objs:
        if o.version == "v5" and o.status != "motor":
            old = o.status or ""
            o.status = "motor"
            mutations.append((o.id, old, "motor"))

    before = {o.id: o.status for o in objs}
    enforce_single_active_in_family(objs, family=FAMILY_ANALYST_V6, keep_id=v6_id)
    for o in objs:
        if before.get(o.id) != o.status:
            # avoid duplicate if already recorded as v5→motor
            if not any(m[0] == o.id and m[2] == o.status for m in mutations):
                mutations.append((o.id, before.get(o.id) or "", o.status or ""))
    return mutations
