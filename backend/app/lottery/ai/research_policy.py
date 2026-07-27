"""Fase X.1 — Default Research Policy (v2.3.2).

Policy-only layer: when to investigate vs when to clarify.
Does NOT modify Motor, Ranking, Histórico, Research Engine, Discovery,
Knowledge Engine, Planner, Conversation Brain, Prompt Maestro.

Golden rule: if a reasonable interpretation allows research → INVESTIGATE.
Clarify ONLY when missing data materially blocks the investigation.
"""

from __future__ import annotations

from typing import Any

from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

RESEARCH_POLICY_VERSION = "2.3.2"

# Slots that MUST NOT block research by default (form bias eliminated).
NON_MATERIAL_SLOTS = frozenset(
    {
        "lottery",
        "date",
        "period",
        "draw_count",
        "position",
        "position_scope",
        "occurrence_limit",
    }
)

# Slots that can materially block (ask only these when empty).
MATERIAL_SLOTS = frozenset({"number", "compare_with", "query"})

RULES_CHANGED = (
    "no_lottery_clarify_when_number_present",
    "no_date_clarify_by_default",
    "no_position_clarify_by_default",
    "default_scope_all_historical",
    "default_position_any",
    "greeting_never_tools",
    "general_chat_never_tools",
    "last_occurrence_all_lotteries_when_number",
    "count_all_historical_when_number",
    "analyze_no_clarify",
    "compare_use_context",
    "last_without_number_asks_number_only",
    "strip_non_material_missing_slots",
    "frequency_no_lottery_period_gate",
    "compound_defaults_to_all_not_clarify",
    "generic_fallback_no_fecha_bias",
)

GREETING_REPLY_V232 = (
    "Hola, estoy muy bien. ¿Qué te gustaría investigar hoy?"
)

GENERAL_CHAT_REPLY_V232 = (
    "De acuerdo. Cuando quieras, dime qué número, comparación o caso "
    "quieres que investigue en el histórico."
)


def default_lotteries() -> list[str]:
    return list(DEFAULT_ALL_HISTORY_LOTTERIES)


def is_material_missing(slot: str) -> bool:
    return slot in MATERIAL_SLOTS


def filter_material_slots(missing: list[str] | None) -> list[str]:
    """Keep only slots that truly block research."""
    out: list[str] = []
    for s in missing or []:
        if s in MATERIAL_SLOTS and s not in out:
            out.append(s)
    return out


def can_investigate_without(
    *,
    numbers: list[str] | None = None,
    active_numbers: list[str] | None = None,
    missing: list[str] | None = None,
    intent: str | None = None,
) -> bool:
    """True when a reasonable investigation path exists."""
    nums = list(numbers or []) or list(active_numbers or [])
    material = filter_material_slots(missing)
    if intent in {"greeting", "general_chat", "help", "GREETING", "GENERAL_CHAT", "HELP"}:
        return False
    # Number-bearing research never blocked by lottery/date/position
    if nums:
        return True
    # Follow-ups with active context
    if active_numbers and intent in {
        "follow_up",
        "FOLLOW_UP",
        "last_occurrence",
        "compare_numbers",
        "COMPARE",
        "EXPLAIN",
        "explain_metric",
    }:
        return True
    # Only material blockers remain
    return len(material) == 0


def apply_to_understanding(result: Any, state: Any) -> Any:
    """Post-process UnderstandingResult: strip form bias, prefer research."""
    if result is None:
        return result
    intent = str(getattr(result, "intent", "") or "")
    if intent in {"greeting", "general_chat", "help"}:
        result.needs_clarification = False
        result.missing_slots = []
        return result

    numbers = list(getattr(result, "numbers", None) or [])
    active = list(getattr(state, "active_numbers", None) or []) if state is not None else []
    missing = list(getattr(result, "missing_slots", None) or [])

    # Drop non-material slots always under default research policy
    material = filter_material_slots(missing)
    # If we have a number (message or memory), never ask for number
    if numbers or active:
        material = [m for m in material if m != "number"]
        if not numbers and active:
            result.numbers = list(active)

    result.missing_slots = material
    params = dict(getattr(result, "params", None) or {})

    if material:
        result.needs_clarification = True
        # Number-only ask — never append lottery/date language
        if material == ["number"]:
            result.clarification_question = "¿La última vez / el análisis de cuál número?"
            if "última" in (result.clarification_question or "").lower() or intent in {
                "last_occurrence",
                "DATE",
            }:
                result.clarification_question = "¿La última vez de cuál número?"
        return result

    # Enough to investigate
    result.needs_clarification = False
    result.clarification_question = None
    if not result.lotteries and getattr(state, "scope", None) != "single":
        result.scope = "all"
        params.setdefault("all_historical", True)
        params.setdefault("lotteries", default_lotteries())
        params.setdefault("nlp_policy", RESEARCH_POLICY_VERSION)
    result.params = params
    return result


def rewrite_resolved_clarify(intent: Any, *, has_number: bool, active_number: str | None = None) -> Any:
    """Rewrite ResolvedIntent clarify→tool when lottery/position/date were the only ask."""
    if getattr(intent, "kind", None) != "clarify":
        return intent
    pending = list((intent.params or {}).get("pending_slots") or [])
    msg = (intent.clarify_message or "").lower()
    number = (intent.params or {}).get("number") or active_number
    if not number and has_number:
        number = (intent.params or {}).get("numbers", [None])[0] if isinstance((intent.params or {}).get("numbers"), list) else None

    # Position-only clarify → investigate any position
    if pending == ["position_scope"] or (
        "posici" in msg and "loter" not in msg and (number or has_number)
    ):
        from app.services.lottery_ai_contracts import LotteryToolName

        intent.kind = "tool"
        intent.clarify_message = None
        intent.tool = LotteryToolName.COMPARE_LOTTERIES if not (intent.params or {}).get("lottery") else LotteryToolName.GET_NUMBER_OCCURRENCES
        params = dict(intent.params or {})
        params["position_scope"] = "any_position"
        params["position"] = None
        params["all_historical"] = True
        params["nlp_policy"] = RESEARCH_POLICY_VERSION
        if number:
            params["number"] = number
        if intent.tool == LotteryToolName.COMPARE_LOTTERIES:
            params["lotteries"] = default_lotteries()
            params["mode"] = "number_compare"
        intent.params = params
        intent.structured_type = "lottery_comparison" if intent.tool == LotteryToolName.COMPARE_LOTTERIES else "lottery_result"
        return intent

    # Lottery-only (or lottery+date) clarify with number → all historical
    lottery_bias = (
        pending == ["lottery"]
        or set(pending) <= {"lottery", "date", "period", "draw_count", "position", "position_scope"}
        or ("loter" in msg and number)
    )
    if lottery_bias and number:
        from app.services.lottery_ai_contracts import LotteryToolName

        # Prefer last-occurrence wording → compare last across lotteries
        if "ultima" in msg or "última" in (intent.clarify_message or "") or "aparición" in msg:
            intent.kind = "tool"
            intent.clarify_message = None
            intent.tool = LotteryToolName.COMPARE_LOTTERIES
            intent.params = {
                "number": number,
                "lotteries": default_lotteries(),
                "mode": "number_compare",
                "all_historical": True,
                "nlp_policy": RESEARCH_POLICY_VERSION,
                "pending_slots": [],
            }
            intent.structured_type = "lottery_comparison"
            return intent
        intent.kind = "tool"
        intent.clarify_message = None
        intent.tool = LotteryToolName.COMPARE_LOTTERIES
        intent.params = {
            "number": number,
            "lotteries": default_lotteries(),
            "mode": "number_compare",
            "all_historical": True,
            "nlp_policy": RESEARCH_POLICY_VERSION,
            "pending_slots": [],
        }
        intent.structured_type = "lottery_comparison"
        return intent

    # Date-only bias without number → still need number if it's last/count
    if pending == ["date"] or (pending == ["lottery", "date"] and not number):
        # If no number, ask number only
        intent.params = {**(intent.params or {}), "pending_slots": ["number"]}
        intent.clarify_message = "¿De qué número?"
        return intent

    # Strip non-material pending; if only number left keep clarify
    material = filter_material_slots(pending)
    if not material and number:
        return rewrite_resolved_clarify(
            intent,
            has_number=True,
            active_number=str(number),
        )
    if material == ["number"] and not number:
        intent.params = {**(intent.params or {}), "pending_slots": ["number"]}
        if "ultima" in msg or "cuándo" in msg or "cuando" in msg:
            intent.clarify_message = "¿La última vez de cuál número?"
        else:
            intent.clarify_message = "¿De qué número?"
        return intent
    return intent


def policy_manifest() -> dict[str, Any]:
    return {
        "version": RESEARCH_POLICY_VERSION,
        "philosophy": "investigate_first_clarify_only_when_blocked",
        "non_material_slots": sorted(NON_MATERIAL_SLOTS),
        "material_slots": sorted(MATERIAL_SLOTS),
        "default_scope": "all_historical",
        "default_position": "any",
        "rules_changed": list(RULES_CHANGED),
        "rules_changed_count": len(RULES_CHANGED),
    }
