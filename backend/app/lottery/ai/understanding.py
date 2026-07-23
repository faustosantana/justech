"""Lottery IA 4.0 — hybrid understanding + slot fill over deterministic intent."""

from __future__ import annotations

import re
from typing import Any

from app.lottery.ai.conversation_state import (
    ConversationState,
    UnderstandingResult,
    smart_clarify,
)
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import ResolvedIntent, resolve_intent, _extract_number, _extract_lotteries


def _ctx_from_state(state: ConversationState) -> LotterySessionContext:
    return LotterySessionContext(
        last_lottery=state.active_lotteries[0] if state.active_lotteries else None,
        compared_lotteries=list(state.active_lotteries[1:] if len(state.active_lotteries) > 1 else []),
        base_date=state.date_context,
        last_draw_count=state.draw_count_context,
        last_numbers=list(state.active_numbers),
        last_tool=state.last_tool,
        last_query_semantics=state.last_intent,
        last_from_date=(state.range_context or {}).get("from") if state.range_context else None,
        last_to_date=(state.range_context or {}).get("to") if state.range_context else None,
    )


def _apply_pending_fill(text: str, state: ConversationState) -> ConversationState | None:
    """If waiting for slots, interpret short replies as slot fills."""
    if not state.pending_intent or not state.pending_slots:
        return None
    lots = _extract_lotteries(text)
    number = _extract_number(text)
    updated = state.model_copy(deep=True)
    filled = False

    # Scope: todas / todas las loterías
    if re.search(r"\btodas\b|todas las loter", text, re.I):
        updated.scope = "all"
        if "lottery" in updated.pending_slots:
            updated.pending_slots = [s for s in updated.pending_slots if s != "lottery"]
        filled = True

    if lots:
        for lot in lots:
            if lot not in updated.active_lotteries:
                updated.active_lotteries.append(lot)
        if "lottery" in updated.pending_slots:
            updated.pending_slots = [s for s in updated.pending_slots if s != "lottery"]
        filled = True
        updated.scope = "multiple" if len(updated.active_lotteries) > 1 else "single"

    if number:
        updated.active_numbers = [number]
        if "number" in updated.pending_slots:
            updated.pending_slots = [s for s in updated.pending_slots if s != "number"]
        filled = True

    # Period shortcuts
    m = re.search(r"[uú]ltimos?\s+(\d+)\s+sorteos?", text, re.I)
    if m:
        updated.draw_count_context = int(m.group(1))
        if "period" in updated.pending_slots or "draw_count" in updated.pending_slots:
            updated.pending_slots = [s for s in updated.pending_slots if s not in {"period", "draw_count"}]
        filled = True
    elif re.search(r"historial|todo el hist[oó]rico|todos los sorteos", text, re.I):
        updated.draw_count_context = 10000
        updated.pending_slots = [s for s in updated.pending_slots if s not in {"period", "draw_count"}]
        filled = True
    elif re.search(r"[uú]ltimo\s+a[nñ]o|este a[nñ]o", text, re.I):
        updated.draw_count_context = 365
        updated.pending_slots = [s for s in updated.pending_slots if s not in {"period", "draw_count"}]
        filled = True

    # Lottery alias short answers: "En la Real", "Leidsa"
    if not lots and "lottery" in state.pending_slots:
        alias = re.sub(r"^(en\s+la\s+|en\s+el\s+|en\s+)", "", text.strip(), flags=re.I)
        guessed = _extract_lotteries(alias) or _extract_lotteries(text)
        if guessed:
            updated.active_lotteries = guessed
            updated.pending_slots = [s for s in updated.pending_slots if s != "lottery"]
            filled = True

    return updated if filled else None


def understand(raw: str, state: ConversationState) -> tuple[UnderstandingResult, ConversationState]:
    """Hybrid understanding: pending slot fill → deterministic intent → smart clarify."""
    text = (raw or "").strip()
    # Follow-ups like "y en Leidsa", "compáralas"
    follow = _detect_follow_up(text, state)
    if follow:
        return follow

    filled = _apply_pending_fill(text, state)
    working = filled or state

    # If pending intent ready after fill → execute
    if working.pending_intent and not working.pending_slots:
        return _resume_pending(working)

    ctx = _ctx_from_state(working)
    intent = resolve_intent(text, ctx)
    result = _map_resolved(intent, working, text)

    # Improve last_occurrence clarify when number known
    if result.intent == "last_occurrence" and result.needs_clarification:
        number = (result.numbers[0] if result.numbers else None) or (
            working.active_numbers[0] if working.active_numbers else None
        )
        if number and "lottery" in result.missing_slots:
            result.clarification_question = smart_clarify(
                intent="last_occurrence", number=number, missing=["lottery"]
            )
            working.pending_intent = "last_occurrence"
            working.pending_slots = ["lottery"]
            working.pending_params = {"number": number}
            working.active_numbers = [number]
            working.clarification_question = result.clarification_question
            result.confidence = max(result.confidence, 0.85)

    # Frequency / hot without lottery or period
    if result.intent in {"frequency", "hot_numbers", "cold_numbers", "overdue_numbers"}:
        missing = list(result.missing_slots)
        if not result.lotteries and not working.active_lotteries and working.scope != "all":
            if "lottery" not in missing:
                missing.append("lottery")
        if result.draw_count is None and working.draw_count_context is None and "draw_count" not in missing:
            if result.intent == "frequency":
                missing.append("period")
        if missing and not result.params.get("lottery"):
            result.needs_clarification = True
            result.missing_slots = missing
            result.clarification_question = smart_clarify(
                intent=result.intent,
                lottery=None,
                missing=missing,
            )
            working.pending_intent = result.intent
            working.pending_slots = missing
            working.pending_params = dict(result.params)
            working.clarification_question = result.clarification_question

    return result, working


def _detect_follow_up(text: str, state: ConversationState) -> tuple[UnderstandingResult, ConversationState] | None:
    low = text.lower().strip()
    working = state.model_copy(deep=True)

    # "compáralas" / "comparalas" / "compara las dos"
    if re.search(r"comp[aá]ralas|compara(r)?\s+las|comparaci[oó]n", low) and state.active_numbers:
        lots = list(state.active_lotteries)
        if len(lots) >= 2 or state.scope == "all":
            return (
                UnderstandingResult(
                    intent="compare_numbers",
                    lotteries=lots,
                    numbers=list(state.active_numbers),
                    scope="multiple" if lots else "all",
                    tool=LotteryToolName.COMPARE_LOTTERIES.value,
                    params={
                        "lotteries": lots,
                        "number": state.active_numbers[0],
                        "mode": "number_compare",
                    },
                    plan=["resolve_lotteries", "last_or_frequency_per_lottery", "summarize"],
                    confidence=0.88,
                    source="follow_up",
                ),
                working,
            )
        working.pending_intent = "compare_numbers"
        working.pending_slots = ["lottery"]
        working.pending_params = {"number": state.active_numbers[0]}
        q = smart_clarify(
            intent="compare_numbers",
            number=state.active_numbers[0],
            missing=["lottery"],
        )
        working.clarification_question = q
        return (
            UnderstandingResult(
                intent="compare_numbers",
                numbers=list(state.active_numbers),
                needs_clarification=True,
                missing_slots=["lottery"],
                clarification_question=q,
                confidence=0.8,
                source="follow_up",
            ),
            working,
        )

    # "y en Leidsa" / "en la Nacional" — require explicit "en …" lottery switch
    if (
        state.active_numbers
        and re.search(r"(^|\b)(y\s+)?en\s+(la\s+|el\s+)?", low)
        and state.last_intent
        in {"last_occurrence", "number_history", "frequency", "hot_numbers", "cold_numbers", "overdue_numbers"}
    ):
        lots = _extract_lotteries(text)
        if lots:
            # Keep prior lotteries for later "compáralas"
            merged = list(dict.fromkeys([*state.active_lotteries, *lots]))
            working.active_lotteries = merged
            working.scope = "multiple" if len(merged) > 1 else "single"
            working.pending_slots = []
            intent_name = state.last_intent or "last_occurrence"
            number = state.active_numbers[0]
            tool = {
                "last_occurrence": LotteryToolName.GET_LAST_OCCURRENCE.value,
                "number_history": LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                "frequency": LotteryToolName.CALCULATE_FREQUENCIES.value,
                "hot_numbers": LotteryToolName.GET_HOT_COLD.value,
                "cold_numbers": LotteryToolName.GET_HOT_COLD.value,
                "overdue_numbers": LotteryToolName.GET_HOT_COLD.value,
            }.get(intent_name, LotteryToolName.GET_LAST_OCCURRENCE.value)
            params: dict[str, Any] = {"lottery": lots[0], "number": number}
            if intent_name in {"hot_numbers", "cold_numbers", "overdue_numbers"}:
                focus = "hot" if intent_name == "hot_numbers" else (
                    "cold_interval" if intent_name == "overdue_numbers" else "cold_frequency"
                )
                params = {
                    "lottery": lots[0],
                    "focus": focus,
                    "window_draws": state.draw_count_context or 30,
                }
            if intent_name == "frequency":
                params = {
                    "lottery": lots[0],
                    "limit": 10,
                    "window_draws": state.draw_count_context or 30,
                }
            return (
                UnderstandingResult(
                    intent=intent_name,
                    lotteries=lots,
                    numbers=[number],
                    tool=tool,
                    params=params,
                    confidence=0.9,
                    source="follow_up",
                ),
                working,
            )

    # "ahora dime cuáles están más atrasados" — keep lottery + window
    if re.search(r"atrasad|m[aá]s tiempo sin|fr[ií]os?", low) and state.active_lotteries:
        if state.last_intent in {"frequency", "hot_numbers", "cold_numbers", "overdue_numbers"} or True:
            lot = state.active_lotteries[0]
            window = state.draw_count_context or 30
            focus = "cold_interval" if re.search(r"atrasad|sin aparecer|sin salir", low) else "cold_frequency"
            if re.search(r"calientes?", low):
                focus = "hot"
            return (
                UnderstandingResult(
                    intent="overdue_numbers" if focus == "cold_interval" else "cold_numbers",
                    lotteries=[lot],
                    draw_count=window,
                    metric=focus,
                    tool=LotteryToolName.GET_HOT_COLD.value,
                    params={"lottery": lot, "focus": focus, "window_draws": window},
                    confidence=0.86,
                    source="follow_up",
                ),
                working,
            )
    return None


def _resume_pending(state: ConversationState) -> tuple[UnderstandingResult, ConversationState]:
    intent = state.pending_intent or "unsupported"
    number = state.pending_params.get("number") or (state.active_numbers[0] if state.active_numbers else None)
    lottery = state.active_lotteries[0] if state.active_lotteries else None
    working = state.model_copy(deep=True)
    working.pending_intent = None
    working.pending_slots = []
    working.clarification_question = None

    if intent == "last_occurrence" and number and (lottery or state.scope == "all"):
        if state.scope == "all":
            return (
                UnderstandingResult(
                    intent="last_occurrence",
                    numbers=[number],
                    scope="all",
                    tool="lottery_compare_last_occurrence_all",
                    params={"number": number, "scope": "all"},
                    plan=["list_lotteries", "last_occurrence_each", "sort_by_date", "summarize"],
                    confidence=0.9,
                    source="follow_up",
                ),
                working,
            )
        return (
            UnderstandingResult(
                intent="last_occurrence",
                lotteries=[lottery] if lottery else [],
                numbers=[number],
                tool=LotteryToolName.GET_LAST_OCCURRENCE.value,
                params={"lottery": lottery, "number": number},
                confidence=0.92,
                source="follow_up",
            ),
            working,
        )

    if intent in {"frequency", "hot_numbers"} and lottery:
        window = state.draw_count_context or 30
        if intent == "hot_numbers" or state.metric_context == "hot":
            return (
                UnderstandingResult(
                    intent="hot_numbers",
                    lotteries=[lottery],
                    draw_count=window,
                    tool=LotteryToolName.GET_HOT_COLD.value,
                    params={"lottery": lottery, "focus": "hot", "window_draws": window},
                    confidence=0.9,
                    source="follow_up",
                ),
                working,
            )
        return (
            UnderstandingResult(
                intent="frequency",
                lotteries=[lottery],
                draw_count=window,
                tool=LotteryToolName.CALCULATE_FREQUENCIES.value,
                params={"lottery": lottery, "limit": 10, "window_draws": window},
                confidence=0.9,
                source="follow_up",
            ),
            working,
        )

    return (
        UnderstandingResult(
            intent="unsupported",
            needs_clarification=True,
            clarification_question="¿Puedes reformular la consulta?",
            confidence=0.2,
            source="follow_up",
        ),
        working,
    )


def _map_resolved(
    intent: ResolvedIntent, state: ConversationState, text: str
) -> UnderstandingResult:
    lots = []
    if intent.params.get("lottery"):
        lots = [str(intent.params["lottery"])]
    elif intent.params.get("lotteries"):
        lots = [str(x) for x in intent.params["lotteries"]]
    numbers = []
    if intent.params.get("number"):
        numbers = [str(intent.params["number"])]
    # Also extract from text for clarify paths
    if not numbers:
        n = _extract_number(text)
        if n:
            numbers = [n]
    if not lots:
        lots = _extract_lotteries(text)

    intent_name = "unsupported"
    if intent.kind == "clarify":
        # Infer intent from text for better clarifications
        if re.search(r"[uú]ltima\s+vez|cu[aá]ndo fue la [uú]ltima", text, re.I):
            intent_name = "last_occurrence"
        elif re.search(r"m[aá]s frecuentes|frecuen", text, re.I):
            intent_name = "frequency"
        elif re.search(r"calientes?", text, re.I):
            intent_name = "hot_numbers"
        missing = []
        msg = (intent.clarify_message or "").lower()
        if "loter" in msg:
            missing.append("lottery")
        if "fecha" in msg:
            missing.append("date")
        if "n[uú]mero" in msg or "numero" in msg:
            missing.append("number")
        # Fix over-asking: if number already known, drop number from missing
        if numbers and "number" in missing:
            missing = [m for m in missing if m != "number"]
        # last occurrence never needs date
        if intent_name == "last_occurrence" and "date" in missing:
            missing = [m for m in missing if m != "date"]
        if not missing and intent_name == "last_occurrence" and not lots:
            missing = ["lottery"]
        q = smart_clarify(
            intent=intent_name,
            number=numbers[0] if numbers else None,
            missing=missing or ["lottery"],
        )
        return UnderstandingResult(
            intent=intent_name,
            lotteries=lots,
            numbers=numbers,
            missing_slots=missing or ["lottery"],
            needs_clarification=True,
            clarification_question=q,
            confidence=0.75,
            source="rules",
        )

    if intent.kind in {"prediction_refused", "injection_refused", "refuse"}:
        return UnderstandingResult(
            intent="unsupported",
            needs_clarification=False,
            clarification_question=intent.refuse_message,
            confidence=1.0,
            source="rules",
            params={"refuse": True, "message": intent.refuse_message},
        )

    tool = intent.tool.value if intent.tool else None
    mapping = {
        LotteryToolName.GET_LAST_OCCURRENCE.value: "last_occurrence",
        LotteryToolName.GET_RESULT_BY_DATE.value: "result_by_date",
        LotteryToolName.GET_NUMBER_OCCURRENCES.value: "number_history",
        LotteryToolName.GET_TOP_NUMBERS.value: "frequency",
        LotteryToolName.GET_HOT_COLD.value: "hot_numbers",
        LotteryToolName.COMPARE_LOTTERIES.value: "compare_lotteries",
        LotteryToolName.GET_MISSING_TODAY.value: "missing_results",
        LotteryToolName.GET_SYNC_STATUS.value: "sync_status",
        LotteryToolName.GET_SYNC_WINDOWS.value: "next_sync",
        LotteryToolName.GET_FOLLOWING_DRAWS.value: "draw_sequence",
        LotteryToolName.GET_FOLLOWING_DAYS.value: "draw_sequence",
        LotteryToolName.GET_COVERAGE.value: "data_coverage",
        LotteryToolName.GET_DATA_QUALITY.value: "data_quality",
    }
    if tool:
        intent_name = mapping.get(tool, "general_domain_question")
    if intent.params.get("focus") == "cold_interval":
        intent_name = "overdue_numbers"
    elif intent.params.get("focus") == "cold_frequency":
        intent_name = "cold_numbers"

    return UnderstandingResult(
        intent=intent_name,
        lotteries=lots,
        numbers=numbers,
        date=intent.params.get("date"),
        draw_count=intent.params.get("window_draws") or intent.params.get("count"),
        tool=tool,
        params=dict(intent.params or {}),
        confidence=0.8 if tool else 0.4,
        source="rules",
    )
