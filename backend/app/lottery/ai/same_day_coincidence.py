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

# Demonstrative / list follow-ups that inherit the prior coincidence EVENT
# («esas últimas 3 veces», «esas fechas», «muéstrame las anteriores», «¿cuáles fueron?»).
_EVENT_LIST_FOLLOW = re.compile(
    r"("
    r"esas?\s+([uú]ltimas?\s+)?(\d{1,2}\s+)?(veces|fechas|apariciones|coinciden)|"
    r"aquellas?\s+([uú]ltimas?\s+)?(\d{1,2}\s+)?(veces|fechas|apariciones)|"
    r"cu[aá]les\s+fueron(\s+esas?)?|"
    r"(mué?strame|dame|lista|enumera)\s+(las?\s+)?(anteriores|fechas|coinciden)|"
    r"las?\s+anteriores|"
    r"ambos|"
    r"los\s+dos|"
    r"esa\s+coinciden|"
    r"esas?\s+(\d{1,2}|tres|cinco|diez)\b|"
    r"[uú]ltimas?\s+(\d{1,2}|tres|cinco)\s+veces|"
    r"las?\s+(\d{1,2}|tres|cinco)\s+coinciden"
    r")",
    re.I,
)

# Attribute follow-ups on the active coincidence EVENT (lotteries / positions / date)
_EVENT_ATTR_FOLLOW = re.compile(
    r"("
    r"(en\s+)?(cu[aá]les?|qu[eé])\s+loter[ií]as?|"
    r"(en\s+)?(qu[eé]|cu[aá]les?)\s+posiciones?|"
    r"y\s+las?\s+posiciones?|"
    r"en\s+qu[eé]\s+loter|"
    r"en\s+qu[eé]\s+posiciones?|"
    r"d[oó]nde\s+(ocurri[oó]|sali[oó]|fue)|"
    r"cu[aá]ndo\s+fue(\s+eso)?|"
    r"esa\s+fecha|"
    r"en\s+qu[eé]\s+orden|"
    r"m[aá]s\s+detalles|"
    r"expl[ií]came(\s+mejor)?|"
    r"por\s+qu[eé]\s+dices|"
    r"qu[eé]\s+significa"
    r")",
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


def is_event_list_follow_up(text: str) -> bool:
    """True when the utterance points at prior coincidence dates/times/list."""
    return bool(_EVENT_LIST_FOLLOW.search(text or ""))


def is_event_attribute_follow_up(text: str) -> bool:
    """True when asking lotteries/positions/date of the prior coincidence event."""
    return bool(_EVENT_ATTR_FOLLOW.search(text or ""))


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
    list_mode = False
    list_limit: int | None = None

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
    elif is_event_list_follow_up(text):
        # «esas últimas 3 veces» / «esas fechas» → list prior coincidence EVENT
        list_mode = True
        from app.lottery.ai.turn_policy import extract_occurrence_limit

        list_limit = extract_occurrence_limit(text) or 3
    elif is_event_attribute_follow_up(text):
        # «¿En cuáles loterías?» / «¿Y en qué posiciones?» → keep EVENT, prefer last
        want_last = True
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
        "list_mode": list_mode,
        "intent": "same_day_coincidence",
        "all_historical": True,
        "use_active_pair": True,
        "policy": SAME_DAY_POLICY_VERSION,
    }
    if list_limit is not None:
        params["limit"] = int(list_limit)
    if lots:
        params["lotteries"] = lots[:8]
        params["lottery"] = lots[0]
    if after:
        params["follow_up_kind"] = "after_coincidences"
        params["after_coincidences"] = True
        if last_coincidence_date:
            params["base_date"] = str(last_coincidence_date)[:10]
            params["date"] = str(last_coincidence_date)[:10]
    if is_event_attribute_follow_up(text):
        from app.lottery.ai.active_investigation.contextual_follow_up import (
            ContextualFollowUpResolver,
        )

        attr = ContextualFollowUpResolver.detect_attribute(text)
        if attr:
            params["requested_attribute"] = attr
            params["follow_up_kind"] = attr
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


def format_coincidence_list(
    summary: dict[str, Any],
    *,
    limit: int | None = None,
) -> str:
    """List coincidence events with per-number concrete positions (never filter scope)."""
    from app.lottery.ai.turn_policy import position_label_es

    nums = [str(n) for n in (summary.get("numbers") or [])][:2]
    items = list(summary.get("items") or summary.get("dates") or [])
    lim = max(1, min(int(limit or summary.get("limit") or 3), 20))
    rows = items[:lim]
    if not rows:
        label = " y ".join(nums) if nums else "los números"
        return f"No encontré fechas de coincidencia listables para {label}."

    lines = [f"Las {len(rows)} coincidencias más recientes fueron:"]
    for i, it in enumerate(rows, 1):
        if not isinstance(it, dict):
            lines.append(f"{i}. {str(it)[:10]}")
            continue
        date_s = str(it.get("date") or it.get("draw_date") or "—")[:10]
        lot = str(it.get("lottery") or "—")
        entries = list(it.get("appearances") or it.get("entries") or [])
        if entries:
            parts = []
            for e in entries[:4]:
                n = str(e.get("number") or "?")
                pos_raw = e.get("position_label") or e.get("position")
                pos_s = position_label_es(pos_raw)
                e_lot = e.get("lottery")
                if e_lot and str(e_lot) != lot:
                    parts.append(f"{n} en {pos_s} ({e_lot})")
                else:
                    parts.append(f"{n} en {pos_s}")
            detail = "; ".join(parts)
            lines.append(f"{i}. {date_s} — {lot} — {detail}.")
        elif len(nums) >= 2:
            # Fallback when payload lacks per-ball positions
            lines.append(
                f"{i}. {date_s} — {lot} — {nums[0]} y {nums[1]} (posiciones no detalladas)."
            )
        else:
            lines.append(f"{i}. {date_s} — {lot}.")
    return "\n".join(lines)


def format_coincidence_narrative(
    summary: dict[str, Any],
    *,
    report_mode: bool = False,
    want_last_only: bool = False,
    list_mode: bool = False,
    limit: int | None = None,
) -> str:
    """User-facing natural language — no internal jargon."""
    if list_mode:
        return format_coincidence_list(summary, limit=limit)

    nums = summary.get("numbers") or []
    label = " y ".join(str(n) for n in nums[:4]) if nums else "los números"
    total = int(summary.get("total") or 0)
    first_related = int(summary.get("first_related") or 0)
    other_only = int(summary.get("other_only") or 0)
    pos_filter = summary.get("position_filter")
    last = summary.get("last")

    if want_last_only:
        if not last or total == 0:
            from app.lottery.ai.official_lottery_scope import scope_label_es

            return (
                f"No encontré coincidencias de {label} en una misma fecha "
                f"dentro del histórico disponible, buscando en {scope_label_es()} "
                "y en todas las posiciones."
                if summary.get("searched_all_positions")
                else (
                    f"No encontré coincidencias de {label} en la posición solicitada "
                    "dentro del histórico disponible."
                )
            )
        return _format_last_block(label, last) + _brief_observation(summary)

    if total == 0:
        from app.lottery.ai.official_lottery_scope import scope_label_es

        scope = (
            f"{scope_label_es()} (buscando en todas las posiciones)"
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
            f"En 1ra posición, {label} coincidieron el mismo día en "
            f"{first_related} ocasión(es)."
        ]
        if other_only or (summary.get("total_all_positions") is not None):
            all_t = summary.get("total_all_positions")
            if all_t and int(all_t) > first_related:
                lines.append(
                    f"Si se busca en todas las posiciones, hay {all_t} fechas "
                    f"con coincidencia; {int(all_t) - first_related} ocurrieron "
                    "fuera de 1ra posición."
                )
        if last:
            lines.append(_format_last_block(label, last))
        lines.append(_brief_observation(summary))
        return "\n\n".join(x for x in lines if x).strip()

    # Default: all positions as search scope (once), then concrete last event
    lines = [
        f"Sí. {label} coincidieron el mismo día en {total} ocasión(es) "
        "(buscando en todas las posiciones)."
    ]
    lines.append(
        "En 1ra posición:\n"
        f"- {first_related} caso(s) con al menos uno de los números en 1ra "
        f"(ambos en 1ra: {int(summary.get('both_first') or 0)})."
    )
    lines.append(f"En otras posiciones:\n- {other_only} caso(s).")

    if first_related == 0 and other_only > 0:
        lines.insert(
            1,
            f"No aparecieron juntos en 1ra posición, pero sí coincidieron "
            f"en {total} fechas al buscar en todas las posiciones.",
        )

    if last:
        lines.append(_format_last_block(label, last))

    if report_mode:
        lines.append(
            "Observación: el desglose separa la preferencia de 1ra posición "
            "del total real; ninguna coincidencia fuera de 1ra queda oculta."
        )
    else:
        lines.append(_brief_observation(summary))

    return "\n\n".join(x for x in lines if x).strip()


def _format_last_block(label: str, last: dict[str, Any]) -> str:
    from app.lottery.ai.turn_policy import position_label_es

    date_s = str(last.get("date") or last.get("draw_date") or "—")
    entries = list(last.get("appearances") or last.get("entries") or [])
    lot = last.get("lottery") or ""
    bits = [f"La coincidencia más reciente fue el {date_s}" + (f" en {lot}" if lot else "") + ":"]
    for e in entries[:6]:
        num = e.get("number")
        e_lot = e.get("lottery") or lot or "lotería"
        pos_raw = e.get("position_label") or e.get("position")
        pos = position_label_es(pos_raw)
        bits.append(f"- {num} en {e_lot}, {pos}.")
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
    """Suggestions aligned with Conversational Routing 3.0 Path B acts."""
    if len(numbers) < 2:
        return [
            "Muéstrame esos resultados.",
            "Ver fechas de coincidencia.",
            "Desglosar por posición.",
        ]
    a, b = numbers[0], numbers[1]
    return [
        "Muéstrame esos resultados.",
        "Ver fechas de coincidencia.",
        "Desglosar por posición.",
        "Exportar Excel.",
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
