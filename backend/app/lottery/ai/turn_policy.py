"""Turn / context policy for Lottery IA Analyst (v2.4.3).

Distinguishes new queries vs follow-ups, extracts limits without treating
them as ball numbers, and normalizes positions/lotteries for display.
Does NOT touch motor math or system prompts.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

TurnType = Literal[
    "greeting",
    "acknowledgment",
    "new_query",
    "follow_up",
    "refinement",
    "comparison",
    "return_to_previous",
    "clarification",
    "correction",
    "general_conversation",
]

# Canonical internal position values
POS_ALL = "all"
POS_1 = 1
POS_2 = 2
POS_3 = 3

_WORD_LIMIT = {
    "una": 1,
    "un": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "quince": 15,
    "veinte": 20,
}


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_LAST_N = re.compile(
    r"\b(?P<y>y\s+)?(las?\s+)?([uú]ltimas?|anteriores?|siguientes?)\s+"
    r"(?P<n>\d{1,2}|una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte)"
    r"(\s+(veces|apariciones|sorteos|fechas))?\b",
    re.I,
)
_LAST_N_WORD_FIRST = re.compile(
    r"\b(?P<n>una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte|"
    r"\d{1,2})\s+([uú]ltimas?|anteriores?)\b",
    re.I,
)
_PREVIOUS_N = re.compile(
    r"\b(dame\s+)?(las?\s+)?(?P<n>\d{1,2}|tres|cinco|diez)\s+anteriores?\b|"
    r"\b(las?\s+)?anteriores?\s+(?P<n2>\d{1,2}|tres|cinco|diez)\b",
    re.I,
)
_GREETING = re.compile(r"^\s*(hola|buenos?\s+dias?|buenas?\s+tardes?|buenas?\s+noches?|hey|qu[eé]\s+tal)\b", re.I)
_ACK = re.compile(r"^\s*(gracias|perfecto|excelente|ok|vale|entendido|de\s+acuerdo)\s*[.!]?\s*$", re.I)
_COMPARE = re.compile(r"\b(comp[aá]ra(lo|la|me|r)?|frente\s+a|versus|\bvs\b)\b", re.I)
_RETURN = re.compile(r"\b(vuelve\s+al?|regresa\s+al?|retoma)\b", re.I)
_REFINE_LOT = re.compile(
    r"\b(ahora\s+)?(solo|solamente|unicamente)?\s*(en\s+)?(nacional|loteka|leidsa|real|gana\s*m[aá]s)\b|"
    r"\b(ahora\s+)?(en\s+)?todas\s+las\s+loter",
    re.I,
)
_REFINE_POS = re.compile(
    r"\b(ahora\s+)?(solo\s+)?(en\s+)?(primera|segunda|tercera)\s+posici|"
    r"\b(ahora\s+)?(en\s+)?todas\s+las\s+posiciones\b|"
    r"\b(ahora\s+)?(en\s+)?cualquier\s+posici",
    re.I,
)
_EXPLICIT_NUMBER = re.compile(
    r"\b(?:el|n[uú]mero|numero|del)\s+(\d{1,2})\b",
    re.I,
)
_QUANTITY_CONTEXT = re.compile(
    r"\b(\d{1,2}|una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte)\s+"
    r"(veces|apariciones|sorteos|dias|días|fechas|anteriores|ultimas|últimas)\b|"
    r"\b(ultimas?|últimas?|anteriores?|siguientes?)\s+"
    r"(\d{1,2}|una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte)\b",
    re.I,
)


def parse_limit_token(tok: str) -> int | None:
    t = _norm(tok or "")
    if t.isdigit():
        n = int(t)
        return n if 1 <= n <= 50 else None
    return _WORD_LIMIT.get(t)


def extract_occurrence_limit(text: str) -> int | None:
    """Extract N from «últimas 3 veces», «las cinco anteriores», etc."""
    raw = text or ""
    for rx in (_LAST_N, _LAST_N_WORD_FIRST, _PREVIOUS_N):
        m = rx.search(raw)
        if not m:
            continue
        tok = m.groupdict().get("n") or m.groupdict().get("n2") or ""
        n = parse_limit_token(tok)
        if n:
            return n
    return None


def strip_quantity_spans(text: str) -> str:
    """Remove quantity phrases so «3 veces» is not parsed as ball 03."""
    return _QUANTITY_CONTEXT.sub(" ", text or "")


def extract_subject_numbers(text: str, *, active: list[str] | None = None) -> list[str]:
    """Ball numbers from the message — never quantity N from «últimas N»."""
    cleaned = strip_quantity_spans(text or "")
    found: list[str] = []
    for m in _EXPLICIT_NUMBER.finditer(cleaned):
        n = m.group(1).zfill(2)
        if n not in found and 0 <= int(n) <= 99:
            found.append(n)
    # Bare two-digit balls only (avoid single digit quantity leftovers)
    if not found:
        for m in re.finditer(r"\b(\d{2})\b", cleaned):
            n = m.group(1)
            if n not in found:
                found.append(n)
    return found[:6]


def classify_turn_type(text: str, *, has_active_subject: bool = False) -> TurnType:
    raw = (text or "").strip()
    if not raw:
        return "clarification"
    if _GREETING.search(raw) and len(raw) < 80:
        return "greeting"
    if _ACK.search(raw):
        return "acknowledgment"
    if _RETURN.search(raw):
        return "return_to_previous"
    if _COMPARE.search(raw):
        return "comparison"
    if extract_occurrence_limit(raw) and has_active_subject and not extract_subject_numbers(raw):
        return "follow_up"
    if (_REFINE_LOT.search(raw) or _REFINE_POS.search(raw)) and has_active_subject:
        if extract_subject_numbers(raw):
            return "new_query"
        return "refinement"
    if extract_subject_numbers(raw):
        return "new_query"
    if has_active_subject and re.search(
        r"\b(y\s+en|ahora|solo|solamente|despues|antes|ultima|veces)\b", _norm(raw)
    ):
        return "follow_up"
    return "general_conversation"


def canonicalize_position_scope(value: Any) -> int | str | None:
    """Map internal aliases → 1|2|3|'all'|None."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if value in (1, 2, 3) else None
    s = str(value).strip().lower()
    if s in {"all", "any", "any_position", "todas", "todas las posiciones"}:
        return POS_ALL
    if s in {"1", "first", "first_position", "primera", "primera posicion", "primera posición"}:
        return POS_1
    if s in {"2", "second", "second_position", "segunda", "segunda posicion", "segunda posición"}:
        return POS_2
    if s in {"3", "third", "third_position", "tercera", "tercera posicion", "tercera posición"}:
        return POS_3
    if s.startswith("position_"):
        try:
            return int(s.split("_")[-1])
        except ValueError:
            return None
    return None


def position_label_es(value: Any) -> str:
    c = canonicalize_position_scope(value)
    if c == POS_ALL or c is None:
        return "todas las posiciones"
    if c == 1:
        return "primera posición"
    if c == 2:
        return "segunda posición"
    if c == 3:
        return "tercera posición"
    return "todas las posiciones"


def filters_label_es(
    *,
    lottery_scope: str | list[str] | None,
    position_scope: Any,
    period: str | None = None,
) -> str:
    if isinstance(lottery_scope, list):
        lot = (
            "Todas las loterías"
            if not lottery_scope or len(lottery_scope) >= 5
            else ", ".join(lottery_scope[:4])
        )
    elif lottery_scope in (None, "", "all", "todas"):
        lot = "Todas las loterías"
    else:
        lot = str(lottery_scope)
    pos = position_label_es(position_scope)
    per = period or "Histórico completo"
    return f"{lot} · {pos} · {per}"


def default_lottery_scope() -> list[str]:
    return list(DEFAULT_ALL_HISTORY_LOTTERIES)


def scrub_internal_jargon(text: str) -> str:
    """Remove internal codes from user-facing text."""
    if not text:
        return text
    out = text
    replacements = [
        (r"\bthird_position\b", "tercera posición"),
        (r"\bsecond_position\b", "segunda posición"),
        (r"\bfirst_position\b", "primera posición"),
        (r"\bany_position\b", "todas las posiciones"),
        (r"\blast_occurrence_and_count_across_lotteries\b", "última aparición por lotería"),
        (r"\bcompare_across_lotteries\b", "comparación entre loterías"),
        (r"\bherramientas disponibles\b", "el histórico disponible"),
        (r"\bNo encontré suficiente evidencia con las herramientas disponibles\.", 
         "No pude completar la consulta con los datos disponibles."),
        (r"\bposition_\d+\b", ""),
        (r"\blottery_[a-z0-9_]+\b", ""),
    ]
    for pat, rep in replacements:
        out = re.sub(pat, rep, out, flags=re.I)
    return re.sub(r"\n{3,}", "\n\n", out).strip()
