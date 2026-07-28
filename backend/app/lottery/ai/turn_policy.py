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
# Word quantities may use singular/plural («tres últimas» / «una anterior»).
# Digit quantities MUST be plural («3 últimas», «7 anteriores») so that
# «el 07 última vez» is last_occurrence of 07 — never limit=7.
_LAST_N_WORD_FIRST = re.compile(
    r"\b(?P<n>una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte)"
    r"\s+([uú]ltimas?|anteriores?)\b|"
    r"\b(?P<n2>\d{1,2})\s+([uú]ltimas|anteriores)\b",
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
    r"(veces|apariciones|sorteos|dias|días|fechas|anteriores|ultimas|últimas|siguientes)\b|"
    r"\b(ultimas?|últimas?|anteriores?|siguientes?|otras?)\s+"
    r"(\d{1,2}|una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte)"
    r"(\s+(veces|apariciones|sorteos|fechas))?\b|"
    r"\b(dame\s+)?(las?\s+)?(\d{1,2}|dos|tres|cuatro|cinco|diez)\s+anteriores?\b",
    re.I,
)
_PREVIOUS_TO_THOSE = re.compile(
    r"\b(anteriores?\s+a\s+(esas|estos|ellas|ellos)|"
    r"dos\s+anteriores|las?\s+anteriores\s+a\s+esas|"
    r"dame\s+las?\s+(\d{1,2}|dos|tres)\s+anteriores)\b",
    re.I,
)
_OTHER_N = re.compile(
    r"\b(las?\s+)?otras?\s+(?P<n>\d{1,2}|tres|cuatro|cinco|diez)\b|"
    r"\b(?P<n2>\d{1,2}|tres|cuatro|cinco)\s+m[aá]s\b",
    re.I,
)
_CORRECTION = re.compile(
    r"\b(me\s+refiero\s+al?|no,?\s+me\s+refiero|no\s+fue\s+lo\s+que|"
    r"eso\s+no\s+fue|revisalo|rev[ií]salo|est[aá]s?\s+seguro|"
    r"expl[ií]camelo\s+m[aá]s\s+simple|dame\s+solo\s+la\s+respuesta|"
    r"an[aá]lisis\s+m[aá]s\s+profundo|qu[eé]\s+te\s+llama\s+la\s+atenci[oó]n)\b",
    re.I,
)
_MOST_RECENT = re.compile(
    r"\b(la\s+m[aá]s\s+reciente|cu[aá]l\s+fue\s+la\s+m[aá]s\s+reciente|"
    r"la\s+[uú]ltima\s+(de\s+esas|aparici[oó]n)?)\b",
    re.I,
)
_ALL_LOTTERIES = re.compile(r"\b(todas\s+las\s+loter[ií]as|cualquier\s+loter[ií]a)\b", re.I)
_ALL_POSITIONS = re.compile(
    r"\b(todas\s+las\s+posiciones|cualquier\s+posici[oó]n|vuelve\s+a\s+todas\s+las\s+posiciones)\b",
    re.I,
)


def purpose_label_es(purpose: str | None) -> str:
    """User-facing label for an internal research purpose — never snake_case."""
    if not purpose:
        return "consulta histórica"
    p = str(purpose).strip()
    mapping = {
        "last_n_occurrences": "últimas apariciones",
        "last_occurrence": "última aparición",
        "last_occurrence_all_lotteries": "última aparición por lotería",
        "compare_across_lotteries": "comparación entre loterías",
        "same_day_coincidence": "coincidencia el mismo día",
        "frequency": "frecuencia",
        "frequency_across_lotteries": "frecuencia por lotería",
        "recent_occurrences": "apariciones recientes",
        "complete_analysis_t1_t2": "análisis completo",
        "what_happened_after": "días siguientes",
        "compare_a_occurrences": "apariciones del primer número",
        "compare_b_occurrences": "apariciones del segundo número",
        "compare_a_lotteries": "primer número por lotería",
        "compare_b_lotteries": "segundo número por lotería",
        "compare_a_frequency": "frecuencia del primer número",
        "compare_b_frequency": "frecuencia del segundo número",
        "compare_historical_patterns": "patrones históricos",
    }
    if p in mapping:
        return mapping[p]
    if p.startswith("compare_"):
        return "comparación histórica"
    return re.sub(r"_+", " ", p).strip() or "consulta histórica"


def is_previous_occurrences_request(text: str) -> bool:
    return bool(_PREVIOUS_TO_THOSE.search(text or ""))


def is_other_occurrences_request(text: str) -> bool:
    return bool(_OTHER_N.search(text or ""))


def extract_other_occurrence_limit(text: str) -> int | None:
    m = _OTHER_N.search(text or "")
    if not m:
        return None
    tok = m.groupdict().get("n") or m.groupdict().get("n2") or ""
    return parse_limit_token(tok)


def is_correction_or_meta_request(text: str) -> bool:
    return bool(_CORRECTION.search(text or ""))


class ConversationPolicy:
    """Continuity rules for meta / correction turns (H.5–H.9).

    Does not touch the LLM. Pins the active subject and prefers factual
    local templates so synthesis cannot reopen prior subjects (22 vs 97).
    """

    @staticmethod
    def is_meta_continuity(text: str) -> bool:
        """Meta follow-up without naming a new ball number."""
        raw = text or ""
        if not is_correction_or_meta_request(raw):
            return False
        return not bool(extract_subject_numbers(raw))

    @staticmethod
    def is_subject_correction(text: str) -> bool:
        raw = text or ""
        return bool(is_correction_or_meta_request(raw) and extract_subject_numbers(raw))

    @staticmethod
    def active_subject(state: Any) -> str | None:
        nums = list(getattr(state, "active_numbers", None) or [])
        if nums:
            return str(nums[0])
        stack = list(getattr(state, "focus_stack", None) or [])
        return str(stack[-1]) if stack else None

    @classmethod
    def pin_active_subject(cls, state: Any) -> Any:
        """Keep only the current subject in focus — drop prior balls from stack."""
        subj = cls.active_subject(state)
        if not subj:
            return state
        state.active_numbers = [subj]
        state.focus_stack = [subj]
        state.active_pair = []
        state.force_local_template = True
        state.conversation_summary = f"Sujeto activo: {subj}."
        filters = dict(getattr(state, "active_filters", None) or {})
        filters["meta_continuity"] = True
        state.active_filters = filters
        return state

    @classmethod
    def apply_correction_subject(cls, state: Any, number: str) -> Any:
        n = str(number).zfill(2) if str(number).isdigit() else str(number)
        state.active_numbers = [n]
        state.focus_stack = [n]
        state.active_pair = []
        state.force_local_template = False
        state.conversation_summary = f"Sujeto activo: {n}."
        filters = dict(getattr(state, "active_filters", None) or {})
        filters.pop("meta_continuity", None)
        state.active_filters = filters
        return state

    @staticmethod
    def should_force_local_template(state: Any, text: str | None = None) -> bool:
        if bool(getattr(state, "force_local_template", False)):
            return True
        if (getattr(state, "active_filters", None) or {}).get("meta_continuity"):
            return True
        if text and ConversationPolicy.is_meta_continuity(text):
            return True
        # D: filter-only refinements must stay on the factual template — LLM
        # otherwise reopens prior same_day subjects from dialogue history.
        if text and (asks_all_positions(text) or asks_all_lotteries(text)):
            return True
        return False


def is_most_recent_request(text: str) -> bool:
    return bool(_MOST_RECENT.search(text or ""))


def asks_all_lotteries(text: str) -> bool:
    return bool(_ALL_LOTTERIES.search(text or ""))


def asks_all_positions(text: str) -> bool:
    return bool(_ALL_POSITIONS.search(text or ""))


def exclude_limit_from_subjects(subjects: list[str], limit: int | None) -> list[str]:
    """Drop quantity digits that were mistaken for ball numbers.

    If the only extracted digit was the limit itself (e.g. «últimas 3» → 03),
    return [] — never restore the limit as a subject.
    """
    if not subjects or limit is None:
        return list(subjects)
    lim = str(int(limit))
    lim_z = lim.zfill(2)
    return [
        s
        for s in subjects
        if not (
            str(s).isdigit()
            and (str(int(s)) == lim or str(s).zfill(2) == lim_z)
        )
    ]


_SPANISH_BALL_WORDS: dict[str, str] = {
    "cero": "00",
    "uno": "01",
    "una": "01",
    "dos": "02",
    "tres": "03",
    "cuatro": "04",
    "cinco": "05",
    "seis": "06",
    "siete": "07",
    "ocho": "08",
    "nueve": "09",
    "diez": "10",
    "once": "11",
    "doce": "12",
    "trece": "13",
    "catorce": "14",
    "quince": "15",
    "dieciseis": "16",
    "dieciséis": "16",
    "diecisiete": "17",
    "dieciocho": "18",
    "diecinueve": "19",
    "veinte": "20",
    "veintiuno": "21",
    "veintiún": "21",
    "veintiun": "21",
    "veintidos": "22",
    "veintidós": "22",
    "veintitres": "23",
    "veintitrés": "23",
    "veinticuatro": "24",
    "veinticinco": "25",
    "veintiseis": "26",
    "veintiséis": "26",
    "veintisiete": "27",
    "veintiocho": "28",
    "veintinueve": "29",
    "treinta": "30",
}


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
    # Spanish number words as ball subjects («veintidós», «catorce»)
    if not found:
        low = (cleaned or "").lower()
        # Prefer longer tokens first (veintidós before dos)
        for word, ball in sorted(_SPANISH_BALL_WORDS.items(), key=lambda kv: -len(kv[0])):
            if re.search(rf"\b{re.escape(word)}\b", low):
                if ball not in found:
                    found.append(ball)
                break
    # Single digit only with explicit el/número cue already handled; avoid bare 1–9
    lim = extract_occurrence_limit(text or "")
    found = exclude_limit_from_subjects(found, lim)
    if not found and active:
        return list(active)[:6]
    return found[:6]


def scrub_internal_jargon(text: str) -> str:
    """Remove internal codes from user-facing text."""
    if not text:
        return text
    out = text
    replacements = [
        (r"\blast_n_occurrences\b", "últimas apariciones"),
        (r"\blast_occurrence_and_count_across_lotteries\b", "última aparición por lotería"),
        (r"\bcompare_across_lotteries\b", "comparación entre loterías"),
        (r"\bcompare_a_lotteries\b", "comparación por lotería"),
        (r"\bcompare_b_lotteries\b", "comparación por lotería"),
        (r"\bcompare_a_occurrences\b", "apariciones"),
        (r"\bcompare_b_occurrences\b", "apariciones"),
        (r"\bcompare_[a-z0-9_]+\b", "comparación histórica"),
        (r"\bthird_position\b", "tercera posición"),
        (r"\bsecond_position\b", "segunda posición"),
        (r"\bfirst_position\b", "primera posición"),
        (r"\bany_position\b", "todas las posiciones"),
        (r"\bherramientas disponibles\b", "el histórico disponible"),
        (r"\bNo encontré suficiente evidencia con las herramientas disponibles\.",
         "No pude completar la consulta con los datos disponibles."),
        (r"\bposition_\d+\b", ""),
        (r"\blottery_[a-z0-9_]+\b", ""),
        (r"\bquestion_kind\b", ""),
        (r"\bevidence_package\b", ""),
        (r"\bsame_day_coincidence\b", "coincidencia el mismo día"),
        (r"(?m)^\s*-\s*[a-z]+_[a-z0-9_]+:\s*", "- "),
    ]
    for pat, rep in replacements:
        out = re.sub(pat, rep, out, flags=re.I)
    # Drop leftover snake_case tokens that look like internal ids
    out = re.sub(r"\b[a-z]+(?:_[a-z0-9]+)+\b", "", out)
    return re.sub(r"[ \t]{2,}", " ", re.sub(r"\n{3,}", "\n\n", out)).strip()


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
        gd = m.groupdict()
        tok = gd.get("n") or gd.get("n2") or ""
        n = parse_limit_token(tok)
        if n:
            return n
    if is_previous_occurrences_request(raw):
        m = re.search(r"\b(\d{1,2}|dos|tres|cuatro|cinco)\s+anteriores", raw, re.I)
        if m:
            return parse_limit_token(m.group(1))
        return 2
    other = extract_other_occurrence_limit(raw)
    if other:
        return other
    return None


def strip_quantity_spans(text: str) -> str:
    """Remove quantity phrases so «3 veces» is not parsed as ball 03."""
    return _QUANTITY_CONTEXT.sub(" ", text or "")


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
    if is_correction_or_meta_request(raw) and extract_subject_numbers(raw):
        return "correction"
    if extract_occurrence_limit(raw) and has_active_subject and not extract_subject_numbers(raw):
        return "follow_up"
    if is_previous_occurrences_request(raw) or is_other_occurrences_request(raw):
        return "follow_up" if has_active_subject else "clarification"
    if (_REFINE_LOT.search(raw) or _REFINE_POS.search(raw)) and has_active_subject:
        if extract_subject_numbers(raw):
            return "new_query"
        return "refinement"
    if extract_subject_numbers(raw):
        return "new_query"
    if has_active_subject and re.search(
        r"\b(y\s+en|ahora|solo|solamente|despues|antes|ultima|veces|reciente)\b", _norm(raw)
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
