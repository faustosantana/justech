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
    r"siguiente sorteo|pr[oó]ximo resultado|mañana saldr|garantiz\w*|"
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
    (r"gana\s*m[aá]s|ganamas", "Gana Más"),
    # Nacional: noche/día primero; "nacional" genérico al final (resolver afina).
    (r"nacional\s+noche|loter[ií]a\s+nacional\s+noche", "Nacional"),
    (r"nacional\s+d[ií]a|loter[ií]a\s+nacional\s+d[ií]a", "New York 2:30"),
    (r"loter[ií]a\s+nacional|\bnacional\b", "Nacional"),
    (r"new\s+york\s+10:?30|\bny\s+10:?30\b|new\s+york\s+noche|\bny\s+noche\b", "New York 10:30"),
    (r"new\s+york\s+2:?30|\bny\s+2:?30\b|new\s+york\s+d[ií]a|\bny\s+d[ií]a\b", "New York 2:30"),
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
    from app.lottery.ai.official_lottery_scope import canonicalize_lottery_name

    hits: list[tuple[int, str]] = []
    for pattern, name in LOTTERY_HINTS:
        for m in re.finditer(pattern, text, re.I):
            hits.append((m.start(), name))
    hits.sort(key=lambda x: x[0])
    out: list[str] = []
    for _, name in hits:
        canon = canonicalize_lottery_name(name)
        if canon and canon not in out:
            out.append(canon)
    return out


def _extract_non_official_lottery(text: str) -> str | None:
    """Detect explicit external lottery mentions for a clear rejection message."""
    from app.lottery.ai.official_lottery_scope import is_official_lottery

    for pattern, name in LOTTERY_HINTS:
        if is_official_lottery(name):
            continue
        if re.search(pattern, text or "", re.I):
            return name
    # Common external brands in the global catalog (not in LOTTERY_HINTS)
    external = [
        (r"\bhaiti\s*bolet\b|\bhait[ií]\b", "Haiti Bolet"),
        (r"\bking\s*lottery\b", "King Lottery"),
        (r"\banguila\b", "Anguila"),
        (r"\bcash\s*4\s*life|cash4life\b", "Cash4Life"),
        (r"\bflorida\b", "Florida"),
    ]
    for pattern, name in external:
        if re.search(pattern, text or "", re.I):
            return name
    return None


def _extract_number(text: str) -> str | None:
    # Avoid treating "últimos 30 sorteos" / "7 días" / "últimas 3 veces" as a ball number.
    cleaned = re.sub(
        r"[uú]ltimos?\s+\d+\s+(sorteos?|dias|días|veces|apariciones)|"
        r"[uú]ltimas?\s+\d+\s+(sorteos?|dias|días|veces|apariciones)|"
        r"\b\d+\s+(sorteos?|dias|días|veces|apariciones)\b|"
        r"\b\d+\s+anteriores?\b|"
        r"\b(anteriores?)\s+\d+\b|"
        r"\b\d+\s+sorteos?\b|\b\d+\s+dias\b|\b\d+\s+días\b",
        " ",
        text,
        flags=re.I,
    )
    m = re.search(r"(?:el|n[uú]mero|numero|del)\s+(\d{1,3})\b", cleaned, re.I)
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


def _extract_occurrence_limit_params(text: str) -> dict[str, Any] | None:
    """Extrae límite explícito 5/10/20/all. None = no especificado (pedir aclaración)."""
    if re.search(
        r"todas\s+(las\s+)?(ocurrencias|veces|apariciones)|"
        r"todo\s+el\s+hist[oó]rico|"
        r"todas\s+las\s+ocurrencias\s+disponibles|"
        r"all_occurrences|\bocurrence_mode\s*=\s*all\b",
        text,
        re.I,
    ):
        return {"occurrence_mode": "all"}
    m = re.search(
        r"[uú]ltimas?\s+(\d+)\s+(veces?|apariciones|ocurrencias)",
        text,
        re.I,
    )
    if m:
        return {"occurrence_mode": "last_k", "occurrence_k": int(m.group(1))}
    # «últimas 20» / «usando las últimas 10» sin la palabra veces (solo K UI 5|10|20)
    m = re.search(r"[uú]ltimas?\s+(\d+)\b", text, re.I)
    if m and int(m.group(1)) in {5, 10, 20}:
        return {"occurrence_mode": "last_k", "occurrence_k": int(m.group(1))}
    m = re.search(r"\blast[_\s-]?(\d+)\b", text, re.I)
    if m and int(m.group(1)) in {5, 10, 20}:
        return {"occurrence_mode": "last_k", "occurrence_k": int(m.group(1))}
    # Respuesta corta al clarifier: solo "5", "10", "20", "todas"
    t = text.strip().lower()
    if t in {"5", "10", "20"}:
        return {"occurrence_mode": "last_k", "occurrence_k": int(t)}
    if t in {"todas", "all", "todas las ocurrencias"}:
        return {"occurrence_mode": "all"}
    return None


def resolve_intent(message: str, ctx: LotterySessionContext) -> ResolvedIntent:
    raw = message.strip()
    text = _norm(raw)

    # Fase X — NLP stability gate (current message priority; no tools on greeting/chat)
    from app.lottery.ai.nlp_stability import (
        DEFAULT_ALL_HISTORY_LOTTERIES,
        classify_nlp,
    )

    has_ctx = bool(
        (ctx.last_numbers or [])
        or getattr(ctx, "current_primary_candidate", None)
        or (getattr(ctx, "last_analysis", None) or {})
        or ctx.last_lottery
    )
    nlp = classify_nlp(raw, has_active_context=has_ctx)
    if nlp.intent in {"GREETING", "GENERAL_CHAT", "HELP"} and not nlp.run_tools:
        return ResolvedIntent(
            kind="chat",
            clarify_message=nlp.conversational_reply,
            refuse_message=None,
            structured_type=nlp.intent.lower(),
            params={
                "nlp_intent": nlp.intent,
                "nlp": nlp.to_dict(),
                "decision_log": list(nlp.decision_log),
            },
        )

    # Official scope gate — reject explicit external lotteries before tooling
    from app.lottery.ai.official_lottery_scope import external_lottery_message

    external = _extract_non_official_lottery(raw)
    if external:
        return ResolvedIntent(
            kind="refuse",
            refuse_message=external_lottery_message(external),
            structured_type="out_of_scope_lottery",
            params={"rejected_lottery": external, "official_scope": True},
        )

    # Fase Final 2.4.0 — same-day continuity before form-biased branches
    from app.lottery.ai.same_day_coincidence import (
        build_same_day_follow_up_params,
        is_after_coincidences_follow_up,
        is_first_position_follow_up,
        is_last_coincidence_follow_up,
        is_lottery_only_follow_up,
        is_return_to_pair,
    )
    from app.lottery.ai.compound_occurrence import follow_up_any_position, follow_up_first_position

    if len(ctx.last_numbers or []) >= 2 and (
        is_lottery_only_follow_up(raw)
        or follow_up_any_position(raw)
        or follow_up_first_position(raw)
        or is_first_position_follow_up(raw)
        or is_last_coincidence_follow_up(raw)
        or is_after_coincidences_follow_up(raw)
        or is_return_to_pair(raw)
    ):
        params = build_same_day_follow_up_params(
            raw,
            active_numbers=list(ctx.last_numbers),
            active_lotteries=list(
                filter(
                    None,
                    [ctx.last_lottery, *(ctx.compared_lotteries or [])],
                )
            ),
            position_scope=getattr(ctx, "default_number_position_scope", None) or "any_position",
            preferred_position=int(getattr(ctx, "default_primary_position", None) or 1),
            last_coincidence_date=(
                str((ctx.last_analysis or {}).get("last_coincidence_date") or ctx.base_date or "")[:10]
                or None
            ),
        )
        if params:
            if params.get("after_coincidences"):
                return ResolvedIntent(
                    kind="tool",
                    tool=LotteryToolName.GET_FOLLOWING_DAYS,
                    params={
                        **params,
                        "count": 7,
                        "lottery": params.get("lottery")
                        or ctx.last_lottery
                        or (params.get("lotteries") or [None])[0],
                        "date": params.get("date")
                        or str((ctx.last_analysis or {}).get("last_coincidence_date") or ctx.base_date or "")[
                            :10
                        ]
                        or None,
                        "nlp_policy": "2.4.0",
                    },
                    structured_type="lottery_result",
                )
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_NUMBER_OCCURRENCES,
                params={**params, "nlp_policy": "2.4.0"},
                structured_type="lottery_same_day_coincidence",
            )

    # Fase X.1 — material-only clarifies / investigate defaults (before form-biased branches)
    _last_ask = bool(
        re.search(
            r"ultima|cu[aá]ndo\s+(fue\s+)?la\s+[uú]ltima|cual\s+fue\s+la\s+ultima|"
            r"la\s+ultima(\s+vez)?",
            text,
            re.I,
        )
    )
    if _last_ask and nlp.intent in {"DATE", "FOLLOW_UP", "UNKNOWN", "GENERAL_CHAT"}:
        # Fase X.2 — "última coincidencia" keeps compound same-day pair
        if re.search(r"coinciden", text, re.I) and (
            len(ctx.last_numbers or []) >= 2
            or len(nlp.entities.get("numbers") or []) >= 2
        ):
            nums = list(nlp.entities.get("numbers") or []) or list(ctx.last_numbers or [])
            nums = [str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n) for n in nums][:8]
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_NUMBER_OCCURRENCES,
                params={
                    "numbers": nums,
                    "relation": "same_day",
                    "active_relation": "same_day",
                    "position_scope": "any_position",
                    "position": None,
                    "preferred_position": 1,
                    "want_last_only": True,
                    "all_historical": True,
                    "intent": "same_day_coincidence",
                    "nlp_intent": "DATE",
                    "nlp_policy": "2.3.3",
                },
                structured_type="lottery_same_day_coincidence",
            )
        number = (nlp.entities.get("numbers") or [None])[0] or (
            ctx.last_numbers[0] if ctx.last_numbers else None
        )
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿La última vez de cuál número?",
                structured_type="lottery_ambiguity",
                params={"pending_slots": ["number"], "nlp_intent": "DATE", "nlp_policy": "2.3.2"},
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.COMPARE_LOTTERIES,
            params={
                "number": number,
                "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                "mode": "number_compare",
                "all_historical": True,
                "nlp_intent": "DATE",
                "nlp_policy": "2.3.2",
            },
            structured_type="lottery_comparison",
        )

    if nlp.intent == "COMPARE" or re.search(r"compara(lo|la|me|r)?\s+con", text, re.I):
        nums = list(nlp.entities.get("numbers") or [])
        if not nums:
            m = re.search(r"\b(\d{1,2})\b", raw)
            if m:
                nums = [m.group(1).zfill(2)]
        if len(nums) >= 1 and (ctx.last_numbers or len(nums) >= 2):
            a = ctx.last_numbers[0] if ctx.last_numbers and len(nums) == 1 else nums[0]
            b = nums[-1]
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.COMPARE_LOTTERIES,
                params={
                    "number": a,
                    "compare_with": b,
                    "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                    "mode": "number_compare",
                    "all_historical": True,
                    "nlp_intent": "COMPARE",
                    "nlp_policy": "2.3.2",
                },
                structured_type="lottery_comparison",
            )

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

    # Analizador histórico T1↔T2 (ciclos, combinaciones, tasas) — antes del analyze NR actual.
    _hist_signals = bool(
        re.search(
            r"ciclo\s+(promedio|medio|observado)|"
            r"tasa\s+hist[oó]rica|"
            r"respuesta\s+(hist[oó]rica|posterior)|"
            r"combinaci[oó]n(es)?\s+de\s+confirm|"
            r"confirmador(es)?|"
            r"fortalec(i[oó]|i[oó]n).{0,40}\d+|"
            r"cu[aá]ntas\s+veces.{0,60}fortalec|"
            r"desde\s+20\d{2}|"
            r"en\s+20\d{2}.{0,40}candidato|"
            r"patr[oó]n\s+hist[oó]rico|"
            r"matriz\s+de\s+combin|"
            r"compara(r)?\s+(leidsa|loteka|candidatos|patrones)",
            text,
            re.I,
        )
    )
    if _hist_signals:
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        lotteries = _extract_lotteries(text) or ([ctx.last_lottery] if ctx.last_lottery else [])
        lotteries = [x for x in lotteries if x]
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Qué número observado N (1..100) analizo en el histórico de relaciones?",
                structured_type="lottery_ambiguity",
            )
        if not lotteries:
            return ResolvedIntent(
                kind="clarify",
                clarify_message=(
                    f"¿En cuál lotería principal analizo el histórico del {number}? "
                    "Follow-up por defecto = misma principal."
                ),
                structured_type="lottery_ambiguity",
            )
        n_int = int(str(number).lstrip("0") or "0")
        year_m = re.search(r"\b(20\d{2})\b", text)
        params_h: dict[str, Any] = {
            "observed_number": n_int,
            "lotteries": lotteries,
            "lottery": lotteries[0],
            "primary_lotteries": lotteries[:1],
            "confirming_lotteries": lotteries,
            "confirmation_window_mode": "SAME_DRAW",
        }
        if year_m:
            params_h["year"] = int(year_m.group(1))
        cand_m = re.search(r"candidato\s+(\d{1,3})", text, re.I)
        conf_m = re.search(r"confirmador\s+(\d{1,3})", text, re.I)
        if cand_m:
            params_h["candidate"] = int(cand_m.group(1))
        if conf_m:
            params_h["confirmer"] = int(conf_m.group(1))

        if re.search(r"combinaci|pares|tr[ií]os", text, re.I):
            tool_h = LotteryToolName.CONFIRMER_COMBINATIONS
            st = "lottery_nr_combinations"
        elif re.search(r"ciclo|tasa|respuesta\s+posterior|m[aá]s\s+r[aá]pido", text, re.I):
            tool_h = LotteryToolName.CANDIDATE_RESPONSE_SUMMARY
            st = "lottery_nr_posterior"
        elif re.search(r"compara", text, re.I):
            tool_h = LotteryToolName.COMPARE_HISTORICAL_PATTERNS
            st = "lottery_nr_compare"
        elif re.search(r"detalle|patr[oó]n|cu[aá]ntas\s+veces", text, re.I):
            tool_h = LotteryToolName.RELATION_PATTERN_DETAIL
            st = "lottery_nr_pattern"
        else:
            tool_h = LotteryToolName.HISTORICAL_RELATION_CONDITIONS
            st = "lottery_nr_historical_conditions"
        return ResolvedIntent(
            kind="tool",
            tool=tool_h,
            params=params_h,
            structured_type=st,
        )

    # Follow-ups over complete-analysis memory (no re-ask when context exists).
    # Fase X: current-message COUNT/ANALYZE with explicit number never inherits memory.
    _skip_memory_hijack = bool(
        (nlp.intent == "COUNT" and (nlp.entities.get("numbers") or []))
        or (nlp.intent == "ANALYZE" and (nlp.entities.get("numbers") or []))
    )
    store = ctx.to_store() if hasattr(ctx, "to_store") else {}
    last_ca = dict(getattr(ctx, "last_analysis", None) or {})
    if not last_ca and isinstance(store, dict):
        v4 = store.get("conversation_v4") if isinstance(store.get("conversation_v4"), dict) else {}
        last_ca = dict(v4.get("last_analysis") or {})
    primary_cand = None
    try:
        primary_cand = int(
            (last_ca or {}).get("primary")
            or getattr(ctx, "current_primary_candidate", None)
            or 0
        ) or None
    except (TypeError, ValueError):
        primary_cand = None
    observed_mem = None
    try:
        observed_mem = int(
            (last_ca or {}).get("observed")
            or (ctx.last_numbers[0] if ctx.last_numbers else 0)
        ) or None
    except (TypeError, ValueError, IndexError):
        observed_mem = None

    if (not _skip_memory_hijack) and primary_cand and re.search(
        r"por\s*qu[eé]\s+no|porqu[eé]\s+no|y\s+no\s+el|frente\s+al?|compar(a|alo|arlo)\s+con",
        text,
        re.I,
    ):
        rival = _extract_number(raw)
        if rival or primary_cand:
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.RUN_COMPLETE_ANALYSIS,
                params={
                    "observed_number": observed_mem or primary_cand,
                    "number": str(observed_mem or primary_cand),
                    "confirmer": (last_ca or {}).get("confirmer"),
                    "date": (last_ca or {}).get("date") or store.get("base_date"),
                    "lottery": (last_ca or {}).get("lottery") or ctx.last_lottery,
                    "compare_with": int(rival) if rival else 7,
                    "include_historical": True,
                    "follow_up": "compare_rival",
                },
                structured_type="lottery_complete_analysis",
            )

    if (not _skip_memory_hijack) and (primary_cand or observed_mem) and re.search(
        r"hist[oó]rico|casos\s+equivalentes|cu[aá]ntas\s+veces|d\+7|d\+3|d\+1|"
        r"comport[oó]|evidencia\s+hist|últimos\s+casos|ultimos\s+casos",
        text,
        re.I,
    ):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.RUN_COMPLETE_ANALYSIS,
            params={
                "observed_number": observed_mem or primary_cand,
                "number": str(observed_mem or primary_cand),
                "confirmer": (last_ca or {}).get("confirmer"),
                "date": (last_ca or {}).get("date") or store.get("base_date"),
                "lottery": (last_ca or {}).get("lottery") or ctx.last_lottery,
                "include_historical": True,
                "follow_up": "historical",
            },
            structured_type="lottery_complete_analysis",
        )

    if (not _skip_memory_hijack) and (primary_cand or observed_mem) and re.search(
        r"m[aá]s\s+sencillo|expl[ií]ca(me)?\s+(eso|eso\s+m[aá]s)|"
        r"en\s+simple|res[uú]me(lo|me)|cu[aá]l\s+fue\s+el\s+resultado|"
        r"por\s*qu[eé]\s+el\s+\d+|explicar\s+tabla\s*1|explicar\s+tabla\s*2",
        text,
        re.I,
    ):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.RUN_COMPLETE_ANALYSIS,
            params={
                "observed_number": observed_mem or primary_cand,
                "number": str(observed_mem or primary_cand),
                "confirmer": (last_ca or {}).get("confirmer"),
                "date": (last_ca or {}).get("date") or store.get("base_date"),
                "lottery": (last_ca or {}).get("lottery") or ctx.last_lottery,
                "include_historical": True,
                "follow_up": "explain_simple",
            },
            structured_type="lottery_complete_analysis",
        )

    # Motor de Relaciones Numéricas / Análisis completo.
    # "Analiza el N" → análisis completo (Tabla 1/2 + mismo día + histórico).
    # Solo exige occurrence_limit cuando el usuario pide explícitamente ocurrencias/veces.
    _nr_occurrence_mode = bool(
        re.search(
            r"([uú]ltimas?\s+\d+\s+veces?)|"
            r"(todas\s+(las\s+)?(ocurrencias|veces|apariciones))|"
            r"(veces?\s+que\s+sali)|"
            r"(muestr(a|ame)\s+todas\s+las\s+ocurrencias)",
            text,
            re.I,
        )
    )
    _nr_signals = bool(
        re.search(
            r"compa[nñ]eros?|"
            r"vecinos?|"
            r"fortalec|"
            r"relaciones?\s+num[eé]ricas?|"
            r"c[oó]digo\s+madre|"
            r"motor\s+de\s+relaciones|"
            r"predicci[oó]n\s+(del?\s+)?\d+|"
            r"predice\s+(los\s+)?(compa|n[uú]meros?)|"
            r"n[uú]meros?\s+m[aá]s\s+fuertes|"
            r"despu[eé]s\s+de\s+salir\s+(el\s+)?\d+|"
            r"cuando\s+sale\s+el\s+\d+",
            text,
            re.I,
        )
    )
    _analiza_observed = bool(
        re.search(
            r"analiz(a|ar|ame|emos)(\s+\w+){0,4}\s+(el\s+)?\d{1,2}|"
            r"analiz(a|ar)\s+el\s+n[uú]mero|"
            r"analiz(a|ar|ame)\s+ese\s+n[uú]mero|"
            r"haz(me)?\s+un\s+(estudio|an[aá]lisis)(\s+completo)?\s+(del?\s+)?\d{1,2}|"
            r"estudia(r)?\s+(el\s+)?\d{1,2}|"
            r"investiga(r)?\s+(el\s+)?(grupo\s+(del\s+)?)?\d{1,2}",
            text,
            re.I,
        )
    ) or (nlp.intent == "ANALYZE" and bool(nlp.entities.get("numbers")))
    if not (_nr_signals or _analiza_observed) and (
        PREDICTION_RE.search(raw) or PREDICTION_RE.search(text)
    ):
        return ResolvedIntent(
            kind="prediction_refused",
            refuse_message=(
                "No puedo predecir resultados futuros ni recomendar apuestas. "
                "Solo consulto el histórico verificado. "
                "Puedes pedir una señal histórica del Motor de Relaciones Numéricas "
                "(ej. «predicción del 34 en Leidsa con las últimas 20»). "
                "Eso no anticipa resultados futuros."
            ),
            structured_type="lottery_error",
        )

    if _nr_signals or _analiza_observed:
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        # "ese número" → memoria
        if not number and re.search(r"ese\s+n[uú]mero|el\s+mismo", text, re.I):
            number = ctx.last_numbers[0] if ctx.last_numbers else None
        lotteries = _extract_lotteries(text)
        if re.search(
            r"todas\s+las\s+loter[ií]as(\s+seleccionadas)?|"
            r"todas\s+las\s+seleccionadas",
            text,
            re.I,
        ):
            session_lots = list(ctx.compared_lotteries or [])
            if ctx.last_lottery and ctx.last_lottery not in session_lots:
                session_lots = [ctx.last_lottery, *session_lots]
            if session_lots:
                lotteries = session_lots
        if not lotteries and ctx.last_lottery:
            lotteries = [ctx.last_lottery]
        if ctx.compared_lotteries:
            for x in ctx.compared_lotteries:
                if x not in lotteries:
                    lotteries.append(x)
        limit_params = _extract_occurrence_limit_params(text)
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Qué número quieres que analice?",
                structured_type="lottery_ambiguity",
                params={"pending_slots": ["number"]},
            )
        try:
            n_int = int(str(number).lstrip("0") or "0")
        except ValueError:
            n_int = 0
        if n_int < 1 or n_int > 100:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="El número debe estar entre 1 y 100.",
                structured_type="lottery_ambiguity",
                params={"pending_slots": ["number"]},
            )
        # Confirmador opcional: "con 14" / segundo número
        confirmer = None
        m_con = re.search(r"\bcon\s+(el\s+)?(\d{1,3})\b", text, re.I)
        if m_con:
            try:
                confirmer = int(m_con.group(2))
            except ValueError:
                confirmer = None
        nums_all = re.findall(r"\b(\d{1,3})\b", text)
        if confirmer is None and len(nums_all) >= 2:
            try:
                a, b = int(nums_all[0]), int(nums_all[1])
                if a == n_int and 1 <= b <= 100:
                    confirmer = b
            except ValueError:
                pass
        # Fecha: reutilizar solo si el usuario habla del mismo número/contexto.
        # Un cambio de número (p. ej. 35 → 39) debe re-resolver la fecha.
        date_s = None
        same_observed = False
        try:
            prev_obs = int((last_ca or {}).get("observed") or 0) or None
            same_observed = prev_obs is not None and int(prev_obs) == int(n_int)
        except (TypeError, ValueError):
            same_observed = False
        if same_observed:
            date_s = (last_ca or {}).get("date") or (
                store.get("base_date") if isinstance(store, dict) else None
            )
            if hasattr(ctx, "base_date") and ctx.base_date:
                date_s = date_s or ctx.base_date
        # Explicit date in message wins
        m_date = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        if m_date:
            date_s = m_date.group(1)
        elif re.search(r"23\s+de\s+junio|23\s*/\s*06|junio\s+23", text, re.I):
            date_s = "2026-06-23"

        # Análisis completo por defecto (conversacional) — sin preguntar lotería/K.
        if _analiza_observed and not _nr_occurrence_mode:
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.RUN_COMPLETE_ANALYSIS,
                params={
                    "observed_number": n_int,
                    "number": str(n_int),
                    "confirmer": confirmer,
                    "date": date_s,
                    "lottery": (
                        ((last_ca or {}).get("lottery") or (lotteries[0] if lotteries else ctx.last_lottery))
                        if same_observed
                        else (lotteries[0] if lotteries else None)
                    ),
                    "include_historical": True,
                    "historical_period": "all",
                },
                structured_type="lottery_complete_analysis",
            )

        # Modo ocurrencias NR: defaults sensatos (10 + lotería de contexto o featured).
        if not lotteries:
            lotteries = [ctx.last_lottery] if ctx.last_lottery else []
        if not limit_params:
            limit_params = {"occurrence_limit_mode": "last_k", "occurrence_limit_k": 10}
        if not lotteries:
            # Sin lotería: usar análisis completo en vez de wizard.
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.RUN_COMPLETE_ANALYSIS,
                params={
                    "observed_number": n_int,
                    "number": str(n_int),
                    "confirmer": confirmer,
                    "date": date_s,
                    "include_historical": True,
                },
                structured_type="lottery_complete_analysis",
            )
        params: dict[str, Any] = {
            "observed_number": n_int,
            "number": str(n_int),
            "lotteries": lotteries,
            **limit_params,
        }
        if len(lotteries) == 1:
            params["lottery"] = lotteries[0]
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.ANALYZE_NUMERIC_RELATIONS,
            params=params,
            structured_type="lottery_numeric_relations",
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

    # "analiza el N" genérico ya se enruta al Motor NR arriba.
    # Lottery-summary ONLY when asking about a lottery (not a number analysis).
    if re.search(
        r"(analiz(a|ar).*(completa|completa(mente)?|resumen)|"
        r"haz(me)?\s+un\s+an[aá]lisis|dame\s+lo\s+m[aá]s\s+importante|"
        r"analiz(a|ala)\s+(la\s+)?(real|leidsa|loteka|nacional))"
        r"(?!.*\b\d{1,2}\b)",
        text,
    ) and not _analiza_observed and nlp.intent != "ANALYZE":
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

    # Fase X — COUNT with explicit number BEFORE last-occurrence compound (avoids false lottery clarify)
    if nlp.intent == "COUNT" or re.search(
        r"cu[aá]ntas?\s+veces|cuantas?\s+veces|cu[aá]ntas?\s+apariciones", text
    ):
        from app.lottery.ai.compound_occurrence import resolve_effective_position as _rep

        number = _extract_number(raw)
        if not number and nlp.entities.get("numbers"):
            number = str(nlp.entities["numbers"][0])
        if not number and nlp.inherit_context and ctx.last_numbers:
            number = ctx.last_numbers[0]
        pos_filter, scope_used, needs_ask = _rep(
            raw,
            pref_scope=getattr(ctx, "default_number_position_scope", None),
            pref_primary=int(getattr(ctx, "default_primary_position", None) or 1),
        )
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Qué número quieres contar?",
                structured_type="lottery_ambiguity",
                params={"pending_slots": ["number"], "nlp_intent": "COUNT"},
            )
        # Fase X.1 — never ask position; default any when ambiguous
        if needs_ask:
            pos_filter, scope_used = None, "any_position"
        lot = _extract_lottery(text)
        if lot:
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_NUMBER_OCCURRENCES,
                params={
                    "lottery": lot,
                    "number": number,
                    "page": 1,
                    "page_size": 50,
                    "position": pos_filter,
                    "position_scope": scope_used,
                    "nlp_intent": "COUNT",
                },
                structured_type="lottery_result",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.COMPARE_LOTTERIES,
            params={
                "number": number,
                "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                "position": pos_filter,
                "position_scope": scope_used,
                "mode": "number_compare",
                "all_historical": True,
                "nlp_intent": "COUNT",
            },
            structured_type="lottery_comparison",
        )

    # --- P1: compound / last-occurrence with default first position ---
    from app.lottery.ai.compound_occurrence import (
        DEFAULT_PRIMARY_POSITION,
        DEFAULT_POSITION_SCOPE,
        is_last_occurrence_question,
        parse_compound_last_occurrence,
        resolve_effective_position,
    )
    from app.lottery.ai.same_day_coincidence import (
        is_first_position_follow_up,
        is_last_coincidence_follow_up,
        is_same_day_coincidence_question,
        parse_same_day_coincidence,
    )
    from app.lottery.ai.compound_occurrence import follow_up_any_position

    pref_scope = getattr(ctx, "default_number_position_scope", None) or DEFAULT_POSITION_SCOPE
    pref_primary = int(getattr(ctx, "default_primary_position", None) or DEFAULT_PRIMARY_POSITION)

    # Fase X.2 — same-day coincidence BEFORE multi last-occurrence
    active_nums = list(ctx.last_numbers or [])
    same_day = None
    if is_same_day_coincidence_question(raw) or (
        (is_last_coincidence_follow_up(raw) or is_first_position_follow_up(raw) or follow_up_any_position(raw))
        and len(active_nums) >= 2
    ):
        same_day = parse_same_day_coincidence(
            raw, active_numbers=active_nums, pref_scope="any_position"
        )
        if same_day is None and len(active_nums) >= 2 and (
            is_last_coincidence_follow_up(raw)
            or is_first_position_follow_up(raw)
            or follow_up_any_position(raw)
        ):
            same_day = {
                "intent": "same_day_coincidence",
                "active_numbers": active_nums[:8],
                "numbers": active_nums[:8],
                "active_relation": "same_day",
                "position_scope": "any_position",
                "position": None,
                "preferred_position": 1,
                "want_last_only": is_last_coincidence_follow_up(raw),
                "report_mode": False,
                "relation": "same_day",
            }
            if is_first_position_follow_up(raw):
                same_day["position"] = 1
                same_day["position_scope"] = "first_position"
            elif follow_up_any_position(raw):
                same_day["position"] = None
                same_day["position_scope"] = "any_position"
    if same_day and same_day.get("numbers"):
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_NUMBER_OCCURRENCES,
            params={
                "numbers": list(same_day["numbers"]),
                "relation": "same_day",
                "active_relation": "same_day",
                "position_scope": same_day.get("position_scope") or "any_position",
                "position": same_day.get("position"),
                "preferred_position": int(same_day.get("preferred_position") or 1),
                "want_last_only": bool(same_day.get("want_last_only")),
                "report_mode": bool(same_day.get("report_mode")),
                "all_historical": True,
                "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                "intent": "same_day_coincidence",
                "nlp_policy": "2.3.3",
            },
            structured_type="lottery_same_day_coincidence",
        )

    compound = parse_compound_last_occurrence(
        raw, pref_scope=pref_scope, pref_primary=pref_primary
    )
    if compound and compound.get("queries"):
        if compound.get("needs_clarification"):
            # Fase X.1 — never block on position; continue with any_position
            compound["needs_clarification"] = False
            compound["position_scope"] = compound.get("position_scope") or "any_position"
            for q in compound.get("queries") or []:
                q["position_scope"] = q.get("position_scope") or "any_position"
                q["position"] = q.get("position")
        if compound.get("intent") == "multi_last_occurrence" and len(compound["queries"]) >= 2:
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_LAST_OCCURRENCE,
                params={
                    "multi_queries": compound["queries"],
                    "intent": "multi_last_occurrence",
                    "position_scope": compound.get("position_scope"),
                },
                structured_type="lottery_comparison",
            )
        if compound.get("intent") == "last_occurrence" and compound["queries"]:
            q0 = compound["queries"][0]
            lots = list(q0.get("lotteries") or [])
            if q0.get("lotteries_scope") in {"defaults_or_clarify", "all"} and not lots:
                # Fase X.1 — investigate all history; never ask lottery
                return ResolvedIntent(
                    kind="tool",
                    tool=LotteryToolName.COMPARE_LOTTERIES,
                    params={
                        "number": q0.get("number"),
                        "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                        "position": q0.get("position"),
                        "position_scope": q0.get("position_scope") or "any_position",
                        "mode": "number_compare",
                        "all_historical": True,
                        "nlp_policy": "2.3.2",
                    },
                    structured_type="lottery_comparison",
                )
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_LAST_OCCURRENCE,
                params={
                    "lottery": lots[0] if lots else lottery,
                    "number": q0.get("number"),
                    "position": q0.get("position"),
                    "position_scope": q0.get("position_scope"),
                },
                structured_type="lottery_result",
            )

    if is_last_occurrence_question(raw):
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        pos_filter, scope_used, needs_ask = resolve_effective_position(
            raw, pref_scope=pref_scope, pref_primary=pref_primary
        )
        # Fase X.1 — never block on position; default any
        if needs_ask:
            pos_filter, scope_used = None, "any_position"
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿La última vez de cuál número?",
                structured_type="lottery_ambiguity",
                params={"pending_slots": ["number"]},
            )
        if not lottery:
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.COMPARE_LOTTERIES,
                params={
                    "number": number,
                    "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                    "position": pos_filter,
                    "position_scope": scope_used or "any_position",
                    "mode": "number_compare",
                    "all_historical": True,
                    "nlp_policy": "2.3.2",
                },
                structured_type="lottery_comparison",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_LAST_OCCURRENCE,
            params={
                "lottery": lottery,
                "number": number,
                "position": pos_filter,
                "position_scope": scope_used,
            },
            structured_type="lottery_result",
        )

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

    # count occurrences: "cuántas veces salió el 01" — default first position
    # Fase X: with number present, use full historical scope (no lottery/date clarify).
    if re.search(r"cu[aá]ntas?\s+veces|cuantas?\s+veces|cu[aá]ntas?\s+apariciones", text):
        from app.lottery.ai.compound_occurrence import resolve_effective_position

        number = _extract_number(raw) or (
            None if nlp.intent == "COUNT" and nlp.entities.get("numbers")
            else (ctx.last_numbers[0] if ctx.last_numbers and nlp.inherit_context else None)
        )
        if not number and nlp.entities.get("numbers"):
            number = str(nlp.entities["numbers"][0])
        pos_filter, scope_used, needs_ask = resolve_effective_position(
            raw,
            pref_scope=getattr(ctx, "default_number_position_scope", None),
            pref_primary=int(getattr(ctx, "default_primary_position", None) or 1),
        )
        if needs_ask and not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Cuento apariciones en primera posición o en cualquier posición?",
                structured_type="lottery_ambiguity",
                params={"number": number, "pending_slots": ["position_scope"]},
            )
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿Qué número quieres contar?",
                structured_type="lottery_ambiguity",
                params={"pending_slots": ["number"], "nlp_intent": "COUNT"},
            )
        lottery = _extract_lottery(text) or (
            ctx.last_lottery if nlp.inherit_context and not nlp.entities.get("numbers") else None
        )
        if lottery:
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.GET_NUMBER_OCCURRENCES,
                params={
                    "lottery": lottery,
                    "number": number,
                    "page": 1,
                    "page_size": 50,
                    "position": pos_filter,
                    "position_scope": scope_used,
                    "nlp_intent": "COUNT",
                },
                structured_type="lottery_result",
            )
        # Full history across featured lotteries — never ask lottery/date
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.COMPARE_LOTTERIES,
            params={
                "number": number,
                "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                "position": pos_filter,
                "position_scope": scope_used,
                "mode": "number_compare",
                "all_historical": True,
                "nlp_intent": "COUNT",
            },
            structured_type="lottery_comparison",
        )

    # last occurrence (legacy explicit phrases — also covered earlier)
    if re.search(
        r"[uú]ltima\s+vez|cuando fue la ultima|cu[aá]ndo fue la [uú]ltima|"
        r"cu[aá]ndo\s+(fue\s+)?la\s+[uú]ltima\s+vez|hace\s+cu[aá]nto.*(sali[oó]|apareci)",
        text,
    ):
        number = _extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)
        if not number:
            return ResolvedIntent(
                kind="clarify",
                clarify_message="¿La última vez de cuál número?",
                structured_type="lottery_ambiguity",
                params={"pending_slots": ["number"]},
            )
        if not lottery:
            return ResolvedIntent(
                kind="tool",
                tool=LotteryToolName.COMPARE_LOTTERIES,
                params={
                    "number": number,
                    "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                    "mode": "number_compare",
                    "all_historical": True,
                    "nlp_policy": "2.3.2",
                },
                structured_type="lottery_comparison",
            )
        return ResolvedIntent(
            kind="tool",
            tool=LotteryToolName.GET_LAST_OCCURRENCE,
            params={"lottery": lottery, "number": number, "position": 1, "position_scope": "first_position"},
            structured_type="lottery_result",
        )

    # following days (incl. "días después" / "7 dias")
    if re.search(
        r"(dias|días)\s+(siguientes?|despu[eé]s)|siguientes?\s+\d*\s*(dias|días)|"
        r"despu[eé]s\s+(de\s+)?\d*\s*(dias|días)?|siete dias|7 dias|dias despu",
        text,
    ):
        if not lottery or not ctx_date:
            # Fase X.1 — if we have date context or active number, don't demand both
            if ctx_date and (lottery or ctx.last_lottery):
                lottery = lottery or ctx.last_lottery
            elif number := (_extract_number(raw) or (ctx.last_numbers[0] if ctx.last_numbers else None)):
                return ResolvedIntent(
                    kind="tool",
                    tool=LotteryToolName.COMPARE_LOTTERIES,
                    params={
                        "number": number,
                        "lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES),
                        "mode": "number_compare",
                        "all_historical": True,
                        "follow_up": "after",
                        "nlp_policy": "2.3.2",
                    },
                    structured_type="lottery_comparison",
                )
            else:
                return ResolvedIntent(
                    kind="clarify",
                    clarify_message="¿Después de cuál número o fecha base?",
                    structured_type="lottery_ambiguity",
                    params={"pending_slots": ["number"]},
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
                    "position": 1,
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

    # Next historical occurrence AFTER a known base date — not "cuándo salió"
    if re.search(
        r"volvi[oó] a salir|proxima aparicion|pr[oó]xima aparici[oó]n|"
        r"cuando\s+(volvi[oó]|apareci[oó])\s+(despu[eé]s|luego)",
        text,
    ):
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
            params={"lottery": lottery, "from_date": from_d, "to_date": to_d, "limit": 20, "position": 1},
            structured_type="lottery_frequency",
        )

    # by-date: salió / resultados (after more specific patterns)
    if re.search(r"[uú]ltima\s+vez|cu[aá]ndo fue la [uú]ltima|cu[aá]ndo\s+sali[oó]", text):
        pass
    elif re.search(r"resultado|que salio|qu[eé] sali[oó]|mostrar.*fecha", text) or (
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
            "Puedo investigar históricos, conteos, últimas apariciones, "
            "comparaciones y análisis completos. ¿Qué te gustaría investigar?"
        ),
        structured_type="lottery_ambiguity",
        params={"pending_slots": ["query"], "nlp_policy": "2.3.2"},
    )
