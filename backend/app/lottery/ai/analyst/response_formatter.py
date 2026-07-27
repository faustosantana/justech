"""Response formatter — structured Analista IA answer sections."""

from __future__ import annotations

import re
from typing import Any


_SECTION_HEADERS = (
    "Conclusión",
    "Explicación",
    "Evidencias",
    "Histórico",
    "Comparación",
    "Observación del Analista",
    "Limitaciones",
)


def format_analyst_response(
    text: str,
    *,
    facts: dict[str, Any] | None = None,
    research: dict[str, Any] | None = None,
    force_structure: bool = True,
) -> str:
    """Ensure professional sectioned answer without inventing new facts."""
    body = (text or "").strip()
    if not body:
        body = "No encontré suficiente evidencia para responder con seguridad."

    # If already well structured, keep it
    has_conclusion = bool(re.search(r"(?im)^\s*conclusi[oó]n\b", body))
    if has_conclusion and not force_structure:
        return _ensure_limitations(body)

    facts = facts or {}
    research = research or {}

    # Try to extract a lead sentence as conclusion
    first = body.split("\n\n")[0].strip()
    rest = body[len(first) :].strip() if body.startswith(first) else body

    conclusion = first
    explanation = rest or first

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
        ("Conclusión", conclusion),
        ("Explicación", explanation if explanation != conclusion else None),
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
