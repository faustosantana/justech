"""Intent Resolver — natural references and filter inheritance (Fase A.1)."""

from __future__ import annotations

import re
from typing import Any

from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.reference_resolver import resolve_references
from app.services.lottery_intent import _extract_lotteries, _extract_number, _norm


class IntentResolver:
    """Resolve deictic / natural follow-ups without asking for known slots."""

    _YEAR = re.compile(r"\b(20\d{2})\b")
    _THIS_YEAR = re.compile(r"\b(este\s+a[nñ]o|el\s+a[nñ]o\s+actual)\b", re.I)
    _ONLY_FIRST = re.compile(
        r"\b((solo|solamente|únicamente|unicamente)\s+)?(primera\s+posici[oó]n|1ra\s+posici[oó]n|"
        r"posici[oó]n\s*(1|primera)|en\s+primera(\s+posici[oó]n)?)\b",
        re.I,
    )
    _ONLY_SECOND = re.compile(
        r"\b((solo|solamente|ahora)\s+)?(segunda\s+posici[oó]n|2da\s+posici[oó]n|"
        r"posici[oó]n\s*(2|segunda)|en\s+segunda(\s+posici[oó]n)?)\b",
        re.I,
    )
    _ONLY_THIRD = re.compile(
        r"\b((solo|solamente|ahora)\s+)?(tercera\s+posici[oó]n|3ra\s+posici[oó]n|"
        r"posici[oó]n\s*(3|tercera)|en\s+tercera(\s+posici[oó]n)?)\b",
        re.I,
    )
    _LAST_N = re.compile(
        r"\b(y\s+)?(las?\s+)?([uú]ltimas?|anteriores?)\s+"
        r"(\d{1,2}|una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte)"
        r"(\s+(veces|apariciones|sorteos|fechas))?\b|"
        r"\b(dame\s+)?(las?\s+)?(\d{1,2}|tres|cinco|diez)\s+anteriores?\b|"
        r"\b(\d{1,2}|una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+"
        r"([uú]ltimas?|anteriores?)\b",
        re.I,
    )
    _ANY_POS = re.compile(
        r"\b(cualquier\s+posici[oó]n|todas\s+las\s+posiciones|en\s+cu[aá]les\s+posiciones)\b",
        re.I,
    )
    _PAIR_REF = re.compile(
        r"\b(esa\s+pareja|esa\s+combinaci[oó]n|ese\s+par|esos\s+n[uú]meros|"
        r"el\s+mismo\s+par|aquella\s+pareja)\b",
        re.I,
    )
    _ANALYSIS_REF = re.compile(
        r"\b(ese\s+an[aá]lisis|este\s+an[aá]lisis|el\s+an[aá]lisis|"
        r"ese\s+resultado|esa\s+conclusi[oó]n)\b",
        re.I,
    )
    _GROUP_REF = re.compile(
        r"\b(ese\s+grupo|el\s+grupo|esa\s+familia|compa[nñ]eros?\s+de\s+tabla\s*1|"
        r"vecinos?\s+de\s+tabla\s*2)\b",
        re.I,
    )
    _LOTTERY_FILTER = re.compile(
        r"\b(solo|solamente|únicamente|unicamente|ahora\s+solamente|mu[eé]strame\s+solo|"
        r"solamente\s+ah[ií]|solo\s+ah[ií])\s*"
        r"(nacional|loteka|leidsa|real|gana\s*m[aá]s|new\s+york)?\b|"
        r"\b(ahora\s+solamente|solamente|solo)\s+(nacional|loteka|leidsa|real)\b",
        re.I,
    )
    _THERE_ONLY = re.compile(
        r"\b(solamente\s+ah[ií]|solo\s+ah[ií]|ah[ií]\s+mismo|en\s+esa\s+loter[ií]a)\b",
        re.I,
    )
    _WHICH_LOTTERIES = re.compile(
        r"\b(en\s+cu[aá]les\s+loter[ií]as|qu[eé]\s+loter[ií]as|cu[aá]les\s+loter[ií]as)\b",
        re.I,
    )
    _WHICH_POSITIONS = re.compile(
        r"\b(en\s+cu[aá]les\s+posiciones|qu[eé]\s+posiciones|cu[aá]les\s+posiciones)\b",
        re.I,
    )
    _LAST_TIME = re.compile(
        r"\b(la\s+[uú]ltima(\s+vez)?|[uú]ltima\s+(vez|aparici[oó]n)|"
        r"cu[aá]l\s+fue\s+la\s+[uú]ltima|cu[aá]ndo\s+sali[oó](\s+por\s+[uú]ltima\s+vez)?|"
        r"cu[aá]ndo\s+sali[oó])\b",
        re.I,
    )
    _FIRST_TIME = re.compile(
        r"\b(la\s+primera(\s+vez)?|primera\s+(vez|aparici[oó]n)|"
        r"cu[aá]l\s+fue\s+la\s+primera)\b",
        re.I,
    )
    _AFTER = re.compile(
        r"\b("
        r"qu[eé]\s+pas[oó]\s+despu[eé]s|qu[eé]\s+ocurri[oó]\s+(luego|despu[eé]s)|"
        r"despu[eé]s\s+de\s+eso|y\s+despu[eé]s|\bdespu[eé]s\b|"
        r"d[ií]as?\s+siguientes|siguientes\s+a\s+cada|"
        r"(los\s+)?(tres|3|\d{1,2})\s+d[ií]as?\s+siguientes|"
        r"qu[eé]\s+pas[oó]\s+en\s+los\s+.+\s+siguientes"
        r")\b",
        re.I,
    )
    _BEFORE = re.compile(
        r"\b(qu[eé]\s+pas[oó]\s+antes|antes\s+de\s+eso|\bantes\b|"
        r"el\s+anterior)\b",
        re.I,
    )
    _D_WINDOW = re.compile(r"\b[dD]\s*\+\s*(1|3|7)\b|\bhasta\s+[dD]\s*\+\s*(1|3|7)\b")
    _DEICTIC = re.compile(
        r"\b(ese|esa|esos|esas|aquel|aquella|aquellos|aquellas|"
        r"el\s+otro|la\s+otra|los\s+otros|las\s+otras|"
        r"esas\s+veces|aquellos|all[ií])\b",
        re.I,
    )
    _COMPARE_OTHER = re.compile(
        r"\b(comp[aá]ralo\s+con\s+(el\s+)?(otro|anterior)|"
        r"comp[aá]ralo\s+con\s+(el\s+)?(?P<num>\d{1,2})|"
        r"comp[aá]ralo\s+con\s+el\s+(?P<num2>\d{1,2})|"
        r"frente\s+al\s+(?P<num3>\d{1,2}))\b",
        re.I,
    )
    _RETURN_TO = re.compile(
        r"\b(vuelve\s+al?\s+(?P<num>\d{1,2})|regresa\s+al?\s+(?P<num2>\d{1,2})|"
        r"ahora\s+(el\s+)?(?P<num3>\d{1,2})\b(?!\s*(loter|posic)))",
        re.I,
    )
    _FOCUS_PRIMARY = re.compile(
        r"\b(ese\s+candidato|el\s+principal|el\s+fortalecido|"
        r"ese\s+n[uú]mero|el\s+mismo)\b",
        re.I,
    )

    @classmethod
    def resolve(cls, text: str, state: ConversationState) -> dict[str, Any]:
        from app.lottery.ai.turn_policy import (
            canonicalize_position_scope,
            classify_turn_type,
            extract_occurrence_limit,
            extract_subject_numbers,
            strip_quantity_spans,
        )

        base = resolve_references(text, state)
        out: dict[str, Any] = {
            **base,
            "year_filter": None,
            "position_scope": None,
            "lottery_filter": None,
            "follow_up_kind": None,
            "use_active_pair": False,
            "use_last_analysis": False,
            "inherit_active_number": False,
            "compare_with": None,
            "return_to_number": None,
            "deictic": False,
            "resolved_refs": [],
            "limit": None,
            "turn_type": None,
            "lottery_explicit": False,
            "position_explicit": False,
        }

        raw = text or ""
        cleaned_for_numbers = strip_quantity_spans(raw)
        out["raw_message"] = raw
        out["turn_type"] = classify_turn_type(
            raw, has_active_subject=bool(state.active_numbers)
        )

        # Limits: «últimas 3 veces» — before position / number parsing
        from app.lottery.ai.turn_policy import (
            asks_all_lotteries,
            asks_all_positions,
            extract_other_occurrence_limit,
            is_correction_or_meta_request,
            is_most_recent_request,
            is_other_occurrences_request,
            is_previous_occurrences_request,
        )

        lim = extract_occurrence_limit(raw)
        if not lim and is_previous_occurrences_request(raw):
            lim = extract_occurrence_limit(raw) or 2
        if not lim and is_other_occurrences_request(raw):
            lim = extract_other_occurrence_limit(raw)
        if lim:
            out["limit"] = lim
            out["follow_up_kind"] = "last_n_occurrences"
            out["resolved_refs"].append(f"limit:{lim}")
            if state.active_numbers and not extract_subject_numbers(raw):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            if is_previous_occurrences_request(raw) or is_other_occurrences_request(raw):
                prior = int((state.last_analysis or {}).get("limit") or 0)
                out["offset"] = prior
                out["page_offset"] = prior
                out["result_limit"] = lim

        # Year / period filters
        if cls._THIS_YEAR.search(raw):
            from datetime import date as _date

            out["year_filter"] = _date.today().year
            out["resolved_refs"].append("this_year")
        else:
            ym = cls._YEAR.search(raw)
            if ym:
                out["year_filter"] = int(ym.group(1))
                out["resolved_refs"].append(f"year:{ym.group(1)}")

        # Positions — never bare digits (that clashes with «últimas 3»)
        if out.get("follow_up_kind") != "last_n_occurrences":
            if cls._ONLY_SECOND.search(raw):
                out["position_scope"] = canonicalize_position_scope("second_position")
                out["follow_up_kind"] = out.get("follow_up_kind") or "positions"
                out["position_explicit"] = True
                out["resolved_refs"].append("second_position")
            elif cls._ONLY_THIRD.search(raw):
                out["position_scope"] = canonicalize_position_scope("third_position")
                out["follow_up_kind"] = out.get("follow_up_kind") or "positions"
                out["position_explicit"] = True
                out["resolved_refs"].append("third_position")
            elif cls._ONLY_FIRST.search(raw):
                out["position_scope"] = canonicalize_position_scope("first_position")
                out["position_explicit"] = True
                out["resolved_refs"].append("first_position")
            elif cls._ANY_POS.search(raw) or cls._WHICH_POSITIONS.search(raw):
                out["position_scope"] = "all"
                out["position_explicit"] = True
                if cls._WHICH_POSITIONS.search(raw):
                    out["follow_up_kind"] = "positions"
                out["resolved_refs"].append("any_position")

        # Lottery-only filters
        if cls._THERE_ONLY.search(raw) and state.active_lotteries:
            out["lottery_filter"] = state.active_lotteries[0]
            out["lotteries"] = [state.active_lotteries[0]]
            out["resolved_refs"].append("there_only")
        else:
            m = cls._LOTTERY_FILTER.search(raw)
            if m:
                guessed = _extract_lotteries(m.group(0)) or _extract_lotteries(raw)
                if guessed:
                    out["lottery_filter"] = guessed[0]
                    out["lotteries"] = guessed[:1]
                    out["lottery_explicit"] = True
                    out["resolved_refs"].append(f"lottery:{guessed[0]}")

        # Return to a previous number
        ret = cls._RETURN_TO.search(raw)
        if ret:
            n = ret.group("num") or ret.group("num2") or ret.group("num3")
            if n:
                out["return_to_number"] = str(n).zfill(2) if len(n) <= 2 else n
                out["numbers"] = [out["return_to_number"]]
                out["resolved_refs"].append(f"return:{out['return_to_number']}")

        # Compare with other / explicit number
        cmp = cls._COMPARE_OTHER.search(raw)
        if cmp:
            n = cmp.group("num") or cmp.group("num2") or cmp.group("num3")
            if n:
                out["compare_with"] = str(n).zfill(2) if len(n) <= 2 else n
            elif state.current_alternatives:
                out["compare_with"] = str(state.current_alternatives[0]).zfill(2)
            elif len(state.active_numbers or []) >= 2:
                out["compare_with"] = state.active_numbers[1]
            elif getattr(state, "focus_stack", None):
                stack = list(state.focus_stack)
                if len(stack) >= 2:
                    out["compare_with"] = stack[-2]
            out["follow_up_kind"] = "compare"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers[:1])
                out["inherit_active_number"] = True
            out["resolved_refs"].append(f"compare:{out.get('compare_with')}")

        if cls._PAIR_REF.search(raw) and (
            getattr(state, "active_pair", None) or len(state.active_numbers or []) >= 2
        ):
            out["use_active_pair"] = True
            pair = list(getattr(state, "active_pair", None) or state.active_numbers[:2])
            out["numbers"] = [str(x) for x in pair]
            out["resolved_refs"].append("active_pair")

        if cls._ANALYSIS_REF.search(raw) and (state.last_analysis or state.current_primary_candidate):
            out["use_last_analysis"] = True
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            out["resolved_refs"].append("last_analysis")

        if cls._GROUP_REF.search(raw):
            out["follow_up_kind"] = out.get("follow_up_kind") or "group"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            out["resolved_refs"].append("group")

        if cls._WHICH_LOTTERIES.search(raw):
            out["follow_up_kind"] = "lotteries"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            out["resolved_refs"].append("which_lotteries")

        if cls._LAST_TIME.search(raw) and out.get("follow_up_kind") != "last_n_occurrences":
            out["follow_up_kind"] = "last_occurrence"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            out["resolved_refs"].append("last_time")

        if cls._FIRST_TIME.search(raw):
            out["follow_up_kind"] = "first_occurrence"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            out["resolved_refs"].append("first_time")

        if cls._AFTER.search(raw):
            out["follow_up_kind"] = "after"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            # «tres días siguientes» / «3 días siguientes» → window 3
            wm = re.search(
                r"\b(los\s+)?(?P<n>\d{1,2}|tres|dos|uno|una|cinco|siete)\s+d[ií]as?\s+siguientes\b",
                raw,
                re.I,
            )
            if wm:
                word = str(wm.group("n")).lower()
                word_map = {
                    "uno": 1,
                    "una": 1,
                    "dos": 2,
                    "tres": 3,
                    "cinco": 5,
                    "siete": 7,
                }
                out["windows"] = [word_map.get(word, int(word) if word.isdigit() else 3)]
            out["resolved_refs"].append("after")

        if cls._BEFORE.search(raw) and out.get("follow_up_kind") != "after":
            out["follow_up_kind"] = "before"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            out["resolved_refs"].append("before")

        dw = cls._D_WINDOW.search(raw)
        if dw:
            out["follow_up_kind"] = f"d_plus_{(dw.group(1) or dw.group(2))}"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            out["resolved_refs"].append(out["follow_up_kind"])

        if cls._FOCUS_PRIMARY.search(raw) and state.current_primary_candidate is not None:
            out["numbers"] = [str(state.current_primary_candidate).zfill(2)]
            out["resolved_refs"].append("focus_primary")

        # Generic deictics → inherit active context
        if cls._DEICTIC.search(raw):
            out["deictic"] = True
            out["resolved_refs"].append("deictic")
            if not out.get("numbers") and state.active_numbers:
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
            if not out.get("lotteries") and state.active_lotteries and re.search(
                r"\b(esas|aquellas|all[ií])\b", raw, re.I
            ):
                out["lotteries"] = list(state.active_lotteries)

        # Bare follow-ups with no number → inherit ONLY with explicit reference (Fase X)
        from app.lottery.ai.nlp_stability import is_complete_standalone, is_explicit_follow_up

        # Subject numbers from message (never quantity digits)
        msg_nums = extract_subject_numbers(raw)
        if msg_nums:
            out["numbers"] = msg_nums
            out["inherit_active_number"] = False
            out["resolved_refs"].append("message_numbers")

        num = _extract_number(cleaned_for_numbers)
        if is_complete_standalone(raw) and out.get("follow_up_kind") != "last_n_occurrences":
            out["inherit_active_number"] = False
            out["resolved_refs"].append("standalone_no_inherit")
        elif (
            not msg_nums
            and not num
            and not out.get("numbers")
            and state.active_numbers
            and (
                is_explicit_follow_up(raw)
                or out.get("follow_up_kind") == "last_n_occurrences"
            )
        ):
            low = _norm(raw)
            if any(
                k in low
                for k in (
                    "loteria",
                    "posicion",
                    "cuantas",
                    "cuantos",
                    "ultima",
                    "primera",
                    "despues",
                    "antes",
                    "compar",
                    "solamente",
                    "solo ",
                    "este ano",
                    "en 20",
                    "nacional",
                    "loteka",
                    "d+1",
                    "d+3",
                    "d+7",
                    "veces",
                    "apareci",
                    "sali",
                    "ese",
                    "esa",
                    "otro",
                    "anterior",
                    "alli",
                    "grupo",
                    "pareja",
                    "vuelve",
                )
            ) or out.get("follow_up_kind") == "last_n_occurrences":
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True
                out["resolved_refs"].append("inherit_active_explicit")

        # Correction: «me refiero al 97» — new subject, replay last factual intent
        if is_correction_or_meta_request(raw):
            out["turn_type"] = "correction"
            out["replay_last_intent"] = True
            if msg_nums:
                out["numbers"] = msg_nums[:1]
                out["active_pair"] = []
                out["use_active_pair"] = False
                out["follow_up_kind"] = out.get("follow_up_kind") or (
                    "last_occurrence"
                    if (state.last_intent or "").startswith("last")
                    else "last_occurrence"
                )
            elif state.active_numbers:
                out["numbers"] = list(state.active_numbers[:1])
                out["inherit_active_number"] = True
                out["use_last_analysis"] = True
            out["resolved_refs"].append("correction_or_meta")

        if asks_all_lotteries(raw):
            out["lottery_explicit"] = False
            out["clear_lottery"] = True
            out["lotteries"] = []
            out["lottery_filter"] = None
            out["resolved_refs"].append("all_lotteries")
        if asks_all_positions(raw):
            out["position_scope"] = "all"
            out["position_explicit"] = True
            out["resolved_refs"].append("all_positions")
        if is_most_recent_request(raw) and (out.get("numbers") or state.active_numbers):
            out["follow_up_kind"] = "last_occurrence"
            if not out.get("numbers") and state.active_numbers:
                out["numbers"] = list(state.active_numbers[:1])
                out["inherit_active_number"] = True
            out["resolved_refs"].append("most_recent")

        return out
