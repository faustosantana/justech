"""Fase X.2 — same-day number coincidence policy + narrative (presentation only).

Does NOT modify Motor, Ranking, Tabla 1/2, Research/Discovery/Knowledge engines.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from app.lottery.ai.compound_occurrence import (
    DEFAULT_PRIMARY_POSITION,
    PositionScope,
    extract_position_scope,
    resolve_effective_position,
)

SAME_DAY_POLICY_VERSION = "2.3.3"

PositionFilter = int | None  # None => all positions


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_SAME_DAY = re.compile(
    r"mismo\s+d[ií]a|misma\s+fecha|el\s+mismo\s+d[ií]a|"
    r"juntos?|coincid(ieron|en|encia|encias)|aparecieron?\s+juntos|"
    r"han\s+salido.*(y|ambos)|sali(eron|ó|o).{0,40}(y|ambos).{0,40}(d[ií]a|juntos)",
    re.I,
)

_REPORT_MODE = re.compile(
    r"analiza(r)?\s+completamente|haz\s+un\s+estudio|comp[aá]rame|"
    r"investiga(r)?\s+el\s+comportamiento|genera(r)?\s+un\s+informe|"
    r"busca(r)?\s+patrones|informe\s+completo|estudio\s+completo",
    re.I,
)

_LAST_COINCIDENCE = re.compile(
    r"[uú]ltima\s+coinciden|[uú]ltima\s+vez\s+que\s+coincid|"
    r"cu[aá]ndo\s+fue\s+la\s+[uú]ltima\s+coinciden|"
    r"la\s+[uú]ltima\s+coinciden",
    re.I,
)

_FIRST_POS_FOLLOW = re.compile(
    r"^(y\s+)?(en\s+)?primera(\s+posici[oó]n)?|"
    r"^(y\s+)?solo\s+en\s+primera|"
    r"^(y\s+)?ahora\s+en\s+primera",
    re.I,
)


def extract_all_numbers(text: str) -> list[str]:
    """Extract ball numbers from text (1–2 digits), de-duplicated, order preserved."""
    cleaned = re.sub(
        r"[uú]ltimos?\s+\d+\s+(sorteos?|dias|días)|"
        r"\b\d+\s+(sorteos?|dias|días)\b|"
        r"\b20\d{2}\b",
        " ",
        text or "",
        flags=re.I,
    )
    found = re.findall(r"(?:el|n[uú]mero|numero)\s+(\d{1,2})\b", cleaned, re.I)
    if len(found) < 2:
        found = re.findall(r"\b(\d{1,2})\b", cleaned)
    out: list[str] = []
    for n in found:
        nn = str(n).zfill(2)
        if nn not in out and 0 <= int(nn) <= 99:
            out.append(nn)
    return out[:8]


def is_same_day_coincidence_question(text: str) -> bool:
    t = _norm(text)
    nums = extract_all_numbers(text)
    if len(nums) < 2 and "coinciden" not in t and "juntos" not in t:
        return False
    if _SAME_DAY.search(text or ""):
        return True
    # "han salido alguna vez el 55 y el 24" without explicit "mismo día"
    # still implies co-occurrence when two numbers + "alguna vez" / "juntos"
    if len(nums) >= 2 and re.search(
        r"alguna\s+vez|han\s+salido|salieron|juntos|coincid", t
    ):
        # Exclude clear last-occurrence-per-lottery compounds ("en Leidsa y el 44 en Loteka")
        if re.search(r"\ben\s+\w+.+\by\s+el\s+\d.+\ben\s+\w+", t):
            return False
        return True
    return False


def is_report_mode_question(text: str) -> bool:
    return bool(_REPORT_MODE.search(text or ""))


def is_last_coincidence_follow_up(text: str) -> bool:
    return bool(_LAST_COINCIDENCE.search(text or ""))


def is_first_position_follow_up(text: str) -> bool:
    t = _norm(text).strip(" ¿?¡!.")
    return bool(_FIRST_POS_FOLLOW.match(t) or re.search(r"^(y\s+)?en\s+primera\s+posicion", t))


def parse_same_day_coincidence(
    text: str,
    *,
    active_numbers: list[str] | None = None,
    pref_scope: PositionScope | None = None,
) -> dict[str, Any] | None:
    """Parse a same-day coincidence question into a structured query."""
    nums = extract_all_numbers(text)
    if len(nums) < 2:
        nums = [str(n).zfill(2) for n in (active_numbers or []) if str(n).isdigit()][:8]
    if len(nums) < 2 and not (
        is_last_coincidence_follow_up(text)
        or is_first_position_follow_up(text)
        or re.search(r"cualquier\s+posici", text or "", re.I)
    ):
        if not is_same_day_coincidence_question(text):
            return None
        return None
    if len(nums) < 2:
        return None

    # Explicit position from text; otherwise ALL positions (preferred=1 is highlight only)
    explicit_scope, explicit_pos = extract_position_scope(text)
    if explicit_scope == "any_position" or (
        pref_scope == "any_position" and explicit_scope == "first_position"
        and not re.search(r"primera|primer[oa]|posicion\s*1", _norm(text))
    ):
        # extract_position_scope returns first_position as legacy default when silent —
        # X.2: silent means all
        if not re.search(
            r"primera|primer[oa]|segund|tercer|posicion\s*[123]|cualquier",
            _norm(text),
        ):
            pos_filter: PositionFilter = None
            scope_used: PositionScope = "any_position"
        elif explicit_scope == "any_position":
            pos_filter = None
            scope_used = "any_position"
        elif explicit_scope == "specific_position" and explicit_pos is not None:
            pos_filter = int(explicit_pos)
            scope_used = "specific_position"
        else:
            pos_filter, scope_used, _ = resolve_effective_position(
                text, pref_scope="any_position"
            )
    elif explicit_scope == "specific_position" and explicit_pos is not None:
        pos_filter = int(explicit_pos)
        scope_used = "specific_position"
    else:
        # No explicit position mention → all positions
        if not re.search(
            r"primera|primer[oa]|segund|tercer|posicion\s*[123]|cualquier",
            _norm(text),
        ):
            pos_filter = None
            scope_used = "any_position"
        else:
            pos_filter, scope_used, _ = resolve_effective_position(
                text, pref_scope=pref_scope or "any_position"
            )

    want_last = is_last_coincidence_follow_up(text)
    report = is_report_mode_question(text)

    return {
        "intent": "same_day_coincidence",
        "active_numbers": nums[:8],
        "active_relation": "same_day",
        "position_scope": scope_used,
        "position": pos_filter,
        "preferred_position": DEFAULT_PRIMARY_POSITION,
        "want_last_only": want_last,
        "report_mode": report,
        "relation": "same_day",
        "numbers": nums[:8],
        "policy": SAME_DAY_POLICY_VERSION,
    }


def classify_position_bucket(entries: list[dict[str, Any]], preferred: int = 1) -> str:
    """both_preferred | one_preferred | other_only."""
    positions = []
    for e in entries:
        try:
            positions.append(int(e.get("position") or 0))
        except (TypeError, ValueError):
            continue
    if not positions:
        return "other_only"
    if all(p == preferred for p in positions) and len(positions) >= 2:
        return "both_preferred"
    if any(p == preferred for p in positions):
        return "one_preferred"
    return "other_only"


def summarize_coincidences(
    payload: dict[str, Any],
    *,
    numbers: list[str],
    preferred_position: int = 1,
    position_filter: PositionFilter = None,
) -> dict[str, Any]:
    """Build position-aware totals from a coincidence payload."""
    items = list(payload.get("items") or payload.get("dates") or [])
    total = int(payload.get("total") if payload.get("total") is not None else len(items))
    both_pref = 0
    one_pref = 0
    other_only = 0
    for it in items:
        entries = list(it.get("appearances") or it.get("entries") or [])
        bucket = classify_position_bucket(entries, preferred_position)
        if bucket == "both_preferred":
            both_pref += 1
        elif bucket == "one_preferred":
            one_pref += 1
        else:
            other_only += 1
    first_related = both_pref + one_pref
    last = items[0] if items else None
    return {
        "numbers": numbers,
        "total": total,
        "both_first": both_pref,
        "one_first": one_pref,
        "first_related": first_related,
        "other_only": other_only,
        "position_filter": position_filter,
        "preferred_position": preferred_position,
        "last": last,
        "items": items,
        "zero_total": total == 0,
        "searched_all_positions": position_filter is None,
        "searched_all_lotteries": bool(payload.get("all_lotteries", True)),
    }


def format_coincidence_narrative(
    summary: dict[str, Any],
    *,
    report_mode: bool = False,
    want_last_only: bool = False,
) -> str:
    """User-facing natural language — no internal jargon."""
    nums = summary.get("numbers") or []
    label = " y ".join(str(n) for n in nums[:4]) if nums else "los números"
    total = int(summary.get("total") or 0)
    first_related = int(summary.get("first_related") or 0)
    other_only = int(summary.get("other_only") or 0)
    pos_filter = summary.get("position_filter")
    last = summary.get("last")

    if want_last_only:
        if not last or total == 0:
            return (
                f"No encontré coincidencias de {label} en una misma fecha "
                "dentro del histórico disponible, considerando todas las loterías "
                "y todas las posiciones."
                if summary.get("searched_all_positions")
                else (
                    f"No encontré coincidencias de {label} en la posición solicitada "
                    "dentro del histórico disponible."
                )
            )
        return _format_last_block(label, last) + _brief_observation(summary)

    if total == 0:
        scope = (
            "todas las loterías y todas las posiciones"
            if summary.get("searched_all_positions")
            else "el alcance de posición indicado"
        )
        return (
            f"No encontré coincidencias de {label} en una misma fecha "
            f"dentro del histórico disponible, considerando {scope}."
        )

    # Filtered to first only but we still know other totals if provided
    if pos_filter == 1:
        lines = [
            f"En primera posición, {label} coincidieron el mismo día en "
            f"{first_related} ocasión(es)."
        ]
        if other_only or (summary.get("total_all_positions") is not None):
            all_t = summary.get("total_all_positions")
            if all_t and int(all_t) > first_related:
                lines.append(
                    f"Si se consideran todas las posiciones, hay {all_t} fechas "
                    f"con coincidencia; {int(all_t) - first_related} ocurrieron "
                    "fuera de primera posición."
                )
        if last:
            lines.append(_format_last_block(label, last))
        lines.append(_brief_observation(summary))
        return "\n\n".join(x for x in lines if x).strip()

    # Default: all positions, highlight first
    lines = [
        f"Sí. {label} coincidieron el mismo día en {total} ocasión(es) "
        "considerando todas las posiciones."
    ]
    lines.append(
        "En primera posición:\n"
        f"- {first_related} caso(s) con al menos uno de los números en primera "
        f"(ambos en primera: {int(summary.get('both_first') or 0)})."
    )
    lines.append(f"En otras posiciones:\n- {other_only} caso(s).")

    if first_related == 0 and other_only > 0:
        lines.insert(
            1,
            f"No aparecieron juntos en primera posición, pero sí coincidieron "
            f"en {total} fechas al considerar todas las posiciones.",
        )

    if last:
        lines.append(_format_last_block(label, last))

    if report_mode:
        lines.append(
            "Observación: el desglose separa la preferencia de primera posición "
            "del total real; ninguna coincidencia fuera de primera queda oculta."
        )
    else:
        lines.append(_brief_observation(summary))

    return "\n\n".join(x for x in lines if x).strip()


def _format_last_block(label: str, last: dict[str, Any]) -> str:
    date_s = str(last.get("date") or last.get("draw_date") or "—")
    entries = list(last.get("appearances") or last.get("entries") or [])
    bits = [f"La coincidencia más reciente fue el {date_s}:"]
    for e in entries[:6]:
        num = e.get("number")
        lot = e.get("lottery") or "lotería"
        pos = e.get("position_label") or e.get("position") or "?"
        bits.append(f"- {num} en {lot}, posición {pos}.")
    if not entries:
        bits.append(f"- Detalle de apariciones no disponible para {label}.")
    return "\n".join(bits)


def _brief_observation(summary: dict[str, Any]) -> str:
    total = int(summary.get("total") or 0)
    first_related = int(summary.get("first_related") or 0)
    if total == 0:
        return ""
    if first_related == total:
        return "Observación: en todos los casos hubo presencia en primera posición."
    if first_related == 0:
        return (
            "Observación: la coincidencia existe, pero no en primera posición; "
            "la preferencia de primera no excluye el resto del histórico."
        )
    return (
        "Observación: conviene mirar el total general y, por separado, "
        "el recorte de primera posición."
    )


def coincidence_suggestions(numbers: list[str]) -> list[str]:
    if len(numbers) < 2:
        return [
            "Ver fechas de coincidencia.",
            "Desglosar por posición.",
            "Ver la última coincidencia.",
        ]
    a, b = numbers[0], numbers[1]
    return [
        "Ver fechas de coincidencia.",
        "Desglosar por posición.",
        "Ver coincidencias en primera.",
        "Ver la última coincidencia.",
        f"Analizar qué pasó después de {a} + {b}.",
    ]


def analyzing_label(numbers: list[str], *, relation: str | None = None) -> str:
    if len(numbers) >= 2:
        joined = " + ".join(str(n) for n in numbers[:4])
        if relation == "same_day":
            return f"coincidencias de {' y '.join(str(n) for n in numbers[:2])}"
        return joined
    if numbers:
        return str(numbers[0])
    return "—"
