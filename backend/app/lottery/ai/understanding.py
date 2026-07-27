"""Lottery IA 4.2 — hybrid understanding + slot fill + reference resolution."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.lottery.ai.conversation_state import (
    ConversationState,
    UnderstandingResult,
    smart_clarify,
)
from app.lottery.ai.domain_classifier import classify_domain
from app.lottery.ai.reference_resolver import (
    derive_per_lottery_base_dates,
    resolve_references,
)
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import ResolvedIntent, resolve_intent, _extract_number, _extract_lotteries


def _ctx_from_state(state: ConversationState) -> LotterySessionContext:
    base = state.date_context
    if not base and state.last_occurrences:
        try:
            dates = [
                date.fromisoformat(str(v.date)[:10])
                for v in state.last_occurrences.values()
                if getattr(v, "date", None)
            ]
            if dates:
                base = max(dates)
        except Exception:
            pass
    return LotterySessionContext(
        last_lottery=state.active_lotteries[0] if state.active_lotteries else None,
        compared_lotteries=list(state.active_lotteries[1:] if len(state.active_lotteries) > 1 else []),
        base_date=base,
        last_draw_count=state.draw_count_context,
        last_days=state.calendar_window,
        last_numbers=list(state.active_numbers),
        last_tool=state.last_tool,
        last_query_semantics=state.last_intent,
        last_from_date=(state.range_context or {}).get("from") if state.range_context else None,
        last_to_date=(state.range_context or {}).get("to") if state.range_context else None,
        default_number_position_scope=state.default_number_position_scope or "first_position",
        default_primary_position=int(state.default_primary_position or 1),
        last_analysis=dict(state.last_analysis or {}),
        conversation_summary=state.conversation_summary,
        current_primary_candidate=state.current_primary_candidate,
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
        # Prefer explicit list as the active set when filling lottery slot
        if "lottery" in state.pending_slots:
            updated.active_lotteries = list(dict.fromkeys(lots))
        else:
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

    # Numeric relations: explicit 5 / 10 / 20 / todas
    if "occurrence_limit" in state.pending_slots or state.pending_intent == "numeric_relations":
        from app.services.lottery_intent import _extract_occurrence_limit_params

        lim = _extract_occurrence_limit_params(text)
        if lim:
            updated.pending_params = {**updated.pending_params, **lim}
            updated.pending_slots = [s for s in updated.pending_slots if s != "occurrence_limit"]
            filled = True

    # Lottery alias short answers: "En la Real", "Leidsa"
    if not lots and "lottery" in state.pending_slots:
        alias = re.sub(r"^(en\s+la\s+|en\s+el\s+|en\s+)", "", text.strip(), flags=re.I)
        guessed = _extract_lotteries(alias) or _extract_lotteries(text)
        if guessed:
            updated.active_lotteries = guessed
            updated.pending_slots = [s for s in updated.pending_slots if s != "lottery"]
            filled = True

    if "unit" in state.pending_slots:
        if re.search(r"sorteos?", text, re.I):
            updated.pending_params = {**updated.pending_params, "unit": "draws"}
            updated.pending_slots = [s for s in updated.pending_slots if s != "unit"]
            filled = True
        elif re.search(r"d[ií]as?|calendario", text, re.I):
            updated.pending_params = {**updated.pending_params, "unit": "days"}
            updated.pending_slots = [s for s in updated.pending_slots if s != "unit"]
            filled = True

    return updated if filled else None


def understand(raw: str, state: ConversationState) -> tuple[UnderstandingResult, ConversationState]:
    """Hybrid understanding: domain gate → references → pending fill → intent."""
    text = (raw or "").strip()
    working = state.model_copy(deep=True)

    domain = classify_domain(text)
    if domain.classification in {
        "out_of_domain",
        "restricted_technical",
        "prediction_request",
        "harmful_or_illegal",
    } and not (working.pending_intent and working.pending_slots and len(text.split()) <= 8):
        return (
            UnderstandingResult(
                intent=domain.classification,
                confidence=domain.confidence,
                source="domain",
                domain_class=domain.classification,
                params={"refuse_message": domain.refuse_message},
            ),
            working,
        )

    refs = resolve_references(text, working)
    if refs.get("last_user_reference"):
        working.last_user_reference = refs["last_user_reference"]
    if refs.get("lotteries"):
        working.active_lotteries = list(dict.fromkeys(list(refs["lotteries"]) + [
            x for x in working.active_lotteries if x not in refs["lotteries"]
        ]))
        working.scope = "multiple" if len(working.active_lotteries) > 1 else working.scope
        if working.scope == "unknown":
            working.scope = "multiple" if len(working.active_lotteries) > 1 else "single"
    if refs.get("numbers"):
        working.active_numbers = list(refs["numbers"])
    if refs.get("post_window"):
        pw = refs["post_window"]
        if pw["unit"] == "days":
            working.calendar_window = int(pw["count"])
        else:
            working.draw_count_context = int(pw["count"])

    # Position / multi-query follow-ups must win over post-occurrence clarifiers
    from app.lottery.ai.compound_occurrence import follow_up_any_position, follow_up_replace_numbers

    if follow_up_any_position(text) or follow_up_replace_numbers(text):
        follow_early = _detect_follow_up(text, working)
        if follow_early:
            return follow_early

    post = _detect_post_occurrence(text, working, refs)
    if post:
        return post

    follow = _detect_follow_up(text, working)
    if follow:
        return follow

    filled = _apply_pending_fill(text, working)
    working = filled or working

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


def _detect_post_occurrence(
    text: str,
    state: ConversationState,
    refs: dict[str, Any],
) -> tuple[UnderstandingResult, ConversationState] | None:
    """P0: multi-lottery calendar/draw windows after last occurrence dates."""
    pw = refs.get("post_window")
    low = text.lower()
    if not pw:
        if not re.search(r"despu[eé]s|siguientes|posteriores", low):
            return None
        if not (state.last_occurrences or state.date_context):
            return None
        pw = {
            "unit": "draws" if re.search(r"sorteos?", low) else "days",
            "count": state.calendar_window
            or state.draw_count_context
            or (5 if re.search(r"sorteos?", low) else 7),
            "direction": "before" if re.search(r"\bantes\b", low) else "after",
        }

    lotteries = list(refs.get("lotteries") or state.active_lotteries or [])
    number = (refs.get("numbers") or state.active_numbers or [None])[0]
    if not lotteries:
        return None

    per_dates = derive_per_lottery_base_dates(state, lotteries, number)
    if not per_dates and not state.date_context:
        if number and lotteries:
            working = state.model_copy(deep=True)
            working.active_lotteries = lotteries
            working.active_numbers = [str(number)]
            return (
                UnderstandingResult(
                    intent="last_occurrence",
                    lotteries=lotteries,
                    numbers=[str(number)],
                    scope="multiple" if len(lotteries) > 1 else "single",
                    tool="lottery_compare_last_occurrence_all"
                    if len(lotteries) > 1
                    else LotteryToolName.GET_LAST_OCCURRENCE.value,
                    params={
                        "number": number,
                        "lotteries": lotteries,
                        "lottery": lotteries[0],
                        "then_post_window": pw,
                    },
                    plan=["last_occurrence", "post_window"],
                    confidence=0.82,
                    source="follow_up",
                ),
                working,
            )
        return None

    if not per_dates and state.date_context:
        per_dates = {lot: state.date_context for lot in lotteries}

    working = state.model_copy(deep=True)
    working.active_lotteries = lotteries
    if number:
        working.active_numbers = [str(number)]
    if pw["unit"] == "days":
        working.calendar_window = int(pw["count"])
    else:
        working.draw_count_context = int(pw["count"])
    working.scope = "multiple" if len(lotteries) > 1 else "single"
    working.pending_slots = []
    working.pending_intent = None
    iso_dates = {k: v.isoformat() for k, v in per_dates.items()}
    return (
        UnderstandingResult(
            intent="post_occurrence_window",
            lotteries=lotteries,
            numbers=[str(number)] if number else list(state.active_numbers),
            calendar_days=int(pw["count"]) if pw["unit"] == "days" else None,
            draw_count=int(pw["count"]) if pw["unit"] == "draws" else None,
            scope=working.scope,
            tool="lottery_analyze_post_occurrence_window",
            params={
                "number": number,
                "lotteries": lotteries,
                "per_lottery_dates": iso_dates,
                "unit": pw["unit"],
                "count": int(pw["count"]),
                "direction": pw["direction"],
            },
            per_lottery_dates=iso_dates,
            plan=["post_occurrence_per_lottery", "insights"],
            confidence=0.93,
            source="follow_up",
        ),
        working,
    )


def _detect_follow_up(text: str, state: ConversationState) -> tuple[UnderstandingResult, ConversationState] | None:
    low = text.lower().strip()
    working = state.model_copy(deep=True)

    from app.lottery.ai.compound_occurrence import (
        follow_up_any_position,
        follow_up_replace_numbers,
    )

    # "¿Y en cualquier posición?" — keep multi_queries / numbers / lotteries, widen position
    if follow_up_any_position(text) and (
        state.last_multi_queries or state.last_intent in {
            "multi_last_occurrence",
            "last_occurrence",
            "cross_lottery_last_occurrence",
            "occurrence_in_other_lotteries",
        }
    ):
        queries = []
        for q in state.last_multi_queries or []:
            qq = dict(q)
            qq["position"] = None
            qq["position_scope"] = "any_position"
            queries.append(qq)
        if not queries and state.active_numbers:
            # Rebuild single/multi from memory
            for num in state.active_numbers:
                queries.append(
                    {
                        "number": num,
                        "lotteries": list(state.active_lotteries[:1]) if state.active_lotteries else [],
                        "lotteries_scope": "named" if state.active_lotteries else "defaults_or_clarify",
                        "position": None,
                        "position_scope": "any_position",
                    }
                )
        working.last_position_scope = "any_position"
        working.last_multi_queries = queries
        nums = [str(q.get("number")) for q in queries if q.get("number")]
        return (
            UnderstandingResult(
                intent="multi_last_occurrence" if len(queries) > 1 else "last_occurrence",
                lotteries=list(state.active_lotteries),
                numbers=nums,
                scope="multiple" if len(queries) > 1 else "single",
                tool=LotteryToolName.GET_LAST_OCCURRENCE.value,
                params={
                    "multi_queries": queries,
                    "intent": "multi_last_occurrence" if len(queries) > 1 else "last_occurrence",
                    "position_scope": "any_position",
                    "position": None,
                },
                confidence=0.95,
                source="follow_up",
            ),
            working,
        )

    # "Ahora hazlo con el 57 y el 62" — replace numbers, keep lottery layout
    replaced = follow_up_replace_numbers(text)
    if replaced and state.last_multi_queries:
        new_queries = []
        for i, q in enumerate(state.last_multi_queries):
            qq = dict(q)
            if i < len(replaced):
                qq["number"] = replaced[i]
            new_queries.append(qq)
        # If more numbers than prior queries, ignore extras; if fewer, only update prefix
        working.last_multi_queries = new_queries
        working.active_numbers = replaced[: len(new_queries)]
        return (
            UnderstandingResult(
                intent="multi_last_occurrence",
                lotteries=list(state.active_lotteries),
                numbers=list(working.active_numbers),
                scope="multiple",
                tool=LotteryToolName.GET_LAST_OCCURRENCE.value,
                params={
                    "multi_queries": new_queries,
                    "intent": "multi_last_occurrence",
                    "position_scope": state.last_position_scope or "first_position",
                },
                confidence=0.95,
                source="follow_up",
            ),
            working,
        )

    # "hazlo con el 57" / "ahora con el 57" — swap number, keep lotteries
    if state.active_lotteries and state.last_intent and re.search(
        r"(hazlo|rep[ií]telo|igual).{0,24}(con|para)\s+(el\s+)?\d{1,2}|"
        r"^ahora\s+(el\s+|con\s+el\s+)?\d{1,2}\b|^con\s+el\s+\d{1,2}\b",
        low,
    ):
        number = _extract_number(text)
        if number:
            working.active_numbers = [number]
            lots = list(state.active_lotteries)
            # If previous turn was a post-occurrence window, keep calendar/draws depth
            if state.last_intent == "post_occurrence_window" or state.last_analysis.get(
                "type"
            ) == "post_occurrence_window":
                working.last_occurrences = {}
                return (
                    UnderstandingResult(
                        intent="last_occurrence",
                        lotteries=lots,
                        numbers=[number],
                        scope="multiple" if len(lots) > 1 else "single",
                        tool="lottery_compare_last_occurrence_all"
                        if len(lots) > 1
                        else LotteryToolName.GET_LAST_OCCURRENCE.value,
                        params={
                            "number": number,
                            "lotteries": lots,
                            "lottery": lots[0],
                            "then_post_window": True,
                            "calendar_days": state.calendar_window or 7,
                            "unit": "days" if state.calendar_window else "draws",
                            "count": int(
                                state.calendar_window or state.draw_count_context or 7
                            ),
                        },
                        calendar_days=state.calendar_window,
                        draw_count=state.draw_count_context,
                        plan=["last_occurrence_each", "post_occurrence_window"],
                        confidence=0.9,
                        source="follow_up",
                    ),
                    working,
                )
            return (
                UnderstandingResult(
                    intent="last_occurrence",
                    lotteries=lots,
                    numbers=[number],
                    scope="multiple" if len(lots) > 1 else "single",
                    tool="lottery_compare_last_occurrence_all"
                    if len(lots) > 1
                    else LotteryToolName.GET_LAST_OCCURRENCE.value,
                    params={
                        "number": number,
                        "lotteries": lots,
                        "lottery": lots[0],
                    },
                    confidence=0.9,
                    source="follow_up",
                ),
                working,
            )

    # "¿en cuál se repitió el 24?" — reuse last post-occurrence / active lotteries
    if state.active_lotteries and (
        state.last_intent == "post_occurrence_window" or state.last_analysis.get("type") == "post_occurrence_window"
    ) and re.search(r"repiti[oó]|reapareci[oó]|volvi[oó]\s+a\s+salir|sali[oó]\s+de\s+nuevo", low):
        number = _extract_number(text) or (state.active_numbers[0] if state.active_numbers else None)
        working.active_numbers = [number] if number else list(state.active_numbers)
        return (
            UnderstandingResult(
                intent="post_occurrence_window",
                lotteries=list(state.active_lotteries),
                numbers=[number] if number else list(state.active_numbers),
                calendar_days=state.calendar_window,
                draw_count=state.draw_count_context,
                scope="multiple" if len(state.active_lotteries) > 1 else "single",
                tool="lottery_analyze_post_occurrence_window",
                params={
                    "number": number,
                    "lotteries": list(state.active_lotteries),
                    "per_lottery_dates": {
                        k: v.date for k, v in state.last_occurrences.items()
                    },
                    "unit": "days" if state.calendar_window else "draws",
                    "count": int(state.calendar_window or state.draw_count_context or 7),
                    "direction": "after",
                    "focus": "reappearance",
                },
                per_lottery_dates={k: v.date for k, v in state.last_occurrences.items()},
                confidence=0.9,
                source="follow_up",
            ),
            working,
        )

    # "y ese mismo número en las demás" / "en las demás"
    if state.active_numbers and re.search(
        r"(en\s+)?(las\s+)?dem[aá]s|todas\s+las\s+(dem[aá]s\s+)?loter|"
        r"ese\s+mismo\s+n[uú]mero|el\s+mismo\s+n[uú]mero",
        low,
    ):
        number = state.active_numbers[0]
        working.scope = "all"
        working.pending_slots = []
        return (
            UnderstandingResult(
                intent="last_occurrence",
                numbers=[number],
                scope="all",
                tool="lottery_compare_last_occurrence_all",
                params={"number": number, "scope": "all"},
                plan=["list_lotteries", "compare_across"],
                confidence=0.88,
                source="follow_up",
            ),
            working,
        )

    # "compáralas" / "comparalas" / "compara las dos" / "compárame eso"
    if re.search(r"comp[aá]ralas|compara(r)?\s+las|comparaci[oó]n|comp[aá]rame\s+(eso|eso)|comp[aá]rame\s+eso", low) and state.active_numbers:
        lots = list(state.active_lotteries)
        if len(lots) >= 2 or state.scope == "all":
            return (
                UnderstandingResult(
                    intent="compare_numbers",
                    lotteries=lots,
                    numbers=list(state.active_numbers),
                    scope="multiple" if lots else "all",
                    tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                    params={
                        "lotteries": lots,
                        "number": state.active_numbers[0],
                        "mode": "number_compare",
                    },
                    plan=["compare_across_lotteries"],
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

    # "y los cinco sorteos siguientes" / "ahora los cinco días siguientes|después"
    if state.date_context and state.active_lotteries and len(state.active_lotteries) == 1 and not state.last_occurrences and re.search(
        r"(sorteos?|d[ií]as?)\s+(siguientes?|despu[eé]s)|siguientes?\s+\d*\s*(sorteos?|d[ií]as?)",
        low,
    ):
        lot = state.active_lotteries[0]
        count = 5
        m = re.search(r"(cinco|5|tres|3|siete|7|diez|10|\d+)\s*(sorteos?|d[ií]as?)?", low)
        word_map = {"cinco": 5, "tres": 3, "siete": 7, "diez": 10}
        if m:
            tok = m.group(1)
            count = word_map.get(tok, int(tok) if tok.isdigit() else 5)
        if re.search(r"d[ií]as?", low) and not re.search(r"sorteos?", low):
            return (
                UnderstandingResult(
                    intent="draw_sequence",
                    lotteries=[lot],
                    query_date=state.date_context,
                    tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                    params={
                        "lottery": lot,
                        "date": state.date_context,
                        "days": count,
                        "include_base_date": False,
                    },
                    confidence=0.9,
                    source="follow_up",
                ),
                working,
            )
        return (
            UnderstandingResult(
                intent="draw_sequence",
                lotteries=[lot],
                query_date=state.date_context,
                tool=LotteryToolName.GET_FOLLOWING_DRAWS.value,
                params={
                    "lottery": lot,
                    "date": state.date_context,
                    "count": count,
                    "include_base_date": False,
                },
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
    lots = list(state.active_lotteries)
    working = state.model_copy(deep=True)
    working.pending_intent = None
    working.pending_slots = []
    working.clarification_question = None

    if intent == "last_occurrence" and number and (lottery or lots or state.scope == "all"):
        if state.scope == "all" or len(lots) > 1:
            return (
                UnderstandingResult(
                    intent="last_occurrence",
                    numbers=[number],
                    lotteries=lots,
                    scope="all" if state.scope == "all" else "multiple",
                    tool="lottery_compare_last_occurrence_all",
                    params={"number": number, "lotteries": lots, "scope": state.scope},
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

    if intent == "numeric_relations" and number and lots:
        pp = dict(state.pending_params or {})
        mode = pp.get("occurrence_mode")
        if mode not in {"last_k", "all"}:
            return (
                UnderstandingResult(
                    intent="numeric_relations",
                    numbers=[str(number)],
                    lotteries=lots,
                    missing_slots=["occurrence_limit"],
                    needs_clarification=True,
                    clarification_question=(
                        f"¿Cuántas últimas ocurrencias del {number} uso? Elige: 5, 10, 20 o todas."
                    ),
                    confidence=0.85,
                    source="follow_up",
                    params={**pp, "observed_number": int(str(number).lstrip("0") or "0")},
                ),
                state.model_copy(
                    update={
                        "pending_intent": "numeric_relations",
                        "pending_slots": ["occurrence_limit"],
                        "pending_params": {
                            **pp,
                            "number": number,
                            "observed_number": int(str(number).lstrip("0") or "0"),
                            "lotteries": lots,
                        },
                    }
                ),
            )
        params = {
            "observed_number": int(str(number).lstrip("0") or "0"),
            "number": str(number),
            "lotteries": lots,
            "occurrence_mode": mode,
        }
        if mode == "last_k":
            params["occurrence_k"] = int(pp.get("occurrence_k") or 0)
        if len(lots) == 1:
            params["lottery"] = lots[0]
        return (
            UnderstandingResult(
                intent="numeric_relations",
                lotteries=lots,
                numbers=[str(number)],
                tool=LotteryToolName.ANALYZE_NUMERIC_RELATIONS.value,
                params=params,
                confidence=0.92,
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
    elif intent.params.get("observed_number") is not None:
        numbers = [str(intent.params["observed_number"])]
    # Also extract from text for clarify paths
    if not numbers:
        n = _extract_number(text)
        if n:
            numbers = [n]
    if not lots:
        lots = _extract_lotteries(text)

    intent_name = "unsupported"
    if intent.kind == "clarify":
        pending = list(intent.params.get("pending_slots") or [])
        # Motor de Relaciones Numéricas — conservar mensaje y slots explícitos
        if (
            "occurrence_limit" in pending
            or intent.params.get("observed_number") is not None
            or re.search(
                r"compa[nñ]eros?|vecinos?|relaciones?\s+num|c[oó]digo\s+madre|"
                r"[uú]ltimas?\s+\d+\s+veces?",
                text,
                re.I,
            )
        ) and (
            pending
            or "relaciones" in (intent.clarify_message or "").lower()
            or "ocurrencias" in (intent.clarify_message or "").lower()
        ):
            return UnderstandingResult(
                intent="numeric_relations",
                lotteries=lots or [str(x) for x in (intent.params.get("lotteries") or [])],
                numbers=numbers,
                missing_slots=pending or ["lottery"],
                needs_clarification=True,
                clarification_question=intent.clarify_message
                or "¿Puedes precisar lotería y cantidad de ocurrencias (5, 10, 20 o todas)?",
                confidence=0.9,
                source="rules",
                params=dict(intent.params or {}),
            )
        # P0: never re-ask lottery+date when memory can drive post-occurrence windows
        if re.search(
            r"(d[ií]as?|sorteos?).{0,16}(siguientes?|despu[eé]s)|(siguientes?|despu[eé]s).{0,16}(d[ií]as?|sorteos?)|"
            r"siete\s+dias|7\s*dias|cinco\s+sorteos",
            text,
            re.I,
        ) and (state.active_lotteries or state.last_occurrences or state.date_context):
            refs = resolve_references(text, state)
            post = _detect_post_occurrence(text, state, refs)
            if post:
                return post[0]
        # Infer intent from text for better clarifications
        if re.search(r"[uú]ltima\s+vez|cu[aá]ndo fue la [uú]ltima", text, re.I):
            intent_name = "last_occurrence"
        elif re.search(r"m[aá]s frecuentes|frecuen", text, re.I):
            intent_name = "frequency"
        elif re.search(r"calientes?", text, re.I):
            intent_name = "hot_numbers"
        missing = []
        msg = (intent.clarify_message or "").lower()
        if "loter" in msg and not (lots or state.active_lotteries):
            missing.append("lottery")
        if "fecha" in msg and not (state.last_occurrences or state.date_context):
            missing.append("date")
        if "n[uú]mero" in msg or "numero" in msg:
            missing.append("number")
        # Fix over-asking: if number already known, drop number from missing
        if numbers and "number" in missing:
            missing = [m for m in missing if m != "number"]
        if state.active_numbers and "number" in missing:
            missing = [m for m in missing if m != "number"]
            if not numbers:
                numbers = list(state.active_numbers)
        # last occurrence never needs date
        if intent_name == "last_occurrence" and "date" in missing:
            missing = [m for m in missing if m != "date"]
        if not missing and intent_name == "last_occurrence" and not lots and not state.active_lotteries:
            missing = ["lottery"]
        if not missing:
            # Clarifier had nothing real to ask — try post-occurrence again
            refs = resolve_references(text, state)
            post = _detect_post_occurrence(text, state, refs)
            if post:
                return post[0]
        q = smart_clarify(
            intent=intent_name,
            number=numbers[0] if numbers else None,
            missing=missing or ["lottery"],
            known_lotteries=lots or list(state.active_lotteries),
        )
        return UnderstandingResult(
            intent=intent_name,
            lotteries=lots or list(state.active_lotteries),
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
        LotteryToolName.CALCULATE_FREQUENCIES.value: "frequency",
        LotteryToolName.GET_HOT_COLD.value: "hot_numbers",
        LotteryToolName.COMPARE_LOTTERIES.value: "compare_lotteries",
        LotteryToolName.COMPARE_NUMBER_PERIODS.value: "compare_number_periods",
        LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value: "compare_numbers",
        LotteryToolName.GET_MISSING_TODAY.value: "missing_results",
        LotteryToolName.GET_SYNC_STATUS.value: "sync_status",
        LotteryToolName.GET_SYNC_WINDOWS.value: "next_sync",
        LotteryToolName.GET_FOLLOWING_DRAWS.value: "draw_sequence",
        LotteryToolName.GET_FOLLOWING_DAYS.value: "draw_sequence",
        LotteryToolName.GET_COVERAGE.value: "data_coverage",
        LotteryToolName.GET_DATA_QUALITY.value: "data_quality",
        LotteryToolName.GET_DATA_COMPLETENESS.value: "data_completeness",
        LotteryToolName.GET_LOTTERY_SUMMARY.value: "lottery_summary",
        LotteryToolName.GET_LATEST_AVAILABLE_DATE.value: "latest_date",
        LotteryToolName.GET_OVERDUE_NUMBERS.value: "overdue_numbers",
        LotteryToolName.EXPLAIN_ANALYSIS_METHOD.value: "explain_metric",
        LotteryToolName.GET_EXPECTED_VS_RECEIVED.value: "expected_vs_received",
        LotteryToolName.GET_YEARLY_COMPARISON.value: "compare_number_periods",
        LotteryToolName.ANALYZE_NUMERIC_RELATIONS.value: "numeric_relations",
    }
    if tool:
        intent_name = mapping.get(tool, "general_domain_question")
    if intent.params.get("focus") == "cold_interval":
        intent_name = "overdue_numbers"
    elif intent.params.get("focus") == "cold_frequency":
        intent_name = "cold_numbers"

    params = dict(intent.params or {})
    if params.get("intent") == "multi_last_occurrence" or (
        isinstance(params.get("multi_queries"), list) and len(params.get("multi_queries") or []) >= 2
    ):
        intent_name = "multi_last_occurrence"
    elif params.get("position") is not None and intent_name == "last_occurrence":
        intent_name = "last_occurrence_by_position"

    return UnderstandingResult(
        intent=intent_name,
        lotteries=lots,
        numbers=numbers,
        query_date=intent.params.get("date"),
        draw_count=intent.params.get("window_draws") or intent.params.get("count"),
        tool=tool,
        params=params,
        confidence=0.8 if tool else 0.4,
        source="rules",
    )
