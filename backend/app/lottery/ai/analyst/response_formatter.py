"""Response formatter — professional Analista IA / Research Engine sections."""

from __future__ import annotations

import re
from typing import Any


def format_analyst_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    force_structure: bool = True,
) -> str:
    """Ensure professional sectioned answer without inventing new facts."""
    facts = facts or {}
    research = research or {}
    evidence_pkg = research.get("evidence_package") if isinstance(research.get("evidence_package"), dict) else {}

    # Prefer Research Engine professional layout when investigation completed
    if evidence_pkg or research.get("question_kind") or research.get("confidence"):
        return format_research_response(
            text,
            facts=facts,
            research=research,
            evidence_package=evidence_pkg,
        )

    body = (text or "").strip()
    if not body:
        body = "No encontré suficiente evidencia para responder con seguridad."

    has_conclusion = bool(re.search(r"(?im)^\s*(conclusi[oó]n|resumen\s+ejecutivo)\b", body))
    if has_conclusion and not force_structure:
        return _ensure_limitations(body)

    first = body.split("\n\n")[0].strip()
    rest = body[len(first) :].strip() if body.startswith(first) else body

    evid_bits: list[str] = []
    hist_bits: list[str] = []
    cmp_bits: list[str] = []

    primary = facts.get("primary") or facts.get("current_primary_candidate")
    observed = facts.get("observed") or facts.get("observed_number")
    confirmer = facts.get("confirmer")
    if primary is not None:
        evid_bits.append(f"Candidato principal del motor: {primary}.")
    if observed is not None:
        evid_bits.append(f"Número observado: {observed}.")
    if confirmer is not None:
        evid_bits.append(f"Confirmador: {confirmer}.")

    hist = facts.get("historical") or facts.get("historical_summary")
    if isinstance(hist, dict):
        if hist.get("exact_cases") or hist.get("evaluable_cases"):
            cases = hist.get("exact_cases") or hist.get("evaluable_cases")
            hist_bits.append(f"Casos equivalentes consultados: {cases}.")
        if hist.get("d7_hits") is not None:
            hist_bits.append(
                f"Comportamiento observado hasta D+7: {hist.get('d7_hits')} apariciones exactas en el histórico."
            )
    elif isinstance(hist, str) and hist.strip():
        hist_bits.append(hist.strip())

    if facts.get("comparison"):
        cmp_bits.append(str(facts["comparison"]))

    observation = None
    if research.get("steps_completed"):
        observation = (
            "La respuesta se construyó consultando herramientas autorizadas "
            f"({', '.join(str(x) for x in research['steps_completed'][:6])})."
        )

    sections = [
        ("Conclusión", first),
        ("Explicación", rest if rest and rest != first else None),
        ("Evidencias", " ".join(evid_bits) if evid_bits else None),
        ("Histórico", " ".join(hist_bits) if hist_bits else None),
        ("Comparación", " ".join(cmp_bits) if cmp_bits else None),
        ("Observación del Analista", observation),
        (
            "Limitaciones",
            "El histórico describe eventos anteriores y no garantiza resultados futuros. "
            "El Analista IA no modifica el motor ni el ranking.",
        ),
    ]
    return _join_sections(sections)


def format_research_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    evidence_package: dict[str, Any] | None = None,
) -> str:
    """Fase B professional investigation response layout."""
    facts = facts or {}
    research = research or {}
    pkg = evidence_package or {}
    body = (text or "").strip()
    lead = body.split("\n\n")[0].strip() if body else "Investigación completada con las herramientas autorizadas."

    confidence = pkg.get("evidence_level") or research.get("confidence") or "Baja"
    case_count = pkg.get("case_count")
    criterion = pkg.get("criterion") or "herramientas históricas autorizadas"
    period = pkg.get("period") or "período consultado en el histórico"
    tools = pkg.get("tools_used") or research.get("steps_completed") or []

    executive = (
        f"Investigación {research.get('question_kind') or 'histórica'} con confianza {confidence}. "
        f"Criterio: {criterion}."
    )
    if case_count:
        executive += f" Casos/registros de referencia: {case_count}."

    result = lead
    if facts.get("primary") is not None:
        result += f" Candidato principal del motor (solo lectura): {facts.get('primary')}."

    evid_lines = list(pkg.get("findings") or [])
    evid_lines.insert(
        0,
        f"Nivel de evidencia: {confidence}. Criterio: {criterion}. Período: {period}. "
        f"Herramientas: {', '.join(str(t) for t in tools[:8]) or 'N/D'}.",
    )
    if case_count is not None:
        evid_lines.insert(1, f"Cantidad de casos/registros consultados: {case_count}.")

    comparisons = list(pkg.get("comparisons") or [])
    if facts.get("comparison"):
        comparisons.insert(0, str(facts["comparison"]))

    timeline = list(pkg.get("timeline") or [])
    suggestions = list(pkg.get("related_suggestions") or [])
    limitations = list(pkg.get("limitations") or [])
    if not limitations:
        limitations = [
            "El histórico describe eventos anteriores y no garantiza resultados futuros.",
            "El Research Engine no modifica Tabla 1/2, ranking ni Prompt Maestro.",
        ]

    sections = [
        ("Resumen Ejecutivo", executive),
        ("Resultado", result),
        ("Evidencias", "\n".join(f"- {x}" for x in evid_lines if x)),
        ("Comparaciones", "\n".join(f"- {x}" for x in comparisons if x) or None),
        ("Cronología", "\n".join(f"- {x}" for x in timeline if x) or None),
        ("Conclusión", lead),
        ("Limitaciones", "\n".join(f"- {x}" for x in limitations)),
        (
            "Sugerencias de investigación relacionadas",
            "\n".join(f"- {x}" for x in suggestions) or None,
        ),
    ]
    return _join_sections(sections)


def _join_sections(sections: list[tuple[str, str | None]]) -> str:
    lines: list[str] = []
    for title, content in sections:
        if not content:
            continue
        lines.append(f"{title}\n{content.strip()}")
    return "\n\n".join(lines).strip()


def _ensure_limitations(body: str) -> str:
    if re.search(r"(?im)^\s*limitaciones\b", body):
        return body
    return (
        body.rstrip()
        + "\n\nLimitaciones\n"
        + "El histórico describe eventos anteriores y no garantiza resultados futuros."
    )
