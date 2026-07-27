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

SAME_DAY_POLICY_VERSION = "2.4.0"

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
    """Extract ball numbers from text — never quantity N from «últimas N»."""
    from app.lottery.ai.turn_policy import extract_subject_numbers, strip_quantity_spans

    subjects = extract_subject_numbers(text)
    if len(subjects) >= 2:
        return subjects[:8]
    cleaned = strip_quantity_spans(text or "")
    cleaned = re.sub(r"\b20\d{2}\b", " ", cleaned)
    found = re.findall(r"(?:el|n[uú]mero|numero|del)\s+(\d{1,2})\b", cleaned, re.I)
    if len(found) < 2:
        # Only two-digit bare tokens to avoid quantity leftovers
        found = re.findall(r"\b(\d{2})\b", cleaned)
    out: list[str] = []
    for n in found:
        nn = str(n).zfill(2)
        if nn not in out and 0 <= int(nn) <= 99:
            out.append(nn)
    return (subjects + [x for x in out if x not in subjects])[:8]


def is_same_day_coincidence_question(text: str) -> bool:
    t = _norm(text)
    nums = extract_all_numbers(text)
    if _SAME_DAY.search(text or "") and len(nums) >= 2:
        return True
    if len(nums) < 2 and "coinciden" not in t and "juntos" not in t:
        return False
    if _SAME_DAY.search(text or ""):
        return True
    # "han salido alguna vez el 55 y el 24" without explicit "mismo día"
    # still implies co-occurrence when two numbers + "alguna vez" / "juntos"
    if len(nums) >= 2 and re.search(
        r"alguna\s+vez|han\s+salido|salieron|juntos|coincid|mismo\s+d", t
    ):
        # Exclude clear last-occurrence-per-lottery compounds ("en Leidsa y el 44 en Loteka")
        if re.search(r"\ben\s+\w+.+\by\s+el\s+\d.+\ben\s+\w+", t):
            return False
        # Exclude pure compare ("compara el 54 con el 94")
        if re.search(r"\bcomp[aá]ra", t):
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


_LOTTERY_FOLLOW = re.compile(
    r"^\s*(y\s+)?(ahora\s+)?(solo\s+)?(en\s+)?"
    r"(nacional(\s+(noche|dia|día))?|leidsa|loteka|real|gana\s*m[aá]s|"
    r"cash4life|new\s+york(\s+(noche|dia|día))?|lotedom|anguila)\b",
    re.I,
)

_AFTER_COINC = re.compile(
    r"qu[eé]\s+pas[oó]\s+despu[eé]s|despu[eé]s\s+de\s+(esas|las)\s+coinciden|"
    r"qu[eé]\s+sali[oó]\s+despu[eé]s|eventos?\s+posteriores|"
    r"despu[eé]s\s+de\s+(esa|la)\s+coinciden",
    re.I,
)

_RETURN_PAIR = re.compile(
    r"vuelve\s+al?\s+(\d{1,2})\s+y\s+(al?\s+)?(\d{1,2})|"
    r"regresa\s+al?\s+(\d{1,2})\s+y|"
    r"ahora\s+(el\s+)?(\d{1,2})\s+y\s+(el\s+)?(\d{1,2})",
    re.I,
)


def is_lottery_only_follow_up(text: str) -> bool:
    t = (text or "").strip()
    t_clean = re.sub(r"^[¿¡\?\s]+", "", t)
    t_clean = re.sub(r"[¿¡]", "", t_clean)
    matched = bool(_LOTTERY_FOLLOW.search(t_clean) or _LOTTERY_FOLLOW.search(t))
    if not matched:
        # "y en Nacional" / "en Leidsa" short follow-ups
        if not re.search(
            r"^\s*(y\s+)?(ahora\s+)?(solo\s+)?en\s+\w+",
            t_clean,
            re.I,
        ):
            return False
        if not extract_follow_up_lottery(t):
            return False
    # Must not introduce a new number focus
    nums = extract_all_numbers(t)
    return len(nums) == 0


def extract_follow_up_lottery(text: str) -> str | None:
    from app.services.lottery_intent import _extract_lotteries

    lots = _extract_lotteries(text or "")
    return lots[0] if lots else None


def is_after_coincidences_follow_up(text: str) -> bool:
    return bool(_AFTER_COINC.search(text or ""))


def is_return_to_pair(text: str) -> list[str] | None:
    m = _RETURN_PAIR.search(text or "")
    if not m:
        return None
    groups = [g for g in m.groups() if g and str(g).isdigit()]
    if len(groups) >= 2:
        return [str(groups[0]).zfill(2), str(groups[1]).zfill(2)]
    return None


def build_same_day_follow_up_params(
    text: str,
    *,
    active_numbers: list[str],
    active_lotteries: list[str] | None = None,
    position_scope: str | None = None,
    preferred_position: int = 1,
    last_coincidence_date: str | None = None,
) -> dict[str, Any] | None:
    """Continuity params for an active same_day investigation (Fase Final 2.4.0)."""
    nums = list(active_numbers or [])[:8]
    if len(nums) < 2:
        return None

    from app.lottery.ai.compound_occurrence import (
        follow_up_any_position,
        follow_up_first_position,
    )

    lots = list(active_lotteries or [])
    pos = None if (position_scope or "any_position") == "any_position" else 1
    scope = position_scope or "any_position"
    want_last = False
    after = False
    report = is_report_mode_question(text)

    if follow_up_first_position(text) or is_first_position_follow_up(text):
        pos = 1
        scope = "first_position"
    elif follow_up_any_position(text):
        pos = None
        scope = "any_position"
    elif is_lottery_only_follow_up(text):
        lot = extract_follow_up_lottery(text)
        if lot:
            lots = [lot]
    elif is_last_coincidence_follow_up(text):
        want_last = True
    elif is_after_coincidences_follow_up(text):
        after = True
    else:
        returned = is_return_to_pair(text)
        if returned:
            nums = returned
        elif not (
            is_same_day_coincidence_question(text)
            or follow_up_any_position(text)
            or follow_up_first_position(text)
        ):
            # Not a same-day continuity utterance
            if not is_lottery_only_follow_up(text):
                return None

    params: dict[str, Any] = {
        "numbers": nums,
        "relation": "same_day",
        "active_relation": "same_day",
        "position": pos,
        "position_scope": scope,
        "preferred_position": preferred_position,
        "want_last_only": want_last,
        "report_mode": report,
        "intent": "same_day_coincidence",
        "all_historical": True,
        "policy": SAME_DAY_POLICY_VERSION,
    }
    if lots:
        params["lotteries"] = lots[:8]
        params["lottery"] = lots[0]
    if after:
        params["follow_up_kind"] = "after_coincidences"
        params["after_coincidences"] = True
        if last_coincidence_date:
            params["base_date"] = str(last_coincidence_date)[:10]
            params["date"] = str(last_coincidence_date)[:10]
    return params


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
    if total <= 4:
        return (
            f"Observación: con solo {total} caso(s) la muestra es pequeña; "
            "describe lo ocurrido en el histórico, no una regla general."
        )
    if first_related == total:
        return (
            "Interpretación: en todos los casos hubo presencia en primera posición; "
            "eso destaca la preferencia del usuario, sin ocultar el total."
        )
    if first_related == 0:
        return (
            "Interpretación: la coincidencia existe fuera de primera posición; "
            "concluir que 'no hubo coincidencia' sería incorrecto."
        )
    return (
        "Interpretación: conviene mirar el total general y, por separado, "
        "el recorte de primera posición para no confundir preferencia con alcance."
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
