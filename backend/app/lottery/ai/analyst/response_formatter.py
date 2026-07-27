"""Response Formatter — Analyst Experience (Fase C / X.2 v2.3.3).

Presentation layer only. Does NOT modify motor, ranking, Research Engine,
Planner bodies, or Prompt Maestro — only how answers are written.
"""

from __future__ import annotations

import re
from typing import Any, Literal


ResponseMode = Literal["short", "full", "report", "delta"]

REPORT_CASE_THRESHOLD = 40
REPORT_STEP_THRESHOLD = 6
REPORT_COMPARE_THRESHOLD = 2

_BAR = "█"
_BAR_EMPTY = "░"
_MAX_BAR = 18

_REPORT_Q = re.compile(
    r"analiza(r)?\s+completamente|haz\s+un\s+estudio|comp[aá]rame|"
    r"investiga(r)?\s+el\s+comportamiento|genera(r)?\s+un\s+informe|"
    r"busca(r)?\s+patrones|informe\s+completo|estudio\s+completo",
    re.I,
)

_SIMPLE_Q = re.compile(
    r"han\s+salido|alguna\s+vez|cu[aá]ntas?\s+veces|cu[aá]ndo|"
    r"coincid|juntos|mismo\s+d[ií]a|[uú]ltima\s+coinciden|"
    r"^\s*\¿?(y\s+)?en\s+(primera|cualquier)",
    re.I,
)

_TECH_LEAK = re.compile(
    r"\b(kind|payload|herramientas hist[oó]ricas autorizadas|trace|"
    r"tool result|confidence engine|motor intacto|Prompt Maestro|"
    r"no se recomienda apostar|no inventa porcentajes|"
    r"HECHOS y AN[AÁ]LISIS est[aá]n separados)\b",
    re.I,
)


def format_analyst_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    force_structure: bool = True,
    question: str | None = None,
    conversation_context: dict[str, Any] | None = None,
    is_follow_up: bool | None = None,
) -> str:
    """Adaptive short / full / report / delta — mature user-facing language."""
    facts = facts or {}
    research = research or {}
    ctx = conversation_context or {}
    pkg = (
        research.get("evidence_package")
        if isinstance(research.get("evidence_package"), dict)
        else {}
    )

    follow_up = (
        bool(is_follow_up)
        if is_follow_up is not None
        else _detect_follow_up(question, ctx, research)
    )
    mode = select_response_mode(
        text=text,
        facts=facts,
        research=research,
        evidence_package=pkg,
        is_follow_up=follow_up,
        force_structure=force_structure,
        question=question,
    )

    cleaned = _sanitize_user_text(text)

    if mode == "delta":
        out = format_delta_response(
            cleaned,
            facts=facts,
            research=research,
            evidence_package=pkg,
            question=question,
        )
    elif mode == "short":
        out = format_short_response(
            cleaned,
            facts=facts,
            research=research,
            evidence_package=pkg,
        )
    else:
        out = format_professional_response(
            cleaned,
            facts=facts,
            research=research,
            evidence_package=pkg,
            question=question,
            mode=mode,
        )
    return self_verify_response(
        out,
        question=question,
        facts=facts,
        research=research,
        conversation_context=ctx,
    )


def self_verify_response(
    text: str,
    *,
    question: str | None = None,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    conversation_context: dict[str, Any] | None = None,
) -> str:
    """Internal checklist before sending — never exposes reasoning to the user."""
    facts = facts or {}
    research = research or {}
    ctx = conversation_context or {}
    body = _sanitize_user_text(text or "")
    q = (question or "").lower()

    # Strip remaining jargon / vague filler
    vague = re.compile(
        r"(?i)^\s*(-?\s*)?(se encontr[oó] evidencia|el an[aá]lisis indica|"
        r"seg[uú]n las herramientas|podr[ií]a existir una tendencia)\s*\.?\s*$",
    )
    lines = [ln for ln in body.splitlines() if not vague.match(ln)]
    body = "\n".join(lines).strip() or body

    # If question asks same-day / both numbers, ensure both appear when we have them
    nums = list(ctx.get("active_numbers") or research.get("numbers") or [])
    if len(nums) >= 2 and re.search(r"mismo\s+d[ií]a|coincid|juntos", q):
        missing = [n for n in nums[:2] if str(n) not in body]
        if missing and "no encontr" not in body.lower():
            body = f"{body}\n\nNúmeros considerados: {' y '.join(str(n) for n in nums[:2])}."

    # Never claim absolute zero if research says there were other-position hits
    if re.search(r"no (encontr|hay|existe).{0,40}coinciden", body, re.I):
        other = (research.get("evidence_package") or {}).get("other_only") or facts.get(
            "other_only"
        )
        total = (research.get("evidence_package") or {}).get("case_count") or facts.get("total")
        if other and int(other) > 0:
            body = (
                f"No hubo coincidencia en primera posición, pero sí en {other} fecha(s) "
                "al considerar otras posiciones.\n\n" + body
            )
        elif total and int(total) > 0 and "otras posiciones" not in body.lower():
            body = re.sub(
                r"(?i)no (encontr[eé]|hay|existe).{0,60}coinciden[^\n.]*\.?",
                f"Hay {total} coincidencia(s) en el alcance consultado.",
                body,
                count=1,
            )

    # Drop duplicated consecutive paragraphs
    paras = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
    dedup: list[str] = []
    seen: set[str] = set()
    for p in paras:
        key = re.sub(r"\s+", " ", p.lower())
        if key in seen:
            continue
        seen.add(key)
        dedup.append(p)
    return "\n\n".join(dedup).strip()


def format_research_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    evidence_package: dict[str, Any] | None = None,
    question: str | None = None,
    mode: ResponseMode = "full",
) -> str:
    """Backward-compatible alias used by Fase B tests."""
    research = dict(research or {})
    if evidence_package and not research.get("evidence_package"):
        research["evidence_package"] = evidence_package
    return format_professional_response(
        text,
        facts=facts,
        research=research,
        evidence_package=evidence_package or research.get("evidence_package") or {},
        question=question,
        mode=mode if mode in {"full", "report"} else "full",
    )


def select_response_mode(
    *,
    text: str,
    facts: dict[str, Any],
    research: dict[str, Any],
    evidence_package: dict[str, Any],
    is_follow_up: bool,
    force_structure: bool,
    question: str | None = None,
) -> ResponseMode:
    q = question or ""
    if is_follow_up and not _REPORT_Q.search(q):
        return "delta"

    if _REPORT_Q.search(q) or research.get("report_mode"):
        return "report"

    # Same-day / simple factual answers → short
    if (
        research.get("relation") == "same_day"
        or evidence_package.get("relation") == "same_day"
        or _SIMPLE_Q.search(q)
        or _SIMPLE_Q.search(text or "")
    ) and not _REPORT_Q.search(q):
        return "short"

    case_count = _as_int(evidence_package.get("case_count")) or 0
    # Missing/unknown counts do not force report mode
    steps = research.get("steps_completed") or research.get("plan") or []
    step_count = len(steps) if isinstance(steps, list) else 0
    comparisons = evidence_package.get("comparisons") or []
    compare_n = len(comparisons) if isinstance(comparisons, list) else 0
    kind = str(research.get("question_kind") or "")

    complex_kind = kind.startswith("compare") or kind in {
        "case_search",
        "what_usually_happens_after",
        "open_investigation",
        "which_lottery_confirms_first",
        "which_confirms_most",
        "temporal_windows",
    }

    if (
        case_count >= REPORT_CASE_THRESHOLD
        or step_count >= REPORT_STEP_THRESHOLD
        or compare_n >= REPORT_COMPARE_THRESHOLD
        or complex_kind
    ):
        return (
            "report"
            if (case_count >= REPORT_CASE_THRESHOLD or step_count >= REPORT_STEP_THRESHOLD or complex_kind)
            else "full"
        )

    if not research.get("question_kind") and not evidence_package and not force_structure:
        return "short"
    if not research.get("question_kind") and case_count < 5 and step_count <= 1:
        return "short"
    body = (text or "").strip()
    if len(body) < 420 and not facts.get("comparison"):
        return "short"
    if research.get("question_kind") or evidence_package:
        return "full"
    return "full"


def format_short_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    evidence_package: dict[str, Any] | None = None,
) -> str:
    """Compact answer — no HECHOS/ANÁLISIS/Limitaciones boilerplate."""
    facts = facts or {}
    research = research or {}
    pkg = evidence_package or {}
    lead = _lead(text)
    extras: list[str] = []
    # Only add compact facts that add new info not already in lead
    for key, label in (
        ("lottery", "Lotería"),
        ("year", "Período"),
    ):
        val = facts.get(key)
        if val and str(val) not in lead:
            extras.append(f"{label}: {val}.")
    case_count = pkg.get("case_count")
    if case_count is not None and str(case_count) not in lead:
        try:
            if int(case_count) > 0 or not pkg.get("timeline"):
                extras.append(f"Registros consultados: {case_count}.")
        except (TypeError, ValueError):
            pass
    lim = _limitations(pkg, only_material=True)
    parts = [lead]
    if extras:
        parts.append("\n".join(extras))
    if lim:
        parts.append(lim)
    return "\n\n".join(p for p in parts if p).strip()


def format_delta_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    evidence_package: dict[str, Any] | None = None,
    question: str | None = None,
) -> str:
    """Follow-up: only what is new — do not repeat the full prior report."""
    facts = facts or {}
    research = research or {}
    pkg = evidence_package or {}
    lead = _lead(text)
    q = (question or "").strip()
    # Avoid repeating the same conclusion under multiple headings
    bits = []
    if q and q.lower() not in lead.lower():
        bits.append(f"Sobre tu pregunta ({q}):")
    bits.append(lead)
    lim = _limitations(pkg, only_material=True)
    if lim:
        bits.append(lim)
    return "\n\n".join(bits).strip()


def format_professional_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    evidence_package: dict[str, Any] | None = None,
    question: str | None = None,
    mode: ResponseMode = "full",
) -> str:
    facts = facts or {}
    research = research or {}
    pkg = evidence_package or {}
    lead = _lead(text)
    if facts.get("primary") is not None and str(facts["primary"]) not in lead:
        lead = f"{lead} Candidato principal (dato histórico): {facts['primary']}."

    hallazgos = _hallazgos(facts, pkg, research, lead)
    analisis = _analisis_block(lead, facts, pkg, research)
    evidencias = _evidence_block(pkg, research, compact=False)
    comparaciones = _comparison_block(facts, pkg, research)
    viz = _ascii_from_facts(facts, pkg, research, max_items=8)
    observaciones = _observaciones(research, pkg, lead)
    limitations = _limitations(pkg, only_material=True)
    suggestions = _suggestions(research, pkg, facts, compact=False)

    # Deduplicate: don't repeat lead in hallazgos/analisis/observaciones
    if hallazgos and _normalize_dup(hallazgos) == _normalize_dup(lead):
        hallazgos = None
    if analisis and _normalize_dup(analisis) == _normalize_dup(lead):
        analisis = None
    if observaciones and _normalize_dup(observaciones) == _normalize_dup(lead):
        observaciones = None

    header = None
    if mode == "report":
        header = "Informe de investigación histórica"

    sections: list[tuple[str, str | None]] = []
    if header:
        sections.append(("Encabezado", header))
    sections.extend(
        [
            ("Respuesta", lead if mode != "report" else _executive_report(lead, pkg, research)),
            ("Hallazgos", hallazgos),
            ("Detalle", _hechos_block(facts, pkg, research, compact=False)),
            ("Interpretación", analisis),
            ("Observación", observaciones),
            ("Comparaciones", comparaciones),
            ("Visualización", viz),
            ("Evidencias", evidencias if mode == "report" else None),
            ("Aclaración", limitations),
            ("Siguiente paso", suggestions if mode == "report" else None),
        ]
    )
    return _join_sections(sections)


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------


def _sanitize_user_text(text: str) -> str:
    if not text:
        return text
    lines = []
    for line in text.splitlines():
        if _TECH_LEAK.search(line):
            continue
        lines.append(line)
    return "\n".join(lines).strip() or (text or "").strip()


def _normalize_dup(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip(" -•*")


def _lead(text: str) -> str:
    body = _sanitize_user_text(text or "").strip()
    if not body:
        return "No encontré suficiente evidencia para responder con seguridad."
    return body.split("\n\n")[0].strip()


def _executive_report(lead: str, pkg: dict[str, Any], research: dict[str, Any]) -> str:
    cases = pkg.get("case_count")
    bits = [lead]
    if cases is not None:
        bits.append(f"Se revisaron {cases} registros de referencia.")
    return " ".join(bits)


def _hechos_block(
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
    *,
    compact: bool,
) -> str | None:
    lines: list[str] = []
    if facts.get("observed") is not None:
        lines.append(f"- Número observado: {facts['observed']}")
    if facts.get("confirmer") is not None:
        lines.append(f"- Confirmador: {facts['confirmer']}")
    if facts.get("primary") is not None:
        lines.append(f"- Candidato principal (dato): {facts['primary']}")
    if facts.get("lottery"):
        lines.append(f"- Lotería activa: {facts['lottery']}")
    if facts.get("year") or (isinstance(pkg.get("period"), str) and pkg.get("period")):
        lines.append(f"- Período: {facts.get('year') or pkg.get('period')}")
    case_count = pkg.get("case_count")
    has_date = bool(pkg.get("timeline") or facts.get("last_occurrence_date"))
    if case_count is not None:
        try:
            n = int(case_count)
        except (TypeError, ValueError):
            n = None
        # Invariant: never show registros=0 when a last-occurrence date exists
        if n is not None and not (n == 0 and has_date):
            lines.append(f"- Cantidad de casos/registros: {n}")
    for f in (pkg.get("findings") or [])[: (3 if compact else 8)]:
        lines.append(f"- {f}")
    hist = facts.get("historical") or facts.get("historical_summary")
    if isinstance(hist, dict):
        if hist.get("exact_cases") is not None:
            lines.append(f"- Casos exactos consultados: {hist.get('exact_cases')}")
        if hist.get("evaluable_cases") is not None:
            lines.append(f"- Casos evaluables: {hist.get('evaluable_cases')}")
        if hist.get("d7_hits") is not None:
            lines.append(f"- Apariciones exactas hasta D+7: {hist.get('d7_hits')}")
    if not lines:
        return None
    return "\n".join(lines)


def _hallazgos(
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
    lead: str,
) -> str | None:
    items: list[str] = []
    if facts.get("primary") is not None and str(facts["primary"]) not in lead:
        items.append(f"El resultado principal reportado es {facts['primary']}.")
    case_count = pkg.get("case_count")
    if case_count is not None and str(case_count) not in lead:
        items.append(f"Se consultaron {case_count} casos/registros históricos relevantes.")
    for c in (pkg.get("comparisons") or [])[:3]:
        if str(c) not in lead:
            items.append(str(c))
    for t in (pkg.get("timeline") or [])[:2]:
        if str(t) not in lead:
            items.append(str(t))
    if not items:
        return None
    return "\n".join(f"- {x}" for x in items if x)


def _analisis_block(
    lead: str,
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
) -> str | None:
    return _explain_why(lead, facts, pkg, research)


def _explain_why(
    lead: str,
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
) -> str | None:
    """Natural interpretation — no internal jargon, no repeated conclusion."""
    case_count = pkg.get("case_count")
    parts: list[str] = []

    if case_count is not None:
        parts.append(
            f"La lectura se basa en {case_count} caso(s)/registro(s) consultados en el histórico."
        )
    elif pkg.get("findings"):
        parts.append("La lectura se basa en los hallazgos devueltos por la consulta histórica.")
    else:
        # Prefer fixing upstream; only surface when truly empty
        if not lead or "no encontr" in lead.lower():
            parts.append(
                "No puedo precisar el total porque la consulta no devolvió un conteo completo."
            )

    m = re.search(
        r"\b([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚáéíóúñ]*(?:\s+[\wÁÉÍÓÚáéíóúñ]+){0,3})\s+"
        r"(confirm[oó]|apareci[oó]|mostr[oó])\s+primero",
        lead,
        re.I,
    )
    if m:
        subject = m.group(1)
        parts.append(
            f"«{subject} confirmó primero» significa que, en los casos evaluados, "
            "fue el primer registro temporal relevante."
        )
    elif facts.get("primary") is not None and str(facts["primary"]) not in lead:
        parts.append(
            f"Que {facts['primary']} figure como principal describe el resultado "
            "matemático del análisis para el input dado."
        )

    comparisons = pkg.get("comparisons") or []
    if comparisons:
        parts.append(
            "Las diferencias numéricas indican mayor o menor volumen histórico, "
            "no un resultado futuro."
        )

    # Do NOT restate lead ("Lectura directa…")
    if not parts:
        return None
    return "\n".join(f"- {p}" for p in parts)


def _observaciones(
    research: dict[str, Any],
    pkg: dict[str, Any],
    lead: str = "",
) -> str | None:
    lines: list[str] = []
    if pkg.get("timeline") and "cronolog" not in lead.lower():
        lines.append("Hay anclas temporales en la evidencia; conviene revisar la cronología.")
    if research.get("relation") == "same_day":
        lines.append(
            "La preferencia de primera posición se destaca aparte; "
            "el total incluye todas las posiciones."
        )
    if not lines:
        return None
    return "\n".join(f"- {x}" for x in lines)


def _evidence_block(pkg: dict[str, Any], research: dict[str, Any], *, compact: bool) -> str | None:
    case_count = pkg.get("case_count")
    period = pkg.get("period")
    lines = []
    if case_count is not None:
        lines.append(f"- Cantidad de casos: {case_count}")
    if period:
        lines.append(f"- Período: {period}")
    findings = pkg.get("findings") or []
    for f in findings[: (2 if compact else 6)]:
        lines.append(f"- {f}")
    if not lines:
        return None
    return "\n".join(lines)


def _comparison_block(
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
) -> str | None:
    raw = list(pkg.get("comparisons") or [])
    if facts.get("comparison"):
        raw.insert(0, str(facts["comparison"]))
    subjects = []
    meta = research.get("research_meta") if isinstance(research.get("research_meta"), dict) else {}
    for n in meta.get("subjects") or []:
        subjects.append(str(n))
    if facts.get("observed") is not None and facts.get("compare_with") is not None:
        subjects = [str(facts["observed"]), str(facts["compare_with"])]

    if not raw and not subjects and not str(research.get("question_kind") or "").startswith("compare"):
        return None

    diferencias = [str(x) for x in raw[:6]] or [
        "Las diferencias concretas dependen de los conteos de cada consulta."
    ]
    head = ""
    if subjects and len(subjects) >= 2:
        head = f"Comparación activa: {subjects[0]} vs {subjects[1]}.\n\n"
    return head + "Diferencias\n" + "\n".join(f"- {x}" for x in diferencias)


def _limitations(pkg: dict[str, Any], *, only_material: bool = True) -> str | None:
    """Only material accuracy caveats — no generic architecture disclaimers."""
    base = list(pkg.get("limitations") or [])
    material_hints = (
        "hora",
        "72",
        "anterior",
        "incomplet",
        "faltan",
        "formato",
        "cobertura",
        "no contiene",
        "sin datos",
        "parcial",
    )
    lines: list[str] = []
    seen: set[str] = set()
    for x in base:
        if not x:
            continue
        low = str(x).lower()
        # Drop generic boilerplate
        if any(
            g in low
            for g in (
                "no garantiza resultados futuros",
                "hechos y análisis",
                "no modifica",
                "no se inventan",
                "no se recomienda apostar",
                "prompt maestro",
                "motor intacto",
            )
        ):
            continue
        if only_material and not any(h in low for h in material_hints):
            continue
        if x not in seen:
            seen.add(x)
            lines.append(f"- {x}")
    if not lines:
        return None
    return "\n".join(lines)


def _suggestions(
    research: dict[str, Any],
    pkg: dict[str, Any],
    facts: dict[str, Any],
    *,
    compact: bool,
) -> str | None:
    suggestions = list(pkg.get("related_suggestions") or [])
    nums = list(research.get("numbers") or [])
    if len(nums) >= 2:
        suggestions = [
            "Ver fechas de coincidencia.",
            "Desglosar por posición.",
            "Ver coincidencias en primera.",
            "Ver la última coincidencia.",
            *suggestions,
        ]
    elif facts.get("observed") is not None:
        observed = facts.get("observed")
        suggestions.append(f"¿Filtro el {observed} por una sola lotería?")
    if not suggestions:
        return None
    limit = 3 if compact else 5
    return "\n".join(f"- {s}" for s in list(dict.fromkeys(suggestions))[:limit])


# ---------------------------------------------------------------------------
# ASCII visualizations
# ---------------------------------------------------------------------------


def render_bar(label: str, value: int, *, max_value: int | None = None, width: int = _MAX_BAR) -> str:
    mv = max(max_value or value, 1)
    filled = int(round((value / mv) * width)) if mv else 0
    filled = max(0, min(width, filled))
    return f"{label[:18]:<18} {_BAR * filled}{_BAR_EMPTY * (width - filled)} {value}"


def render_ranking_bars(items: list[tuple[str, int]], *, width: int = _MAX_BAR) -> str:
    if not items:
        return ""
    mx = max(v for _, v in items) or 1
    return "\n".join(render_bar(lab, val, max_value=mx, width=width) for lab, val in items)


def _ascii_from_facts(
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
    *,
    max_items: int,
) -> str | None:
    chart = pkg.get("chart") or facts.get("chart")
    if isinstance(chart, dict) and chart.get("bars"):
        lines = []
        bars = chart["bars"][:max_items]
        mx = max(int(b.get("value") or 0) for b in bars) if bars else 1
        for b in bars:
            lines.append(render_bar(str(b.get("label") or "?"), int(b.get("value") or 0), max_value=mx))
        return "\n".join(lines) if lines else None

    comparisons = pkg.get("comparisons") or []
    numeric: list[tuple[str, int]] = []
    for c in comparisons:
        if isinstance(c, dict) and c.get("label") is not None and c.get("value") is not None:
            try:
                numeric.append((str(c["label"]), int(c["value"])))
            except (TypeError, ValueError):
                continue
        elif isinstance(c, str):
            m = re.search(r"(.+?):\s*(\d+)", c)
            if m:
                numeric.append((m.group(1).strip(), int(m.group(2))))
    if numeric:
        mx = max(v for _, v in numeric) or 1
        return "\n".join(render_bar(lab, val, max_value=mx) for lab, val in numeric[:max_items])
    return None


def _join_sections(sections: list[tuple[str, str | None]]) -> str:
    blocks: list[str] = []
    for title, body in sections:
        if not body or not str(body).strip():
            continue
        if title == "Encabezado":
            blocks.append(str(body).strip())
        elif title == "Respuesta":
            blocks.append(str(body).strip())
        else:
            blocks.append(f"**{title}**\n{str(body).strip()}")
    return "\n\n".join(blocks).strip()


def _detect_follow_up(
    question: str | None,
    ctx: dict[str, Any],
    research: dict[str, Any],
) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False
    if re.match(r"^(y\s+)?(en\s+)?(primera|cualquier|esa|ese|la\s+[uú]ltima)", q):
        return True
    if ctx.get("has_prior_research") and re.match(r"^(y\s+|entonces\s+|ahora\s+)", q):
        return True
    return False


def _as_int(v: Any) -> int | None:
    try:
        if v is None:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None
