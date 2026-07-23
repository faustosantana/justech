"""Lottery IA 4.2 — reference / pronoun resolver over ConversationState."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from app.lottery.ai.conversation_state import ConversationState
from app.services.lottery_intent import _extract_lotteries, _extract_number


_PRONOUN_LOTTERIES = re.compile(
    r"\b("
    r"esas?\s+loter[ií]as?|dichas?\s+loter[ií]as?|las\s+mismas(\s+loter[ií]as?)?|"
    r"ambas(\s+loter[ií]as?)?|las\s+dos|en\s+esas|las\s+anteriores|"
    r"mis\s+loter[ií]as?|las\s+principales|las\s+predeterminadas"
    r")\b",
    re.I,
)
_PRONOUN_NUMBER = re.compile(
    r"\b(ese\s+(mismo\s+)?n[uú]mero|el\s+mismo\s+n[uú]mero|ese\s+\d{1,2}|aquel\s+n[uú]mero)\b",
    re.I,
)
_AFTER_DAYS = re.compile(
    r"(?P<n>\d+|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
    r"siete|cinco|tres)?\s*"
    r"(?P<unit>d[ií]as?|sorteos?)\s+"
    r"(?P<dir>despu[eé]s|siguientes?|posteriores?)"
    r"|"
    r"(?P<dir2>despu[eé]s|siguientes?|posteriores?)\s+(de\s+)?"
    r"(?P<n2>\d+|siete|cinco|tres|diez)?\s*"
    r"(?P<unit2>d[ií]as?|sorteos?)",
    re.I,
)
_BEFORE_DAYS = re.compile(
    r"(?P<n>\d+|siete|cinco|tres|diez)?\s*"
    r"(?P<unit>d[ií]as?|sorteos?)\s+"
    r"(?P<dir>antes|anteriores?|previos?)",
    re.I,
)
_SWAP_NUMBER = re.compile(
    r"^(ahora\s+)?(hazlo|hazlo\s+ahora|rep[ií]telo|igual)\s+(con|para)\s+(el\s+)?(?P<num>\d{1,2})\b|"
    r"^con\s+el\s+(?P<num2>\d{1,2})\b|"
    r"^ahora\s+(el\s+)?(?P<num3>\d{1,2})\b",
    re.I,
)

_WORD_NUM = {
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
}


def _parse_count(tok: str | None, default: int = 7) -> int:
    if not tok:
        return default
    t = tok.lower().strip()
    if t.isdigit():
        return max(1, min(int(t), 90))
    return _WORD_NUM.get(t, default)


def resolve_references(text: str, state: ConversationState) -> dict[str, Any]:
    """
    Resolve pronouns / deictic references before intent classification.

    Returns a dict of resolved entities (does not mutate state unless caller applies it).
    """
    low = (text or "").lower().strip()
    out: dict[str, Any] = {
        "lotteries": [],
        "numbers": [],
        "used_pronoun_lotteries": False,
        "used_pronoun_number": False,
        "post_window": None,  # {"unit": "days"|"draws", "count": int, "direction": "after"|"before"}
        "swap_number": None,
        "last_user_reference": None,
    }

    # Explicit lotteries always win
    explicit = _extract_lotteries(text)
    if explicit:
        out["lotteries"] = explicit
    elif _PRONOUN_LOTTERIES.search(low) and state.active_lotteries:
        out["lotteries"] = list(state.active_lotteries)
        out["used_pronoun_lotteries"] = True
        out["last_user_reference"] = "esas loterías"
    elif state.active_lotteries and re.search(
        r"\b(despu[eé]s|antes|siguientes|anteriores|comp[aá]ral|hazlo)\b", low
    ):
        # Soft inherit lotteries when follow-up verbs omit them
        out["lotteries"] = list(state.active_lotteries)

    # Numbers
    num = _extract_number(text)
    swap = _SWAP_NUMBER.search(low)
    if swap:
        out["swap_number"] = (
            swap.group("num") or swap.group("num2") or swap.group("num3")
        )
        out["numbers"] = [out["swap_number"]]
    elif num:
        out["numbers"] = [num]
    elif _PRONOUN_NUMBER.search(low) and state.active_numbers:
        out["numbers"] = list(state.active_numbers)
        out["used_pronoun_number"] = True
        out["last_user_reference"] = "ese número"
    elif state.active_numbers and (
        out["used_pronoun_lotteries"]
        or re.search(r"\b(despu[eé]s|antes|siguientes|anteriores|comp[aá]ral)\b", low)
    ):
        out["numbers"] = list(state.active_numbers)

    # After / before windows
    m = _AFTER_DAYS.search(low)
    if m:
        n = m.groupdict().get("n") or m.groupdict().get("n2")
        unit = (m.groupdict().get("unit") or m.groupdict().get("unit2") or "dias").lower()
        count = _parse_count(n, default=7)
        out["post_window"] = {
            "unit": "draws" if "sorteo" in unit else "days",
            "count": count,
            "direction": "after",
        }
        out["last_user_reference"] = f"{count} {'sorteos' if 'sorteo' in unit else 'días'} después"
    else:
        m2 = _BEFORE_DAYS.search(low)
        if m2:
            n = m2.group("n")
            unit = (m2.group("unit") or "dias").lower()
            count = _parse_count(n, default=7)
            out["post_window"] = {
                "unit": "draws" if "sorteo" in unit else "days",
                "count": count,
                "direction": "before",
            }

    return out


def derive_per_lottery_base_dates(
    state: ConversationState,
    lotteries: list[str],
    number: str | None = None,
) -> dict[str, date]:
    """Map lottery → occurrence base date from memory (or single date_context)."""
    out: dict[str, date] = {}
    for lot in lotteries:
        mem = state.last_occurrences.get(lot)
        if mem and mem.date and (not number or str(mem.number) == str(number)):
            try:
                out[lot] = date.fromisoformat(str(mem.date)[:10])
                continue
            except ValueError:
                pass
        # Fallback: any occurrence for that lottery regardless of number mismatch
        if mem and mem.date:
            try:
                out[lot] = date.fromisoformat(str(mem.date)[:10])
            except ValueError:
                pass
    if not out and state.date_context and lotteries:
        for lot in lotteries:
            out[lot] = state.date_context
    return out


def window_bounds(base: date, *, days: int, direction: str = "after") -> tuple[date, date]:
    """Calendar window exclusive of base date."""
    if direction == "before":
        end = base - timedelta(days=1)
        start = base - timedelta(days=days)
        return start, end
    start = base + timedelta(days=1)
    end = base + timedelta(days=days)
    return start, end
