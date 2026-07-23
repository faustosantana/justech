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

WORD_NUMBERS = {
    "un": 1,
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
    "quince": 15,
    "veinte": 20,
    "treinta": 30,
}

PREDICTION_RE = re.compile(
    r"(va a salir|saldr[aá]|n[uú]mero.?probable|predicc|predecir|permite predecir|"
    r"siguiente sorteo|pr[oó]ximo resultado|mañana saldr|"
    r"recomienda.*(apostar|jugad)|qu[eé] n[uú]mero (juego|apuesto)|"
    r"n[uú]mero para apostar|para apostar|apostar ma[nñ]ana|qu[eé] juego)",
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
    (r"quiniela\s+real|\breal\b", "Real"),
    (r"quiniela\s+loteka|loteka", "Loteka"),
    (r"quiniela\s+leidsa|leidsa", "Leidsa"),
    (r"loter[ií]a\s+nacional|nacional\s+noche", "Nacional Noche"),
    (r"nacional\s+d[ií]a", "Nacional Día"),
    (r"new\s+york\s+noche|\bny\s+noche\b", "New York Noche"),
    (r"new\s+york\s+d[ií]a|\bny\s+d[ií]a\b|new\s+york\s*2:?30", "New York Día"),
]

DEFAULT_COMPARE_TRIPLE = ["Real", "Nacional Noche", "Leidsa"]


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
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
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
    found = _extract_lotteries(text)
    return found[0] if found else None


def _extract_lotteries(text: str) -> list[str]:
    hits: list[tuple[int, str]] = []
    for pattern, name in LOTTERY_HINTS:
        for m in re.finditer(pattern, text, re.I):
            hits.append((m.start(), name))
    hits.sort(key=lambda x: x[0])
    out: list[str] = []
    for _, name in hits:
        if name not in out:
            out.append(name)
    return out


def _extract_number(text: str) -> str | None:
    # Avoid treating "últimos 30 sorteos" / "7 días" as a ball number.
    cleaned = re.sub(
        r"[uú]ltimos?\s+\d+\s+(sorteos?|dias|días)|"
        r"\b\d+\s+(sorteos?|dias|días)\s+siguientes|"
        r"siguientes?\s+\d+\s+(sorteos?|dias|días)|"
        r"\b\d+\s+sorteos?\b|\b\d+\s+dias\b|\b\d+\s+días\b",
        " ",
        text,
        flags=re.I,
    )
    m = re.search(r"(?:el|n[uú]mero|numero)\s+(\d{1,3})\b", cleaned, re.I)
    if m:
        return m.group(1).zfill(2) if len(m.group(1)) <= 2 else m.group(1)
    m = re.search(r"\b(\d{2})\b", cleaned)
    if m:
        return m.group(1)
    return None


def _word_or_digit(token: str) -> int | None:
    t = _norm(token)
    if t.isdigit():
        return int(t)
    return WORD_NUMBERS.get(t)


def _extract_int(text: str, *keywords: str, default: int | None = None) -> int | None:
    ntext = _norm(text)
    for kw in keywords:
        m = re.search(rf"(\d+)\s*{kw}|{kw}\s*(\d+)", ntext, re.I)
        if m:
            return int(m.group(1) or m.group(2))
        m = re.search(
            rf"\b({'|'.join(WORD_NUMBERS.keys())})\s+{kw}|{kw}\s+({'|'.join(WORD_NUMBERS.keys())})\b",
            ntext,
            re.I,
        )
        if m:
            val = _word_or_digit(m.group(1) or m.group(2) or "")
            if val is not None:
                return val
    # "los cinco sorteos siguientes" / "siguientes cinco sorteos"
    m = re.search(
        rf"\b({'|'.join(WORD_NUMBERS.keys())}|\d+)\s+sorteos?\b|\bsorteos?\s+({'|'.join(WORD_NUMBERS.keys())}|\d+)\b",
        ntext,
        re.I,
    )
    if m and any(k in keywords for k in ("sorteos", "sorteo")):
        val = _word_or_digit(m.group(1) or m.group(2) or "")
        if val is not None:
            return val
    m = re.search(r"\b(siete|7)\b", ntext, re.I)
    if m and any(k in ntext for k in ("dia", "dias", "sorteo")):
        return 7
    return default


def _last_n_window(n: int, *, anchor: date | None = None) -> tuple[date, date]:
    """Aproxima N sorteos diarios como N días calendario hasta hoy (o ancla)."""
    end = anchor or date.today()
    start = end - timedelta(days=max(n - 1, 0))
    return start, end


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

    # 4.1 — year-over-year / period compare for a number
    if re.search(
        r"(ha|has|han)\s+salido\s+m[aá]s|"
        r"m[aá]s\s+(este|el)\s+a[nñ]o|"
        r"compar(a|ar).*(a[nñ]o\s+pasado|este\s+a[nñ]o)|"
        r"este\s+a[nñ]o\s+que\s+(el\s+)?(a[nñ]o\s+)?pasado",
        text,
    ):
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        lottery = _extract_lottery(text) or ctx.last_lottery
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Qué número quieres comparar entre este año y el anterior?",
                structured_type="lottery_ambiguity",
            )
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message=(
                    f"¿En cuál lotería comparo el {number} entre este año y el pasado? "
                    "También puedo hacerlo en todas las sincronizadas."
                ),
                structured_type="lottery_ambiguity",
                params={"number": number, "pending_slots": ["lottery"]},
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.COMPARE_NUMBER_PERIODS,
            params={
                "lottery": lottery,
                "number": number,
                "period_a": "current_year",
                "period_b": "previous_year",
            },
            structured_type="lottery_comparison",
        )

    if re.search(r"analiz(a|ar|ame|emos)\s+(el\s+)?\d+|analiz(a|ar)\s+el\s+n[uú]mero", text):
        number = _extract_number(raw)
        lottery = _extract_lottery(text) or ctx.last_lottery
        if number and not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message=(
                    f"Claro. ¿Quieres analizar el {number} en una lotería específica o compararlo entre todas? "
                    "También puedo revisar todo el historial, el último año o los últimos 30 sorteos."
                ),
                structured_type="lottery_ambiguity",
                params={"number": number, "pending_slots": ["lottery", "period"]},
            )

    if re.search(
        r"analiz(a|ar).*(completa|completa(mente)?|resumen)|"
        r"haz(me)?\s+un\s+an[aá]lisis|dame\s+lo\s+m[aá]s\s+importante|"
        r"analiz(a|ala)\s+(la\s+)?(real|leidsa|loteka|nacional)",
        text,
    ):
        lottery = _extract_lottery(text) or ctx.last_lottery
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿De qué lotería quieres el resumen analítico?",
                structured_type="lottery_ambiguity",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_LOTTERY_SUMMARY,
            params={"lottery": lottery},
            structured_type="lottery_result",
        )

    if re.search(
        r"m[aá]s\s+actualizada|ultima\s+fecha|hasta\s+qu[eé]\s+fecha|"
        r"[uú]ltima\s+fecha\s+disponible",
        text,
    ):
        lottery = _extract_lottery(text) or ctx.last_lottery
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_LATEST_AVAILABLE_DATE,
            params={"lottery": lottery} if lottery else {},
            structured_type="lottery_result",
        )

    if re.search(r"datos?\s+incompletos|completitud|qu[eé]\s+tan\s+confiables?", text):
        lottery = _extract_lottery(text) or ctx.last_lottery
        if re.search(r"confiables?|confianza", text):
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.EXPLAIN_ANALYSIS_METHOD,
                params={"metric": "general"},
                structured_type="lottery_result",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_DATA_COMPLETENESS,
            params={"lottery": lottery} if lottery else {},
            structured_type="lottery_result",
        )

    if re.search(r"fr[ií]o\s+por\s+tiempo|atrasad|por\s+intervalo|no\s+por\s+frecuencia", text):
        lottery = _extract_lottery(text) or ctx.last_lottery
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿En qué lotería quieres los atrasados (frío por intervalo/tiempo)?",
                structured_type="lottery_ambiguity",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_OVERDUE_NUMBERS,
            params={"lottery": lottery, "focus": "cold_interval", "window_draws": ctx.last_draw_count or 30},
            structured_type="lottery_result",
        )

    # Lottery 3.0 — operational / analyst intents
    if re.search(
        r"qu[eé]\s+per[ií]odo\s+(analiz|usaste|revis)|"
        r"cu[aá]ntos?\s+sorteos?\s+(utiliz|analiz|usaste|revis)|"
        r"qu[eé]\s+par[aá]metros?\s+(usaste|empleaste|aplicaste)|"
        r"muestra\s+(usaste|analiz)",
        text,
    ):
        # Prefer last hot/cold context; otherwise coverage summary
        if ctx.last_lottery or (ctx.last_tool and "hot" in (ctx.last_tool or "")):
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_HOT_COLD,
                params={
                    "lottery": ctx.last_lottery or "Leidsa",
                    "focus": "definition",
                    "window_draws": 30,
                    "explain_only": True,
                    "report_params": True,
                },
                structured_type="lottery_result",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_COVERAGE,
            params={},
            structured_type="lottery_result",
        )
    if re.search(
        r"cu[aá]ntos?\s+resultados?\s+(hay\s+)?hoy|"
        r"resultados?\s+hoy|"
        r"resultados?\s+pendientes|"
        r"pendientes?\s+hoy|"
        r"hay\s+resultados?\s+pendientes|"
        r"por qu[eé].*resultados?\s+hoy|"
        r"qu[eé] loter[ií]as.*(no|a[uú]n).*(sincron|hoy)|"
        r"faltan.*(hoy|sincron)|cu[aá]ntos?\s+faltan|"
        r"qu[eé] datos faltan( hoy)?|datos te faltan",
        text,
    ):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_MISSING_TODAY,
            params={},
            structured_type="lottery_result",
        )
    if re.search(
        r"por qu[eé].*(solo|solamente).*(sincron|tres|3)|"
        r"solo sincronizan|solamente sincronizan|"
        r"por qu[eé].*tres loter|"
        r"auto[- ]?write|escritura autom[aá]tica",
        text,
    ):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_SYNC_STATUS,
            params={"explain_auto_write_trio": True},
            structured_type="lottery_result",
        )
    if re.search(
        r"pr[oó]xima sincronizaci[oó]n|pr[oó]xima sync|ventana(s)? de sync|"
        r"cu[aá]ndo.*(ser[aá]|es).*sincron",
        text,
    ):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_SYNC_WINDOWS,
            params={},
            structured_type="lottery_result",
        )
    if re.search(
        r"fuentes?.*(degrad|salud|health)|circuit\s*breaker|"
        r"sincronizaci[oó]n.*(estado|status)|[uú]ltima sincronizaci[oó]n|"
        r"loter[ií]as.*(estan|están)?\s*sincronizando|qu[eé] loter[ií]as.*(sync|sincron)",
        text,
    ):
        if re.search(r"fuente|degrad|health|circuit", text):
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_SOURCE_HEALTH,
                params={},
                structured_type="lottery_result",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_SYNC_STATUS,
            params={},
            structured_type="lottery_result",
        )
    if re.search(r"anomal[ií]as|inconsistencias|calidad de datos", text):
        # quality/anomalies need a lottery — defer to later extraction
        pass

    if re.search(r"guarda(r)? (esta )?consulta|salvar consulta|save query", text):
        name_m = re.search(r"(?:como|como|as)\s+[«\"']?([^\"'»]+)[»\"']?", raw, re.I)
        name = (name_m.group(1).strip() if name_m else None) or "Consulta guardada"
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.SAVE_QUERY,
            params={"name": name[:255]},
            structured_type="lottery_result",
        )

    mentioned = _extract_lotteries(text)
    lottery = mentioned[0] if mentioned else ctx.last_lottery
    parsed_date = _parse_spanish_date(raw)  # do not inherit ctx date for unrelated number queries
    ctx_date = parsed_date or ctx.base_date

    def_hot_cold = bool(
        re.search(
            r"(qu[eé]\s+(significa|es\b|quiere\s+decir)|diferencia.*entre|en\s+qu[eé]\s+se\s+diferencia).*"
            r"(caliente|fr[ií]o|atrasad)",
            text,
        )
        or re.search(
            r"(caliente|fr[ií]o|atrasad).*(significa|definición|definicion|vs|versus|o\s+atrasad)",
            text,
        )
        or re.search(r"diferencia.*fr[ií]o.*atrasad|fr[ií]o\s+y\s+atrasad", text)
    )
    hot_cold_list = bool(
        re.search(
            r"("
            r"n[uú]meros?\s+(m[aá]s\s+)?(calientes?|fr[ií]os?|atrasados?)|"
            r"(est[aá]n|estan)\s+(calientes?|fr[ií]os?|atrasados?)|"
            r"(los\s+)?(m[aá]s\s+)?(calientes?|fr[ií]os?|atrasados?)\b|"
            r"calientes?\s+y\s+fr[ií]os?|"
            r"fr[ií]os?\s+por\s+frecuencia|"
            r"llevan\s+m[aá]s\s+tiempo\s+sin\s+(aparecer|salir)|"
            r"m[aá]s\s+tiempo\s+sin\s+(aparecer|salir)|"
            r"sin\s+aparecer|"
            r"compar(a|e).*calientes?"
            r")",
            text,
        )
    )
    if def_hot_cold or hot_cold_list:
        focus = "both"
        if def_hot_cold:
            focus = "definition"
        elif re.search(
            r"atrasad|sin\s+aparecer|llevan\s+m[aá]s\s+tiempo|m[aá]s\s+tiempo\s+sin",
            text,
        ) and not re.search(r"calientes?", text):
            focus = "cold_interval"
        elif re.search(r"fr[ií]os?.*frecuencia|frecuencia.*fr[ií]os?|m[aá]s\s+fr[ií]os?\s+por\s+frecuencia", text):
            focus = "cold_frequency"
        elif re.search(r"\bfr[ií]os?\b", text) and not re.search(r"calientes?", text):
            focus = "cold_interval"
        elif re.search(r"calientes?", text) and not re.search(r"fr[ií]os?|atrasad", text):
            focus = "hot"
        if not lottery and focus != "definition":
            return ResolvedIntent(
                kind="clarify",
                clarify_message=(
                    "¿De qué lotería quieres el análisis de números calientes/fríos "
                    "(descriptivo histórico, no predicción)?"
                ),
                structured_type="lottery_ambiguity",
            )
        window = 30
        wm = re.search(r"[uú]ltimos?\s+(\d+)\s+sorteos?", text)
        if wm:
            window = max(5, min(365, int(wm.group(1))))
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_HOT_COLD,
            params={
                "lottery": lottery or ctx.last_lottery or "Leidsa",
                "focus": focus,
                "window_draws": window,
                "explain_only": focus == "definition",
            },
            structured_type="lottery_result",
        )
    if re.search(r"anomal[ií]as|calidad de (los )?datos|inconsistencias de (los )?datos", text) and lottery:
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_DATA_QUALITY,
            params={"lottery": lottery},
            structured_type="lottery_result",
        )

    if lottery == "Nacional Día" or "Nacional Día" in mentioned or re.search(
        r"por que no.*(nacional\s+d[ií]a)|no puedes consultar nacional",
        text,
    ):
        return ResolvedIntent(
            kind="clarify",
            clarify_message=(
                "No consulto «Nacional Día» porque no tiene mapping definitivo en JAIOS. "
                "Candidatos históricos: La Primera Tarde (source_id 20) y La Suerte MD "
                "(source_id 21). Indica cuál deseas para consultar datos reales."
            ),
            structured_type="lottery_ambiguity",
            params={"pending_ambiguity": {"alias": "Nacional Día", "candidates": [20, 21]}},
        )

    if re.search(r"que loter[ií]as puedo|loter[ií]as (puedo|disponibles)|lista(r)? loter", text):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.LIST_LOTTERIES,
            params={"limit": 100, "searchable_only": True},
            structured_type="lottery_result",
        )

    if re.search(r"fuente de (los )?datos|de donde (salen|vienen)|source_id|adapter", text):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_SYNC_STATUS,
            params={},
            structured_type="lottery_result",
        )

    if re.search(r"que datos te faltan|qu[eé] te falta|limitaciones de (la )?data|faltantes", text):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_COVERAGE,
            params={},
            structured_type="lottery_result",
        )

    if re.search(r"actualizadas? hasta hoy|al d[ií]a|estan actualizadas", text):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_LATEST_RESULTS,
            params={"limit": 20},
            structured_type="lottery_result",
        )

    if re.search(r"analiza(r)? los [uú]ltimos|analisis de los [uú]ltimos|frecuencias? de", text):
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿De qué lotería quieres el análisis de los últimos sorteos?",
                structured_type="lottery_ambiguity",
            )
        n = _extract_int(text, "sorteos", "sorteo", default=30) or 30
        from_d, to_d = _last_n_window(n)
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.CALCULATE_FREQUENCIES,
            params={"lottery": lottery, "from_date": from_d, "to_date": to_d, "limit": 15},
            structured_type="lottery_frequency",
        )

    if re.search(r"coincid(ieron|en)|numeros? (en )?comun|aparecieron en (esas|ambas)", text):
        lots = list(mentioned) or list(ctx.compared_lotteries or [])
        if ctx.last_lottery and ctx.last_lottery not in lots:
            lots = [ctx.last_lottery, *lots]
        if len(lots) < 2:
            lots = ["Leidsa", "Loteka", "Nacional Noche"]
        from_d, to_d = _last_n_window(7)
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.COMPARE_LOTTERIES,
            params={
                "lotteries": lots[:10],
                "from_date": from_d,
                "to_date": to_d,
                "mode": "repeated_numbers",
            },
            structured_type="lottery_comparison",
        )

    # coverage / freshness — before generic "salió"
    if re.search(
        r"hasta que fecha|hasta qu[eé] fecha|est[aá] actualizada|fecha.*actualiz|"
        r"cobertura hist[oó]rica|mas cobertura|m[aá]s cobertura|mayor cobertura|"
        r"cu[aá]ntos sorteos|cuantos sorteos|hist[oó]rico disponible",
        text,
    ):
        if re.search(r"actualiz|hasta que fecha|hasta qu[eé] fecha", text) and lottery:
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_DRAW_COUNT,
                params={"lottery": lottery},
                structured_type="lottery_result",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_COVERAGE,
            params={},
            structured_type="lottery_result",
        )

    # count occurrences: "cuántas veces salió el 01"
    if re.search(r"cu[aá]ntas?\s+veces|cuantas?\s+veces|cu[aá]ntas?\s+apariciones", text):
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Qué número quieres contar? También indica la lotería si aún no la mencionaste.",
                structured_type="lottery_ambiguity",
            )
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message=(
                    f"¿En cuál lotería quieres contar las apariciones del {number}? "
                    "Puedo revisarlo en una específica o en todas las disponibles."
                ),
                structured_type="lottery_ambiguity",
                params={"number": number, "pending_slots": ["lottery"]},
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_NUMBER_OCCURRENCES,
            params={"lottery": lottery, "number": number, "page": 1, "page_size": 50},
            structured_type="lottery_result",
        )

    # last occurrence: "última vez que salió el 19"
    if re.search(
        r"[uú]ltima\s+vez|cuando fue la ultima|cu[aá]ndo fue la [uú]ltima|"
        r"cu[aá]ndo\s+(fue\s+)?la\s+[uú]ltima\s+vez|hace\s+cu[aá]nto.*(sali[oó]|apareci)",
        text,
    ):
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿De qué número quieres la última aparición? También indica la lotería.",
                structured_type="lottery_ambiguity",
            )
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message=(
                    f"¿En cuál lotería quieres que busque la última aparición del {number}? "
                    "Puedo revisarlo en una específica o compararlo entre todas las loterías disponibles."
                ),
                structured_type="lottery_ambiguity",
                params={"number": number, "pending_slots": ["lottery"]},
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_LAST_OCCURRENCE,
            params={"lottery": lottery, "number": number},
            structured_type="lottery_result",
        )

    # following days (incl. "días después" / "7 dias")
    if re.search(
        r"(dias|días)\s+(siguientes?|despu[eé]s)|siguientes?\s+\d*\s*(dias|días)|"
        r"despu[eé]s\s+(de\s+)?\d*\s*(dias|días)?|siete dias|7 dias|dias despu",
        text,
    ):
        if not lottery or not ctx_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito la lotería y la fecha base para los días siguientes.",
                structured_type="lottery_ambiguity",
            )
        days = _extract_int(text, "dias", "días", default=ctx.last_days or 7) or 7
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_FOLLOWING_DAYS,
            params={"lottery": lottery, "date": ctx_date, "days": days, "include_base_date": False},
            structured_type="lottery_range",
        )

    # following draws (incl. "los cinco sorteos siguientes" / "sorteos después")
    if re.search(
        r"sorteos?\s+(siguientes?|despu[eé]s)|siguientes?\s+\d*\s*sorteos|siete sorteos|7 sorteos|"
        r"(cinco|5|tres|3|diez|10)\s+sorteos?\s+(siguientes?|despu[eé]s)",
        text,
    ):
        if not lottery or not ctx_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito la lotería y la fecha base para los sorteos siguientes.",
                structured_type="lottery_ambiguity",
            )
        count = _extract_int(text, "sorteos", "sorteo", default=ctx.last_draw_count or 7) or 7
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_FOLLOWING_DRAWS,
            params={"lottery": lottery, "date": ctx_date, "count": count, "include_base_date": False},
            structured_type="lottery_range",
        )

    if re.search(r"siguientes?\s+(siete|7)\b", text) and "sorteo" not in text and "dia" not in text:
        if ctx.last_query_semantics == "next_n_draws" or (
            ctx.last_tool and "following_draws" in (ctx.last_tool or "")
        ):
            if not lottery or not ctx_date:
                return ResolvedIntent(
                    kind="clarify",
                    clarify_message="Necesito lotería y fecha base.",
                    structured_type="lottery_ambiguity",
                )
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_FOLLOWING_DRAWS,
                params={"lottery": lottery, "date": ctx_date, "count": 7},
                structured_type="lottery_range",
            )
        return ResolvedIntent(
            kind="clarify",
            clarify_message="¿Quieres siete días calendario o siete sorteos?",
            structured_type="lottery_ambiguity",
        )

    if re.search(r"(dias|días)\s+anteriores|anteriores?\s+\d*\s*(dias|días)", text):
        if not lottery or not ctx_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito lotería y fecha base para los días anteriores.",
                structured_type="lottery_ambiguity",
            )
        days = _extract_int(text, "dias", "días", default=7) or 7
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_PREVIOUS_DAYS,
            params={"lottery": lottery, "date": ctx_date, "days": days},
            structured_type="lottery_range",
        )

    if re.search(r"sorteos?\s+anteriores|anteriores?\s+\d*\s*sorteos", text):
        if not lottery or not ctx_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito lotería y fecha base para los sorteos anteriores.",
                structured_type="lottery_ambiguity",
            )
        count = _extract_int(text, "sorteos", "sorteo", default=7) or 7
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_PREVIOUS_DRAWS,
            params={"lottery": lottery, "date": ctx_date, "count": count},
            structured_type="lottery_range",
        )

    # repetitions in last N draws
    if re.search(r"repitieron|repeticion|repetición|se repiten|numeros repetidos", text):
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Sobre qué lotería quieres las repeticiones?",
                structured_type="lottery_ambiguity",
            )
        last_n = _extract_int(text, "sorteos", "sorteo", default=None)
        if last_n and re.search(r"[uú]ltimos?", text):
            from_d, to_d = _last_n_window(last_n)
        else:
            from_d = ctx.last_from_date
            to_d = ctx.last_to_date
            if not from_d or not to_d:
                if ctx_date and ctx.last_days:
                    from_d = ctx_date + timedelta(days=1)
                    to_d = ctx_date + timedelta(days=ctx.last_days)
                elif ctx_date:
                    from_d = ctx_date
                    to_d = ctx_date
                else:
                    from_d, to_d = _last_n_window(30)
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.FIND_REPETITIONS,
            params={"lottery": lottery, "from_date": from_d, "to_date": to_d, "min_count": 2},
            structured_type="lottery_repetitions",
        )

    # compare (multi-lottery + optional number)
    if re.search(
        r"tambien aparecieron|tambi[eé]n aparecieron|compar(a|ame|ar)|aparecieron en|"
        r"entre .+ y |de tres loter",
        text,
    ):
        lots = list(mentioned)
        if len(lots) < 2 and ctx.last_lottery and ctx.last_lottery not in lots:
            lots = [ctx.last_lottery, *lots]
        if len(lots) < 2 and ctx.compared_lotteries:
            lots = list(ctx.compared_lotteries)
        if re.search(r"tres loter", text) and len(lots) < 3:
            base = lots[0] if lots else (ctx.last_lottery or "Real")
            lots = [base]
            for name in DEFAULT_COMPARE_TRIPLE:
                if name not in lots:
                    lots.append(name)
                if len(lots) >= 3:
                    break
        if len(lots) < 2:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Indica al menos dos loterías para comparar.",
                structured_type="lottery_ambiguity",
            )

        number = _extract_number(raw)
        last_n = _extract_int(text, "sorteos", "sorteo", default=None)
        if number:
            # Comparación de un número: usar histórico amplio, no el rango del turno anterior.
            from_d, to_d = _last_n_window(3650)
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.COMPARE_LOTTERIES,
                params={
                    "lotteries": lots[:10],
                    "from_date": from_d,
                    "to_date": to_d,
                    "mode": "number_compare",
                    "number": number,
                },
                structured_type="lottery_comparison",
            )
        if last_n and re.search(r"[uú]ltimos?", text):
            from_d, to_d = _last_n_window(last_n)
        else:
            from_d = ctx.last_from_date or parsed_date
            to_d = ctx.last_to_date or parsed_date
            if not from_d or not to_d:
                from_d, to_d = _last_n_window(30)
        mode = "frequencies" if re.search(r"[uú]ltimos?\s+\d+\s+sorteos|tres loter", text) else "repeated_numbers"
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.COMPARE_LOTTERIES,
            params={
                "lotteries": lots[:10],
                "from_date": from_d,
                "to_date": to_d,
                "mode": mode,
                "include_draws": True,
            },
            structured_type="lottery_comparison",
        )

    if re.search(r"volvi[oó] a salir|proxima aparicion|pr[oó]xima aparici[oó]n|cuando (sali[oó]|apareci)", text):
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        if not lottery or not number or not ctx_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Necesito lotería, número y fecha base para la próxima aparición histórica.",
                structured_type="lottery_ambiguity",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.FIND_NEXT_OCCURRENCES,
            params={"lottery": lottery, "number": number, "after_date": ctx_date, "limit": 10},
            structured_type="lottery_next_occurrences",
        )

    if re.search(r"frecuencia|mas frecuentes|m[aá]s frecuentes|n[uú]meros?\s+m[aá]s\s+frecuentes", text):
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message=(
                    "¿Quieres analizarlos en alguna lotería específica o en todas? "
                    "También dime si prefieres los últimos 30 sorteos, el último año o todo el historial."
                ),
                structured_type="lottery_ambiguity",
                params={"pending_slots": ["lottery", "period"]},
            )
        from_d = ctx.last_from_date or parsed_date
        to_d = ctx.last_to_date or from_d
        if not from_d or not to_d:
            from_d, to_d = _last_n_window(365)
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.CALCULATE_FREQUENCIES,
            params={"lottery": lottery, "from_date": from_d, "to_date": to_d, "limit": 20},
            structured_type="lottery_frequency",
        )

    # by-date: salió / resultados (after more specific patterns)
    # Never treat "última vez que salió N" as by-date (handled above).
    if re.search(r"[uú]ltima\s+vez|cu[aá]ndo fue la [uú]ltima", text):
        pass
    elif re.search(r"sali[oó]|resultado|que salio|qu[eé] sali[oó]|mostrar.*fecha", text) or (
        lottery and parsed_date and re.search(r"\d{4}|\bde\b", text)
    ):
        if not lottery and not parsed_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="Indica la lotería y la fecha exacta (ej. Real el 15 de marzo de 2022).",
                structured_type="lottery_ambiguity",
            )
        if not lottery:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿De qué lotería quieres el resultado de esa fecha?",
                structured_type="lottery_ambiguity",
            )
        if not parsed_date:
            return ResolvedIntent(
                kind="clarify",
                clarify_message=f"¿Qué fecha exacta quieres consultar en {lottery}?",
                structured_type="lottery_ambiguity",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_RESULT_BY_DATE,
            params={"lottery": lottery, "date": parsed_date},
            structured_type="lottery_result",
        )

    if re.search(r"qu[eé] loter[ií]as|lista(r)? loter|cat[aá]logo", text):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.LIST_LOTTERIES,
            params={"limit": 50},
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
