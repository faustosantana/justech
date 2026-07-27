"""Compound last-occurrence parsing + default position scope for Lottery IA."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal


PositionScope = Literal["first_position", "any_position", "specific_position", "ask_each_time"]

# Fase X.2 — if user does not limit position, search ALL positions.
# preferred_position (1) is highlight-only, never an exclusive filter.
DEFAULT_POSITION_SCOPE: PositionScope = "any_position"
DEFAULT_PRIMARY_POSITION = 1
PREFERRED_POSITION = 1

POSITION_LABELS = {
    1: "Primera posición",
    2: "Segunda posición",
    3: "Tercera posición",
}


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def position_label(pos: int | None) -> str:
    if pos is None:
        return "Cualquier posición"
    return POSITION_LABELS.get(int(pos), f"Posición {pos}")


def extract_position_scope(text: str) -> tuple[PositionScope, int | None]:
    """Return (scope, specific_position). specific_position only when explicit 1/2/3."""
    t = _norm(text)
    if re.search(
        r"cualquier\s+posicion|sin\s+importar\s+la\s+posicion|todas\s+las\s+posiciones|"
        r"en\s+primero,?\s*segundo\s*(o|y)\s*tercero|dondequiera|en\s+cualquier\s+lugar",
        t,
    ):
        return "any_position", None
    m = re.search(
        r"\b(en\s+)?(primer[oa]|1r[oa]|1\s*era?|posicion\s*1|primero)\b",
        t,
    )
    if m:
        return "specific_position", 1
    m = re.search(r"\b(en\s+)?(segund[oa]|2d[oa]|2\s*da|posicion\s*2)\b", t)
    if m:
        return "specific_position", 2
    m = re.search(r"\b(en\s+)?(tercer[oa]|3r[oa]|3\s*ra|posicion\s*3)\b", t)
    if m:
        return "specific_position", 3
    # Fase X.2 — silent default is all positions (not first-only)
    return "any_position", None


def resolve_effective_position(
    text: str,
    *,
    pref_scope: PositionScope | None = None,
    pref_primary: int = DEFAULT_PRIMARY_POSITION,
) -> tuple[int | None, PositionScope, bool]:
    """
    Returns (position_filter, scope_used, needs_ask).
    position_filter None => any position.
    Preferred first position is never applied as an exclusive filter unless
    the user (or explicit pref_scope=first_position) asks for it.
    """
    explicit_scope, explicit_pos = extract_position_scope(text)
    if explicit_scope == "any_position":
        return None, "any_position", False
    if explicit_scope == "specific_position" and explicit_pos is not None:
        return int(explicit_pos), "specific_position", False

    scope = pref_scope or DEFAULT_POSITION_SCOPE
    if scope == "ask_each_time":
        return None, "ask_each_time", True
    if scope == "any_position":
        return None, "any_position", False
    if scope == "specific_position":
        return int(pref_primary or DEFAULT_PRIMARY_POSITION), "specific_position", False
    if scope == "first_position":
        return int(pref_primary or DEFAULT_PRIMARY_POSITION), "first_position", False
    return None, "any_position", False


_LOTTERY_HINTS = [
    (r"quiniela\s+real|\breal\b", "Real"),
    (r"quiniela\s+loteka|loteka", "Loteka"),
    (r"quiniela\s+leidsa|leidsa", "Leidsa"),
    (r"loter[ií]a\s+nacional|nacional\s+noche|\bnacional\b", "Nacional Noche"),
    (r"gana\s+m[aá]s|ganamas", "Gana Más"),
    (r"lotedom|lote\s*dom", "LoteDom"),
    (r"new\s+york\s+noche|\bny\s+noche\b", "New York Noche"),
    (r"new\s+york\s+d[ií]a|\bny\s+d[ií]a\b|new\s+york\s*2:?30", "New York Día"),
]


def _extract_lottery_from_chunk(chunk: str) -> str | None:
    t = _norm(chunk)
    for pattern, name in _LOTTERY_HINTS:
        if re.search(pattern, t):
            return name
    return None


def _extract_number_token(chunk: str) -> str | None:
    m = re.search(r"\b(?:el|n[uú]mero)?\s*(\d{1,2})\b", chunk, re.I)
    if not m:
        return None
    return m.group(1).zfill(2)


OTHER_LOTTERY_RE = re.compile(
    r"cualquier\s+otra(\s+loter[ií]a)?|otra\s+loter[ií]a|las\s+dem[aá]s|"
    r"todas\s+excepto|resto\s+de\s+loter|en\s+otra",
    re.I,
)

LAST_OCC_TRIGGER_RE = re.compile(
    r"(cu[aá]ndo\s+(sali[oó]|apareci)|cuando\s+sali|"
    r"[uú]ltima\s+vez|hace\s+cu[aá]nto.*(sali|apareci)|"
    r"d[oó]nde\s+sali[oó]|ha\s+salido|sali[oó]\s+el\s+\d)",
    re.I,
)


def is_last_occurrence_question(text: str) -> bool:
    t = _norm(text)
    # Fase X: count questions are not last-occurrence
    if re.search(r"cuantas?\s+veces|cuantas?\s+apariciones", t):
        return False
    # Fase X.2 — same-day coincidence is not last-occurrence-per-number
    if re.search(
        r"mismo\s+dia|misma\s+fecha|coincid|juntos|alguna\s+vez.*(y\s+el|ambos)",
        t,
    ):
        return False
    if re.search(r"frecuencia|mas frecuentes|analiza(r)?\s+los\s+ultimos", t):
        # Explicit frequency wins only if no clear "cuándo salió"
        if not re.search(r"cuando\s+sali|ultima\s+vez|donde\s+sali", t):
            return False
    return bool(LAST_OCC_TRIGGER_RE.search(text))


def parse_compound_last_occurrence(
    text: str,
    *,
    pref_scope: PositionScope | None = None,
    pref_primary: int = DEFAULT_PRIMARY_POSITION,
) -> dict[str, Any] | None:
    """
    Parse multi-subject last-occurrence questions into independent subqueries.

    Example:
      ¿Cuándo salió el 35 en Leidsa y el 44 en cualquier otra lotería?
    """
    # Same-day co-occurrence belongs to same_day_coincidence policy (X.2)
    if re.search(
        r"mismo\s+d[ií]a|misma\s+fecha|coincid|juntos|"
        r"han\s+salido\s+alguna\s+vez|alguna\s+vez\s+el\s+\d",
        text or "",
        re.I,
    ) and not re.search(r"\ben\s+\w+.+\by\s+el\s+\d.+\ben\s+\w+", text or "", re.I):
        return None

    if not is_last_occurrence_question(text) and not re.search(
        r"\bel\s+\d{1,2}\b.+\by\s+el\s+\d{1,2}\b", text, re.I
    ):
        # Allow "Busca el 10 en Real y el 20 en Nacional"
        if not re.search(r"busca(r)?\s+el\s+\d|ambos\s+en\s+primera", text, re.I):
            return None

    pos_filter, scope_used, needs_ask = resolve_effective_position(
        text, pref_scope=pref_scope, pref_primary=pref_primary
    )
    if needs_ask:
        return {
            "intent": "multi_last_occurrence",
            "needs_clarification": True,
            "clarification_question": (
                "¿Busco estos números en primera posición o en cualquier posición?"
            ),
            "queries": [],
            "position_scope": scope_used,
        }

    # Split clauses on " y el N" / " y la N" while keeping the connector number with right clause
    parts: list[str] = []
    cursor = 0
    for m in re.finditer(r"\s+y\s+(?=el\s+\d{1,2}\b)", text, re.I):
        parts.append(text[cursor : m.start()])
        cursor = m.end()
    parts.append(text[cursor:])
    parts = [p.strip(" ¿?.,;") for p in parts if p.strip()]

    if len(parts) < 2:
        # Single-clause last occurrence → still return structured one-query form when trigger matches
        if not is_last_occurrence_question(text):
            return None
        number = _extract_number_token(text)
        lottery = _extract_lottery_from_chunk(text)
        if not number:
            return None
        q: dict[str, Any] = {
            "number": number,
            "position": pos_filter,
            "position_scope": scope_used,
        }
        if lottery:
            q["lotteries"] = [lottery]
            q["lotteries_scope"] = "named"
        else:
            q["lotteries_scope"] = "all"
        return {
            "intent": "last_occurrence",
            "queries": [q],
            "position_scope": scope_used,
            "needs_clarification": False,
        }

    queries: list[dict[str, Any]] = []
    mentioned: list[str] = []
    for part in parts:
        number = _extract_number_token(part)
        if not number:
            continue
        other = bool(OTHER_LOTTERY_RE.search(part))
        lottery = _extract_lottery_from_chunk(part)
        q = {
            "number": number,
            "position": pos_filter,
            "position_scope": scope_used,
        }
        if other:
            q["lotteries_scope"] = "all_except_previous"
            q["excluded_lotteries"] = list(dict.fromkeys(mentioned))
            q["lotteries"] = []
        elif lottery:
            q["lotteries_scope"] = "named"
            q["lotteries"] = [lottery]
            mentioned.append(lottery)
        else:
            q["lotteries_scope"] = "all"
            q["lotteries"] = []
        queries.append(q)

    if len(queries) < 2:
        return None

    return {
        "intent": "multi_last_occurrence",
        "queries": queries,
        "position_scope": scope_used,
        "needs_clarification": False,
        "raw": text,
    }


def follow_up_any_position(text: str) -> bool:
    t = _norm(text).strip(" ¿?¡!.")
    return bool(
        re.search(
            r"^(y\s+)?en\s+cualquier\s+posicion|"
            r"^(y\s+)?ahora\s+en\s+cualquier(\s+posicion)?|"
            r"sin\s+importar\s+(la\s+)?posicion|"
            r"cualquier\s+posicion\??$",
            t,
        )
    )


def follow_up_first_position(text: str) -> bool:
    t = _norm(text).strip(" ¿?¡!.")
    return bool(
        re.search(
            r"^(y\s+)?(en\s+)?primera(\s+posicion)?|"
            r"^(y\s+)?solo\s+en\s+primera|"
            r"^(y\s+)?ahora\s+en\s+primera|"
            r"^(y\s+)?en\s+primera\s+posicion\??$",
            t,
        )
    )


def follow_up_replace_numbers(text: str) -> list[str] | None:
    """Parse 'Ahora hazlo con el 57 y el 62' → ['57','62']."""
    t = _norm(text)
    if not re.search(r"hazlo\s+con|ahora\s+con|cambia(r)?\s+(a|por)|usa(ndo)?\s+el", t):
        if not re.search(r"ahora\s+hazlo", t):
            return None
    nums = re.findall(r"\bel\s+(\d{1,2})\b", text, re.I)
    if len(nums) >= 2:
        return [n.zfill(2) for n in nums[:5]]
    if len(nums) == 1:
        return [nums[0].zfill(2)]
    return None
