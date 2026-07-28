"""Reasoning modes — Hermes selects; Huawei analyzes under that mode."""

from __future__ import annotations

import re
from typing import Any, Literal

ReasoningMode = Literal[
    "factual_answer",
    "explain_evidence",
    "compare",
    "interpret_pattern",
    "summarize_investigation",
    "clarify_limitation",
    "skip",  # do not call Huawei
]

_EXPLAIN = re.compile(
    r"("
    r"explic|expl[ií]c|"
    r"por\s+qu[eé]|qu[eé]\s+significa|qu[eé]\s+observas|"
    r"analiza|an[aá]lisis|interpreta|tendencia|patr[oó]n|"
    r"dame\s+contexto|en\s+profundidad|m[aá]s\s+detalle|"
    r"por\s+qu[eé]\s+dices|diferencia\s+entre\s+misma|"
    r"alcance\s+de\s+las?\s+7"
    r")",
    re.I,
)
_COMPARE = re.compile(
    r"\b(compara|comparaci[oó]n|versus|\bvs\b|cu[aá]l\s+sali[oó]\s+m[aá]s|"
    r"m[aá]s\s+recientemente\s+entre)\b",
    re.I,
)
_SUMMARIZE = re.compile(
    r"\b("
    r"resume|resumen|recapitula|qu[eé]\s+hemos\s+visto|"
    r"estado\s+de\s+la\s+investigaci[oó]n|"
    r"resume\s+(esta\s+)?(investigaci[oó]n|sesi[oó]n)|"
    r"lo\s+que\s+vimos|10\s+minutos"
    r")\b",
    re.I,
)
_LIMIT = re.compile(
    r"\b("
    r"predicci[oó]n|predic[ae]|va\s+a\s+salir|seguro\s+que|garantiz|"
    r"pr[oó]ximo\s+sorteo|mañana\s+sale|inventa|supón\s+que|"
    r"haiti|king\s+lottery|anguila"
    r")\b",
    re.I,
)
_PURE_FACT = re.compile(
    r"^\s*[¿¡]?\s*("
    r"cu[aá]ntas?\s+veces|"
    r"cu[aá]ndo(\s+fue|\s+sali[oó])?|"
    r"[uú]ltima(\s+vez)?|"
    r"en\s+qu[eé]\s+(posici[oó]n|loter[ií]a)|"
    r"cu[aá]les?\s+(fueron\s+)?(esas\s+)?(fechas|loter[ií]as|posiciones)|"
    r"las?\s+(tres|3|últimas|anteriores)\b"
    r").*$",
    re.I,
)


class ReasoningModeSelector:
    """Hermes-side mode selection (deterministic)."""

    @classmethod
    def select(
        cls,
        message: str,
        *,
        hermes_decision: Any = None,
        relation: str | None = None,
        has_evidence: bool = True,
    ) -> ReasoningMode:
        raw = message or ""
        turn = getattr(hermes_decision, "turn_type", None) if hermes_decision else None
        attr = getattr(hermes_decision, "requested_attribute", None) if hermes_decision else None

        if _LIMIT.search(raw):
            return "clarify_limitation"

        if not has_evidence:
            return "clarify_limitation"

        # Explain verbs beat compare/same-day defaults
        if _EXPLAIN.search(raw) or attr in {"explain", "details"}:
            return "explain_evidence"

        if _SUMMARIZE.search(raw) or (
            turn == "meta" and re.search(r"resume|resumen", raw, re.I)
        ):
            return "summarize_investigation"

        if _COMPARE.search(raw) or (relation in {"compare", "comparison"} and _COMPARE.search(raw)):
            return "compare"

        if relation in {"compare", "comparison"} and re.search(
            r"compara|versus|\bvs\b|frecuencia", raw, re.I
        ):
            return "compare"

        # Pure attribute / date / position follow-ups → skip Huawei
        if attr in {"lotteries", "positions", "date", "count", "order"}:
            return "skip"

        if turn == "attribute_of_last_event" and not _EXPLAIN.search(raw):
            return "skip"

        # Bare count/date/position asks → skip Huawei (no interpretive value),
        # except same_day coincidence where "misma fecha ≠ misma lotería" needs analysis.
        if (
            _PURE_FACT.match(raw.strip())
            and not _EXPLAIN.search(raw)
            and relation != "same_day"
        ):
            return "skip"

        # Same-day coincidence: interpret (value over bare rewrite)
        if relation == "same_day" and not attr:
            if len(raw.strip()) >= 20 or _EXPLAIN.search(raw):
                return "interpret_pattern"

        if turn in {"new_investigation", "contextual_follow_up"} and (
            _EXPLAIN.search(raw) or len(raw.strip()) > 80
        ):
            return "interpret_pattern"

        return "skip"


def should_invoke_reasoning(mode: ReasoningMode | None) -> bool:
    return mode is not None and mode not in {"skip", "factual_answer"}


MODE_INSTRUCTIONS: dict[str, str] = {
    "explain_evidence": (
        "Explica por qué la respuesta factual es correcta usando solo el Evidence Package. "
        "Aclara significado de relation/scope. Incluye limitaciones y un siguiente análisis útil."
    ),
    "compare": (
        "Compara los subjects usando comparison_data y counts. Señala diferencias observables. "
        "No inventes frecuencias. Incluye limitaciones."
    ),
    "interpret_pattern": (
        "Interpreta patrones observables en dates/occurrences/positions. "
        "Distingue misma fecha vs misma lotería si relation=same_day. "
        "Sé descriptivo, no predictivo. Propón un siguiente análisis útil."
    ),
    "summarize_investigation": (
        "Resume la investigación con known_facts, counts y dates. "
        "No agregues hechos nuevos. Señala limitaciones."
    ),
    "clarify_limitation": (
        "Aclara limitaciones o rechaza con cortesía predicciones garantizadas / datos inexistentes. "
        "Reafirma que solo usas hechos del Evidence Package."
    ),
    "factual_answer": (
        "Responde de forma directa apoyándote en factual_answer y counts. "
        "Puedes añadir una frase breve de contexto de alcance si ayuda."
    ),
}
