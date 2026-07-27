"""Response Formatter — Analyst Experience (Fase C / v2.1.0).

Presentation layer only. Does NOT modify motor, ranking, Research Engine,
Planner, or Conversation Brain logic — only how answers are written.
"""

from __future__ import annotations

import re
from typing import Any, Literal


ResponseMode = Literal["short", "full", "report", "delta"]

# Investigation size above this → automatic report layout
REPORT_CASE_THRESHOLD = 40
REPORT_STEP_THRESHOLD = 6
REPORT_COMPARE_THRESHOLD = 2

_BAR = "█"
_BAR_EMPTY = "░"
_MAX_BAR = 18


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
    """Fase C professional formatter — adaptive short / full / report / delta."""
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
    )

    if mode == "delta":
        return format_delta_response(
            text,
            facts=facts,
            research=research,
            evidence_package=pkg,
            question=question,
        )
    if mode == "short":
        return format_short_response(
            text,
            facts=facts,
            research=research,
            evidence_package=pkg,
        )
    # full + report share the same section skeleton; report adds title + ASCII
    return format_professional_response(
        text,
        facts=facts,
        research=research,
        evidence_package=pkg,
        question=question,
        mode=mode,
    )


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
) -> ResponseMode:
    if is_follow_up:
        return "delta"

    case_count = _as_int(evidence_package.get("case_count")) or 0
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
        return "report" if (case_count >= REPORT_CASE_THRESHOLD or step_count >= REPORT_STEP_THRESHOLD or complex_kind) else "full"

    # Simple: short answer unless force_structure and we have research meta
    if not research.get("question_kind") and not evidence_package and not force_structure:
        return "short"
    if not research.get("question_kind") and case_count < 5 and step_count <= 1:
        return "short"
    if research.get("question_kind") or evidence_package:
        return "full"
    body = (text or "").strip()
    if len(body) < 220 and not facts.get("comparison"):
        return "short"
    return "full"


def format_short_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    evidence_package: dict[str, Any] | None = None,
) -> str:
    facts = facts or {}
    research = research or {}
    pkg = evidence_package or {}
    lead = _lead(text)
    facts_block = _hechos_block(facts, pkg, research, compact=True)
    why = _explain_why(lead, facts, pkg, research)
    limitations = _limitations(pkg)
    sections = [
        ("Resumen Ejecutivo", lead),
        ("HECHOS", facts_block),
        ("ANÁLISIS", why),
        ("Limitaciones", limitations),
        ("Próximas investigaciones sugeridas", _suggestions(research, pkg, facts, compact=True)),
    ]
    return _join_sections(sections)


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
    focus = f"Sobre tu pregunta: {q}" if q else "Actualización sobre el contexto activo."
    new_facts = _hechos_block(facts, pkg, research, compact=True)
    why = _explain_why(lead, facts, pkg, research)
    viz = _ascii_from_facts(facts, pkg, research, max_items=4)
    sections = [
        ("Resumen Ejecutivo", f"{focus}\n{lead}"),
        ("Hallazgos Principales (solo lo nuevo)", new_facts),
        ("ANÁLISIS", why),
        ("Visualización", viz),
        ("Evidencias", _evidence_block(pkg, research, compact=True)),
        ("Limitaciones", _limitations(pkg)),
        ("Próximas investigaciones sugeridas", _suggestions(research, pkg, facts, compact=True)),
    ]
    return _join_sections(sections)


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
        lead = f"{lead} Candidato principal del motor (solo lectura): {facts['primary']}."

    hallazgos = _hallazgos(facts, pkg, research, lead)
    analisis = _analisis_block(lead, facts, pkg, research)
    evidencias = _evidence_block(pkg, research, compact=False)
    comparaciones = _comparison_block(facts, pkg, research)
    viz = _ascii_from_facts(facts, pkg, research, max_items=8)
    observaciones = _observaciones(research, pkg)
    limitations = _limitations(pkg)
    suggestions = _suggestions(research, pkg, facts, compact=False)

    header = None
    if mode == "report":
        kind = research.get("question_kind") or "investigación histórica"
        header = (
            f"INFORME DE INVESTIGACIÓN — {kind}\n"
            f"(formato informe; no es una predicción)"
        )

    sections: list[tuple[str, str | None]] = []
    if header:
        sections.append(("Encabezado", header))
    sections.extend(
        [
            ("Resumen Ejecutivo", lead if mode != "report" else _executive_report(lead, pkg, research)),
            ("Hallazgos Principales", hallazgos),
            ("HECHOS", _hechos_block(facts, pkg, research, compact=False)),
            ("ANÁLISIS", analisis),
            ("OBSERVACIONES", observaciones),
            ("Comparaciones", comparaciones),
            ("Visualización", viz),
            ("Evidencias", evidencias),
            ("Limitaciones", limitations),
            ("Próximas investigaciones sugeridas", suggestions),
        ]
    )
    return _join_sections(sections)


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------


def _lead(text: str) -> str:
    body = (text or "").strip()
    if not body:
        return "No encontré suficiente evidencia para responder con seguridad."
    return body.split("\n\n")[0].strip()


def _executive_report(lead: str, pkg: dict[str, Any], research: dict[str, Any]) -> str:
    conf = pkg.get("evidence_level") or research.get("confidence") or "Baja"
    cases = pkg.get("case_count")
    bits = [lead, f"Nivel de evidencia: {conf}."]
    if cases is not None:
        bits.append(f"Casos/registros de referencia: {cases}.")
    return " ".join(bits)


def _hechos_block(
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
    *,
    compact: bool,
) -> str:
    lines: list[str] = []
    if facts.get("observed") is not None:
        lines.append(f"- Número observado: {facts['observed']}")
    if facts.get("confirmer") is not None:
        lines.append(f"- Confirmador: {facts['confirmer']}")
    if facts.get("primary") is not None:
        lines.append(f"- Candidato principal del motor (dato, no predicción): {facts['primary']}")
    if facts.get("lottery"):
        lines.append(f"- Lotería activa: {facts['lottery']}")
    if facts.get("year") or (isinstance(pkg.get("period"), str) and pkg.get("period")):
        lines.append(f"- Período: {facts.get('year') or pkg.get('period')}")
    case_count = pkg.get("case_count")
    if case_count is not None:
        lines.append(f"- Cantidad de casos/registros: {case_count}")
    for f in (pkg.get("findings") or [])[: (3 if compact else 8)]:
        # Strip interpretive verbs when possible — keep as factual bullets
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
        lines.append("- Hechos insuficientes en el payload; se respondió con la plantilla disponible.")
    return "\n".join(lines)


def _hallazgos(
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
    lead: str,
) -> str:
    items: list[str] = []
    if facts.get("primary") is not None:
        items.append(f"El motor reporta como principal a {facts['primary']} (solo lectura).")
    case_count = pkg.get("case_count")
    if case_count is not None:
        items.append(f"Se consultaron {case_count} casos/registros históricos relevantes.")
    conf = pkg.get("evidence_level") or research.get("confidence")
    if conf:
        items.append(f"Nivel de evidencia cualitativo: {conf}.")
    for c in (pkg.get("comparisons") or [])[:3]:
        items.append(str(c))
    for t in (pkg.get("timeline") or [])[:2]:
        items.append(str(t))
    if not items:
        items.append(lead)
    return "\n".join(f"- {x}" for x in items if x)


def _analisis_block(
    lead: str,
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
) -> str:
    """Interpretation separated from raw facts — always explains the why."""
    return _explain_why(lead, facts, pkg, research)


def _explain_why(
    lead: str,
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
) -> str:
    case_count = pkg.get("case_count")
    conf = pkg.get("evidence_level") or research.get("confidence") or "Baja"
    criterion = pkg.get("criterion") or "herramientas históricas autorizadas"
    kind = research.get("question_kind") or "consulta"

    parts: list[str] = []
    parts.append(
        f"La conclusión se apoya en el kind «{kind}» y el criterio «{criterion}»."
    )
    if case_count is not None:
        parts.append(
            f"Se observó sobre {case_count} caso(s)/registro(s) consultados; "
            f"eso explica el nivel de evidencia «{conf}»."
        )
    else:
        parts.append(
            f"El nivel de evidencia es «{conf}» porque la cantidad de casos "
            "no quedó cuantificada con claridad en el payload."
        )

    # If lead mentions a lottery / confirmation — expand meaning
    m = re.search(
        r"\b([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚáéíóúñ]*(?:\s+[\wÁÉÍÓÚáéíóúñ]+){0,3})\s+"
        r"(confirm[oó]|apareci[oó]|mostr[oó])\s+primero",
        lead,
        re.I,
    )
    if m:
        subject = m.group(1)
        parts.append(
            f"«{subject} confirmó primero» significa que, dentro de los casos evaluados "
            f"y el criterio temporal usado, fue la primera lotería/evento en registrar "
            f"el destino. No significa que siempre lo hará, ni que sea una recomendación."
        )
    elif facts.get("primary") is not None:
        parts.append(
            f"Que el motor señale {facts['primary']} como principal describe el resultado "
            "matemático de Tabla 1/2 + ranking para el input dado; no implica que 'vaya a salir'."
        )

    comparisons = pkg.get("comparisons") or []
    if comparisons:
        parts.append(
            "En comparación, las diferencias numéricas indican mayor o menor volumen/"
            "cobertura histórica, no superioridad predictiva."
        )

    parts.append(f"Lectura directa del resultado: {lead}")
    return "\n".join(f"- {p}" for p in parts)


def _observaciones(research: dict[str, Any], pkg: dict[str, Any]) -> str:
    lines: list[str] = []
    steps = research.get("steps_completed") or []
    if steps:
        lines.append(
            "La investigación usó pasos autorizados: "
            + ", ".join(str(s) for s in steps[:8])
            + "."
        )
    if research.get("cache_hits"):
        lines.append(
            f"Se reutilizaron {research['cache_hits']} resultado(s) cacheados para evitar consultas repetidas."
        )
    if pkg.get("timeline"):
        lines.append("Hay anclas temporales en la evidencia; conviene revisar la cronología.")
    if not lines:
        lines.append(
            "Observación: la respuesta separa hechos de interpretación; "
            "cualquier lectura a futuro queda fuera de alcance."
        )
    return "\n".join(f"- {x}" for x in lines)


def _evidence_block(pkg: dict[str, Any], research: dict[str, Any], *, compact: bool) -> str:
    conf = pkg.get("evidence_level") or research.get("confidence") or "Baja"
    criterion = pkg.get("criterion") or "herramientas históricas autorizadas"
    period = pkg.get("period") or "período del histórico consultado"
    tools = pkg.get("tools_used") or research.get("steps_completed") or []
    case_count = pkg.get("case_count")
    lines = [
        f"- Cantidad de casos: {case_count if case_count is not None else 'N/D'}",
        f"- Criterio: {criterion}",
        f"- Período: {period}",
        f"- Herramientas utilizadas: {', '.join(str(t) for t in tools[: (4 if compact else 10)]) or 'N/D'}",
        f"- Nivel de evidencia: {conf}",
    ]
    return "\n".join(lines)


def _comparison_block(
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
) -> str | None:
    raw = list(pkg.get("comparisons") or [])
    if facts.get("comparison"):
        raw.insert(0, str(facts["comparison"]))
    # Extract numeric subjects from facts / research meta
    subjects = []
    meta = research.get("research_meta") if isinstance(research.get("research_meta"), dict) else {}
    for n in (meta.get("subjects") or []):
        subjects.append(str(n))
    if facts.get("observed") is not None and facts.get("compare_with") is not None:
        subjects = [str(facts["observed"]), str(facts["compare_with"])]

    if not raw and not subjects and not str(research.get("question_kind") or "").startswith("compare"):
        return None

    similitudes = [
        "Ambos sujetos se evaluaron con las mismas herramientas históricas autorizadas.",
        "Ninguno de los conteos implica predicción ni recomendación de apuesta.",
    ]
    diferencias = [str(x) for x in raw[:6]] or [
        "Las diferencias concretas dependen de los conteos devueltos por cada herramienta."
    ]
    conclusiones = [
        (
            f"Con nivel de evidencia «{pkg.get('evidence_level') or research.get('confidence') or 'Baja'}», "
            "la comparación describe volumen/cobertura histórica, no un ganador futuro."
        )
    ]
    if subjects and len(subjects) >= 2:
        conclusiones.insert(
            0,
            f"Comparación activa: {subjects[0]} vs {subjects[1]}.",
        )

    return (
        "Similitudes\n"
        + "\n".join(f"- {x}" for x in similitudes)
        + "\n\nDiferencias\n"
        + "\n".join(f"- {x}" for x in diferencias)
        + "\n\nConclusiones\n"
        + "\n".join(f"- {x}" for x in conclusiones)
    )


def _limitations(pkg: dict[str, Any]) -> str:
    base = list(pkg.get("limitations") or [])
    defaults = [
        "El histórico describe eventos anteriores y no garantiza resultados futuros.",
        "HECHOS y ANÁLISIS están separados: la interpretación no crea datos nuevos.",
        "El Analista IA no modifica Tabla 1/2, ranking, motor ni Prompt Maestro.",
        "No se inventan porcentajes ni se recomienda apostar.",
    ]
    seen: set[str] = set()
    lines: list[str] = []
    for x in [*base, *defaults]:
        if x and x not in seen:
            seen.add(x)
            lines.append(f"- {x}")
    return "\n".join(lines)


def _suggestions(
    research: dict[str, Any],
    pkg: dict[str, Any],
    facts: dict[str, Any],
    *,
    compact: bool,
) -> str:
    suggestions = list(pkg.get("related_suggestions") or [])
    observed = facts.get("observed") or facts.get("primary")
    kind = str(research.get("question_kind") or "")
    if observed is not None:
        suggestions.append(f"¿Filtro el {observed} solo en Nacional/Loteka/Leidsa/Real?")
        suggestions.append(f"¿Comparo el {observed} únicamente en 2026 vs 2025?")
    if kind.startswith("compare"):
        suggestions.append("¿Muestro solo diferencias en primera posición?")
    if "after" in kind or "temporal" in kind:
        suggestions.append("¿Restrinjo a D+1 únicamente?")
    if not suggestions:
        suggestions = [
            "¿Quieres filtrar por una sola lotería?",
            "¿Comparo con otro número del contexto?",
            "¿Acoto el período a un año concreto?",
        ]
    limit = 3 if compact else 5
    return "\n".join(f"- {s}" for s in list(dict.fromkeys(suggestions))[:limit])


# ---------------------------------------------------------------------------
# ASCII visualizations
# ---------------------------------------------------------------------------


def render_bar(label: str, value: int, *, max_value: int | None = None, width: int = _MAX_BAR) -> str:
    v = max(0, int(value))
    mv = max(1, int(max_value or v or 1))
    filled = int(round((v / mv) * width)) if mv else 0
    filled = max(0, min(width, filled))
    bar = _BAR * filled + _BAR_EMPTY * (width - filled)
    return f"{label}\n{bar}\n{v} casos"


def render_ranking_bars(items: list[tuple[str, int]], *, width: int = _MAX_BAR) -> str:
    if not items:
        return ""
    max_v = max(int(v) for _, v in items) or 1
    blocks = [render_bar(str(label), int(val), max_value=max_v, width=width) for label, val in items]
    return "\n\n".join(blocks)


def _ascii_from_facts(
    facts: dict[str, Any],
    pkg: dict[str, Any],
    research: dict[str, Any],
    *,
    max_items: int,
) -> str | None:
    pairs: list[tuple[str, int]] = []

    # Explicit chart payloads
    charts = facts.get("charts") or research.get("charts") or pkg.get("charts")
    if isinstance(charts, list):
        for item in charts[:max_items]:
            if isinstance(item, dict) and item.get("label") is not None and item.get("value") is not None:
                try:
                    pairs.append((str(item["label"]), int(item["value"])))
                except (TypeError, ValueError):
                    continue

    # Comparison subjects with counts in findings like "54: 3467"
    if not pairs:
        for f in pkg.get("findings") or []:
            m = re.search(r"(?:^|\b)(\d{1,2}|[A-Za-zÁÉÍÓÚáéíóúñ ]{2,40}).{0,20}?\b(\d{2,6})\b", str(f))
            if m:
                try:
                    pairs.append((m.group(1).strip(), int(m.group(2))))
                except ValueError:
                    pass
            if len(pairs) >= max_items:
                break

    # Fallback: case_count alone
    if not pairs and pkg.get("case_count") is not None:
        label = str(facts.get("observed") or research.get("question_kind") or "Casos")
        pairs.append((label, int(pkg["case_count"])))

    # Dual subjects from meta without values — skip empty viz
    if not pairs:
        return None
    return render_ranking_bars(pairs[:max_items])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_follow_up(
    question: str | None,
    ctx: dict[str, Any],
    research: dict[str, Any],
) -> bool:
    if ctx.get("is_follow_up"):
        return True
    if research.get("delta_only"):
        return True
    q = (question or "").strip().lower()
    if not q:
        # If conversation already has active numbers / last research, treat short continuations as follow-up when flagged
        return bool(ctx.get("has_prior_research"))
    markers = (
        "y ahora",
        "ahora solo",
        "ahora solamente",
        "y solamente",
        "compáralo",
        "comparalo",
        "¿y ",
        "y en ",
        "dentro de",
        "muéstrame solamente",
        "muestrame solamente",
        "solo durante",
        "solamente en",
        "cuál de los dos",
        "cual de los dos",
    )
    if any(m in q for m in markers):
        return True
    # Leading connector
    if re.match(r"^(¿?\s*)?(y|ahora|solo|solamente|después|despues)\b", q):
        return True
    return False


def _as_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _join_sections(sections: list[tuple[str, str | None]]) -> str:
    lines: list[str] = []
    for title, content in sections:
        if not content or not str(content).strip():
            continue
        lines.append(f"{title}\n{str(content).strip()}")
    return "\n\n".join(lines).strip()
