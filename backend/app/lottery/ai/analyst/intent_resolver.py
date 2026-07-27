"""Intent Resolver — natural references and filter inheritance (Fase A)."""

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
    _ONLY_POS = re.compile(
        r"\b(solo|solamente|únicamente|unicamente)\s+(primera|1(ra)?|primera\s+posici[oó]n)\b|"
        r"\b(solo|solamente)\s+primera\b|"
        r"\bprimera\s+posici[oó]n\b",
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
        r"\b(solo|solamente|únicamente|unicamente|mu[eé]strame\s+solo)\s+"
        r"(nacional|loteka|leidsa|real|gana\s*m[aá]s|new\s+york)\b",
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
        r"\b(la\s+[uú]ltima\s+vez|[uú]ltima\s+aparici[oó]n|cu[aá]ndo\s+sali[oó]\s+[uú]ltima)\b",
        re.I,
    )
    _AFTER = re.compile(
        r"\b(qu[eé]\s+pas[oó]\s+despu[eé]s|qu[eé]\s+ocurri[oó]\s+luego|"
        r"despu[eé]s\s+de\s+eso|y\s+despu[eé]s)\b",
        re.I,
    )
    _D_WINDOW = re.compile(r"\b[dD]\s*\+\s*(1|3|7)\b|\bhasta\s+[dD]\s*\+\s*(1|3|7)\b")

    @classmethod
    def resolve(cls, text: str, state: ConversationState) -> dict[str, Any]:
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
        }

        # Year / period filters
        if cls._THIS_YEAR.search(text or ""):
            from datetime import date as _date

            out["year_filter"] = _date.today().year
        else:
            ym = cls._YEAR.search(text or "")
            if ym:
                out["year_filter"] = int(ym.group(1))

        if cls._ONLY_POS.search(text or ""):
            out["position_scope"] = "first_position"
        elif cls._ANY_POS.search(text or "") or cls._WHICH_POSITIONS.search(text or ""):
            out["position_scope"] = "any_position"
            if cls._WHICH_POSITIONS.search(text or ""):
                out["follow_up_kind"] = "positions"

        # Lottery-only filters
        m = cls._LOTTERY_FILTER.search(text or "")
        if m:
            guessed = _extract_lotteries(m.group(0)) or _extract_lotteries(text or "")
            if guessed:
                out["lottery_filter"] = guessed[0]
                out["lotteries"] = guessed[:1]

        if cls._PAIR_REF.search(text or "") and (
            getattr(state, "active_pair", None) or len(state.active_numbers or []) >= 2
        ):
            out["use_active_pair"] = True
            pair = list(getattr(state, "active_pair", None) or state.active_numbers[:2])
            out["numbers"] = [str(x) for x in pair]

        if cls._ANALYSIS_REF.search(text or "") and (state.last_analysis or state.current_primary_candidate):
            out["use_last_analysis"] = True
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True

        if cls._GROUP_REF.search(text or ""):
            out["follow_up_kind"] = out.get("follow_up_kind") or "group"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True

        if cls._WHICH_LOTTERIES.search(text or ""):
            out["follow_up_kind"] = "lotteries"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True

        if cls._LAST_TIME.search(text or ""):
            out["follow_up_kind"] = "last_occurrence"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True

        if cls._AFTER.search(text or ""):
            out["follow_up_kind"] = "after"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True

        dw = cls._D_WINDOW.search(text or "")
        if dw:
            out["follow_up_kind"] = f"d_plus_{(dw.group(1) or dw.group(2))}"
            if state.active_numbers and not out.get("numbers"):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True

        # Bare follow-ups with no number → inherit active number
        num = _extract_number(text or "")
        if not num and not out.get("numbers") and state.active_numbers:
            low = _norm(text or "")
            if any(
                k in low
                for k in (
                    "loteria",
                    "posicion",
                    "cuantas",
                    "cuantos",
                    "ultima",
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
                )
            ):
                out["numbers"] = list(state.active_numbers)
                out["inherit_active_number"] = True

        return out
