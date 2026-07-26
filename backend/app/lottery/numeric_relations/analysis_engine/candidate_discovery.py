"""Candidate discovery — ONLY after complete graph + evidence collection."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.relationship_graph import RelationshipGraph
from app.lottery.numeric_relations.analysis_engine.schemas import (
    CandidateEvidence,
    Classification,
)


def discover_candidates_after_full_analysis(
    evidence_by_dest: dict[int, CandidateEvidence],
    graph: RelationshipGraph,
    *,
    observed_numbers: list[int] | None = None,
) -> list[dict[str, Any]]:
    """
    Discover candidates only after the relationship graph is complete.

    A number becomes a candidate when it has structural evidence; it does NOT
    automatically become FUERTE_PRINCIPAL.
    """
    if not graph.complete:
        raise RuntimeError(
            "NO_EARLY_CANDIDATE_SELECTION: discover_candidates_after_full_analysis "
            "requires a completed relationship graph"
        )

    observed = set(observed_numbers or graph.observed_numbers)
    discovered: list[dict[str, Any]] = []

    # Peer ambiguity: how many destinations share similar support shape
    cross_table_dests = [
        n
        for n, ev in evidence_by_dest.items()
        if n not in observed and ev.cross_table_support
    ]

    for number, ev in sorted(evidence_by_dest.items()):
        if number in observed:
            # Observed numbers are inputs, not prediction candidates by default
            continue

        reasons: list[str] = []
        provisional = Classification.SIN_EVIDENCIA_SUFICIENTE.value

        has_t1 = bool(ev.table1_sources)
        has_t2_conf = bool(ev.direct_confirmers)
        has_direct_t2 = bool(
            ev.table2_sources
            and not has_t1
            and any(
                fp.endswith("|T2_NEIGHBOR|0") or "|T2_NEIGHBOR|0" in fp
                for fp in ev.path_fingerprints
            )
        )
        # More precise direct T2: some observed has T2_NEIGHBOR edge to this number
        has_direct_t2 = any(
            e.relation_type == "T2_NEIGHBOR"
            and int(e.target.split(":")[1]) == number
            and e.depth == 0
            and e.observed_origin in observed
            for e in graph.edges
        ) and not has_t1

        if has_t1 and has_t2_conf:
            provisional = Classification.CANDIDATO_CONFIRMADO.value
            reasons.append(
                "Relación Tabla 1 desde entrada(s) observada(s) más confirmación Tabla 2"
            )
        elif has_t1 and ev.multi_source_support:
            provisional = Classification.CANDIDATO_PARCIAL.value
            reasons.append("Apoyo Tabla 1 con múltiples fuentes observadas")
        elif has_t1:
            provisional = Classification.FAMILIA_T1.value
            reasons.append("Aparece como compañero/destino de Tabla 1 sin confirmación T2")
        elif has_direct_t2:
            provisional = Classification.VECINO_T2_DIRECTO.value
            reasons.append(
                "Señal directa de vecino Tabla 2; no es fuerte oficial T1×T2"
            )
        elif ev.derivation_paths:
            provisional = Classification.DERIVACION_RELEVANTE.value
            reasons.append("Destino alcanzado solo por derivación")
        else:
            reasons.append("Evidencia insuficiente para candidatura operativa")

        if ev.independent_path_count >= 2:
            reasons.append("Al menos dos rutas independientes")
        if ev.cross_table_support:
            reasons.append("Apoyo cruzado Tabla 1 + Tabla 2")

        ev.ambiguity_score = float(max(0, len(cross_table_dests) - 1)) if (
            number in cross_table_dests
        ) else float(len(cross_table_dests)) * 0.0

        if provisional == Classification.SIN_EVIDENCIA_SUFICIENTE.value:
            continue

        discovered.append(
            {
                "number": number,
                "provisional_classification": provisional,
                "reasons": reasons,
                "evidence": ev,
            }
        )

    return discovered
