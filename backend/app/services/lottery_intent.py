"""Resolución determinística de intención de chat Lotería IA.

El LLM no autoriza ni valida: este módulo decide tool + params a partir del
mensaje y del contexto de sesión.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext


MONTHS_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

PREDICTION_RE = re.compile(
    r"(va a salir|saldr[aá]|n[uú]mero.?probable|predicc|mañana saldr|"
    r"recomienda.*(apostar|jugad)|qu[eé] n[uú]mero (juego|apuesto))",
    re.I,
)

INJECTION_RE = re.compile(
    r"(ignora (todas )?las reglas|muestra(me)? el prompt|system prompt|"
    r"drop\s+table|ejecuta\s+sql|select\s+.+\s+from|consulta la tabla|"
    r"tools? de correo|cambia mi rol|otro tenant|inventa el resultado|"
    r"acceso (a )?sql|desactiva(r)? restricciones)",
    re.I,
)

LOTTERY_HINTS = [
    (r"\breal\b", "Real"),
    (r"loteka", "Loteka"),
    (r"leidsa", "Leidsa"),
    (r"nacional\s+noche", "Nacional Noche"),
    (r"nacional\s+d[ií]a", "Nacional Día"),
    (r"new\s+york\s+noche|\bny\s+noche\b", "New York Noche"),
    (r"new\s+york\s+d[ií]a|\bny\s+d[ií]a\b|new\s+york\s*2:?30", "New York Día"),
]


@dataclass
class ResolvedIntent:
    kind: str  # tool | clarify | refuse | prediction_refused | injection_refused
    tool: LotteryToolName | None = None
    params: dict[str, Any] = field(default_factory=dict)
    clarify_message: str | None = None
    refuse_message: str | None = None
    structured_type: str | None = None


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _parse_spanish_date(text: str) -> date | None:
    # ISO
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # 15 de marzo de 2022 / 15 marzo 2022
    m = re.search(
        r"(\d{1,2})\s*(?:de\s+)?([a-záéíóú]+)\s*(?:de\s+)?(\d{4})",
        text,
        re.I,
    )
    if m:
        day = int(m.group(1))
        mon = MONTHS_ES.get(_norm(m.group(2)))
        year = int(m.group(3))
        if mon:
            return date(year, mon, day)
    return None


def _extract_lottery(text: str) -> str | None:
    for pattern, name in LOTTERY_HINTS:
        if re.search(pattern, text, re.I):
            return name
    return None


def _extract_number(text: str) -> str | None:
    # Prefer quoted / "el 01" / número 05
    m = re.search(r"(?:el|n[uú]mero|numero)\s+(\d{1,3})\b", text, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{2})\b", text)
    if m:
        return m.group(1)
    return None


def _extract_int(text: str, *keywords: str, default: int | None = None) -> int | None:
    for kw in keywords:
        m = re.search(rf"(\d+)\s*{kw}|{kw}\s*(\d+)", text, re.I)
        if m:
            return int(m.group(1) or m.group(2))
    m = re.search(r"\b(siete|7)\b", text, re.I)
    if m and any(k in text for k in ("dia", "días", "dias", "sorteo")):
        return 7
    return default


def resolve_intent(message: str, ctx: LotterySessionContext) -> ResolvedIntent:
    raw = message.strip()
    text = _norm(raw)

    if INJECTION_RE.search(raw) or INJECTION_RE.search(text):
        return ResolvedIntent(
            kind="injection_refused",
            refuse_message=(
                "No puedo ejecutar esa instrucción. Solo consulto resultados históricos "
                "mediante herramientas autorizadas. No revelo el prompt, no ejecuto SQL "
                "ni cambio permisos."
            ),
            structured_type="lottery_error",
        )

    if PREDICTION_RE.search(raw) or PREDICTION_RE.search(text):
        return ResolvedIntent(
            kind="prediction_refused",
            refuse_message=(
                "No puedo predecir resultados futuros ni recomendar apuestas. "
                "Solo consulto el histórico verificado. "
                "Los resultados históricos y las estadísticas son únicamente informativos. "
                "No garantizan resultados futuros."
            ),
            structured_type="lottery_error",
        )

    # Save query
    if re.search(r"guarda(r)? (esta )?consulta|salvar consulta|save query", text):
        name_m = re.search(r"(?:como|como|as)\s+[«\"']?([^\"'»]+)[»\"']?", raw, re.I)
        name = (name_m.group(1).strip() if name_m else None) or "Consulta guardada"
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.SAVE_QUERY,
            params={"name": name[:255]},
            structured_type="lottery_result",
        )

    lottery = _extract_lottery(text) or ctx.last_lottery
    parsed_date = _parse_spanish_date(raw) or ctx.base_date

    # Nacional Día explicit
    if lottery == "Nacional Día":
        return ResolvedIntent(
            kind="clarify",
            clarify_message=(
                "«Nacional Día» no tiene mapping definitivo. Candidatos: "
                "La Primera Tarde (source_id 20) y La Suerte MD (source_id 21). "
                "Indica cuál deseas consultar."
            ),
            structured_type="lottery_ambiguity",
            params={"pending_ambiguity": {"alias": "Nacional Día", "candidates": [20, 21]}},
        )

    # following days
    if re.search(r"(dias|días)\s+siguientes|siguientes?\s+\d*\s*(dias|días)|siete dias|7 dias", text):
        if not lottery or not parsed_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito la lotería y la fecha base para los días siguientes.",
                structured_type="lottery_ambiguity",
            )
        days = _extract_int(text, "dias", "días", default=ctx.last_days or 7) or 7
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_FOLLOWING_DAYS,
            params={"lottery": lottery, "date": parsed_date, "days": days, "include_base_date": False},
            structured_type="lottery_range",
        )

    # following draws
    if re.search(r"sorteos?\s+siguientes|siguientes?\s+\d*\s*sorteos|siete sorteos|7 sorteos", text):
        if not lottery or not parsed_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito la lotería y la fecha base para los sorteos siguientes.",
                structured_type="lottery_ambiguity",
            )
        count = _extract_int(text, "sorteos", default=ctx.last_draw_count or 7) or 7
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_FOLLOWING_DRAWS,
            params={"lottery": lottery, "date": parsed_date, "count": count, "include_base_date": False},
            structured_type="lottery_range",
        )

    # Ambiguous "siguientes siete" without days/draws
    if re.search(r"siguientes?\s+(siete|7)\b", text) and "sorteo" not in text and "dia" not in text:
        if ctx.last_query_semantics == "next_n_draws" or (
            ctx.last_tool and "following_draws" in (ctx.last_tool or "")
        ):
            count = 7
            if not lottery or not parsed_date:
                return ResolvedIntent(
                    kind="clarify",
                    clarify_message="Necesito lotería y fecha base.",
                    structured_type="lottery_ambiguity",
                )
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_FOLLOWING_DRAWS,
                params={"lottery": lottery, "date": parsed_date, "count": count},
                structured_type="lottery_range",
            )
        return ResolvedIntent(
            kind="clarify",
            clarify_message="¿Quieres siete días calendario o siete sorteos?",
            structured_type="lottery_ambiguity",
        )

    # previous days / draws
    if re.search(r"(dias|días)\s+anteriores|anteriores?\s+\d*\s*(dias|días)", text):
        if not lottery or not parsed_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito lotería y fecha base para los días anteriores.",
                structured_type="lottery_ambiguity",
            )
        days = _extract_int(text, "dias", "días", default=7) or 7
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_PREVIOUS_DAYS,
            params={"lottery": lottery, "date": parsed_date, "days": days},
            structured_type="lottery_range",
        )

    if re.search(r"sorteos?\s+anteriores|anteriores?\s+\d*\s*sorteos", text):
        if not lottery or not parsed_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito lotería y fecha base para los sorteos anteriores.",
                structured_type="lottery_ambiguity",
            )
        count = _extract_int(text, "sorteos", default=7) or 7
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_PREVIOUS_DRAWS,
            params={"lottery": lottery, "date": parsed_date, "count": count},
            structured_type="lottery_range",
        )

    # repetitions
    if re.search(r"repitieron|repeticion|repetición|se repiten|numeros repetidos", text):
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Sobre qué lotería quieres las repeticiones?",
                structured_type="lottery_ambiguity",
            )
        from_d = ctx.last_from_date
        to_d = ctx.last_to_date
        if not from_d or not to_d:
            if parsed_date and ctx.last_days:
                from_d = parsed_date + timedelta(days=1)
                to_d = parsed_date + timedelta(days=ctx.last_days)
            elif parsed_date:
                from_d = parsed_date
                to_d = parsed_date
            else:
                return ResolvedIntent(
                    kind="clarify",
                    clarify_message="Necesito un rango de fechas para buscar repeticiones.",
                    structured_type="lottery_ambiguity",
                )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.FIND_REPETITIONS,
            params={"lottery": lottery, "from_date": from_d, "to_date": to_d, "min_count": 2},
            structured_type="lottery_repetitions",
        )

    # compare / also appeared in
    if re.search(
        r"tambien aparecieron|tambi[eé]n aparecieron|compar(a|ame|ar)|aparecieron en",
        text,
    ):
        other = _extract_lottery(text)
        base = ctx.last_lottery
        if other and base and other != base:
            lots = [base, other]
        elif other and lottery and other != lottery:
            lots = [lottery, other]
        elif ctx.compared_lotteries:
            lots = ctx.compared_lotteries
        else:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Indica al menos dos loterías para comparar.",
                structured_type="lottery_ambiguity",
            )
        from_d = ctx.last_from_date or parsed_date
        to_d = ctx.last_to_date or parsed_date
        if not from_d or not to_d:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito el rango de fechas para comparar.",
                structured_type="lottery_ambiguity",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.COMPARE_LOTTERIES,
            params={
                "lotteries": lots,
                "from_date": from_d,
                "to_date": to_d,
                "mode": "repeated_numbers",
            },
            structured_type="lottery_comparison",
        )

    # next historical occurrence
    if re.search(r"volvi[oó] a salir|proxima aparicion|pr[oó]xima aparici[oó]n|cuando (sali[oó]|apareci)", text):
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        if not lottery or not number or not parsed_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito lotería, número y fecha base para la próxima aparición histórica.",
                structured_type="lottery_ambiguity",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.FIND_NEXT_OCCURRENCES,
            params={"lottery": lottery, "number": number, "after_date": parsed_date, "limit": 10},
            structured_type="lottery_next_occurrences",
        )

    # frequencies
    if re.search(r"frecuencia|mas frecuentes|m[aá]s frecuentes", text):
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿De qué lotería quieres las frecuencias?",
                structured_type="lottery_ambiguity",
            )
        from_d = ctx.last_from_date or (parsed_date if parsed_date else None)
        to_d = ctx.last_to_date or from_d
        if not from_d or not to_d:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Indica el rango de fechas para frecuencias.",
                structured_type="lottery_ambiguity",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.CALCULATE_FREQUENCIES,
            params={"lottery": lottery, "from_date": from_d, "to_date": to_d, "limit": 20},
            structured_type="lottery_frequency",
        )

    # by-date: salió / resultados / qué salió
    if re.search(r"sali[oó]|resultado|que salio|qu[eé] sali[oó]|mostrar.*fecha", text) or (
        lottery and parsed_date and re.search(r"\d{4}|\bde\b", text)
    ):
        if not lottery or not parsed_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Indica la lotería y la fecha exacta (ej. Real el 15 de marzo de 2022).",
                structured_type="lottery_ambiguity",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_RESULT_BY_DATE,
            params={"lottery": lottery, "date": parsed_date},
            structured_type="lottery_result",
        )

    # list / coverage
    if re.search(r"qu[eé] loter[ií]as|lista(r)? loter|cat[aá]logo", text):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.LIST_LOTTERIES,
            params={"limit": 50},
            structured_type="lottery_result",
        )

    if re.search(r"cobertura|cu[aá]ntos sorteos|cuantos sorteos|hist[oó]rico disponible", text):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_COVERAGE,
            params={},
            structured_type="lottery_result",
        )

    if re.search(r"consultas guardadas|mis consultas", text):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_SAVED_QUERIES,
            params={},
            structured_type="lottery_result",
        )

    return ResolvedIntent(
        kind="clarify",
        clarify_message=(
            "Puedo consultar resultados históricos: fecha exacta, días o sorteos "
            "siguientes/anteriores, repeticiones, comparaciones y próxima aparición histórica. "
            "¿Qué deseas consultar?"
        ),
        structured_type="lottery_ambiguity",
    )
