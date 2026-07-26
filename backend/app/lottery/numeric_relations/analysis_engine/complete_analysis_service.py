"""Complete Analysis Engine orchestrator.

Order (mandatory):
  normalize → build graph → derivations → evidence → discover → rank → confidence
Never select a fuerte before the graph is complete.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.analysis_engine.candidate_discovery import (
    discover_candidates_after_full_analysis,
)
from app.lottery.numeric_relations.analysis_engine.candidate_ranker import rank_all_candidates
from app.lottery.numeric_relations.analysis_engine.confidence_engine import (
    compute_analytical_confidence,
)
from app.lottery.numeric_relations.analysis_engine.derivation_engine import apply_derivations
from app.lottery.numeric_relations.analysis_engine.evidence_collector import collect_all_evidence
from app.lottery.numeric_relations.analysis_engine.explanation_engine import explain_analysis
from app.lottery.numeric_relations.analysis_engine.input_normalizer import (
    normalize_request,
    unique_observed,
)
from app.lottery.numeric_relations.analysis_engine.prediction_engine import (
    create_experimental_signals,
)
from app.lottery.numeric_relations.analysis_engine.relationship_graph import (
    build_complete_relationship_graph,
)
from app.lottery.numeric_relations.analysis_engine.schemas import (
    ENGINE_VERSION,
    TABLE_VERSION,
    AnalysisRequest,
    CompleteAnalysisResult,
    new_id,
)
from app.lottery.numeric_relations.analysis_engine.signal_tracker import get_signal_store


def run_complete_analysis(
    request: AnalysisRequest | dict[str, Any],
    *,
    catalog: TableCatalog | None = None,
    persist: bool = True,
) -> CompleteAnalysisResult:
    stages: list[str] = []
    cat = catalog or build_catalog()
    req = normalize_request(request)
    stages.append("normalized")

    analysis_id = new_id("an")
    observed = unique_observed(req.numbers)
    date_s = req.date.isoformat() if req.date else None

    # --- FULL GRAPH (no candidate selection) ---
    graph = build_complete_relationship_graph(
        observed,
        catalog=cat,
        derivation_depth=req.derivation_depth,
        date=date_s,
        position=",".join(req.positions),
    )
    stages.append("graph_built")

    derivations = apply_derivations(
        graph, catalog=cat, max_depth=req.derivation_depth
    )
    if not graph.complete:
        raise RuntimeError("graph must be marked complete after derivations")
    stages.append("graph_complete")
    stages.append("derivations_applied")

    # --- EVIDENCE (still no selection) ---
    evidence = collect_all_evidence(
        graph, catalog=cat, derivation_paths=derivations
    )
    stages.append("evidence_collected")

    # --- DISCOVER only after complete analysis ---
    discovered = discover_candidates_after_full_analysis(
        evidence, graph, observed_numbers=observed
    )
    stages.append("candidates_discovered")

    ranked = rank_all_candidates(discovered, profile=req.mode)
    stages.append("candidates_ranked")

    for c in ranked:
        c.analytical_confidence = compute_analytical_confidence(
            c, ranked=ranked, observed_count=len(observed)
        )
    stages.append("confidence_assigned")

    explanation = explain_analysis(
        observed=observed, ranked=ranked, level=req.explanation_level
    )
    stages.append("explanation_built")

    signals = []
    if req.create_signals and ranked:
        signals = create_experimental_signals(
            ranked,
            analysis_id=analysis_id,
            observed_numbers=observed,
            analysis_date=req.date,
            lotteries=req.lotteries,
            positions=req.positions,
            mode=req.mode,
            derivation_depth=req.derivation_depth,
        )
        stages.append("experimental_signals_created")

    primary = next(
        (c for c in ranked if c.classification == "FUERTE_PRINCIPAL"),
        None,
    )
    # Broad/experimental / direct-T2 reconstructions may surface top ranked
    # even when no official FUERTE_PRINCIPAL exists (e.g. 41+62→75).
    if primary is None and ranked:
        for pref in (
            "FUERTE_SECUNDARIO",
            "CANDIDATO_CONFIRMADO",
            "VECINO_T2_DIRECTO",
        ):
            hit = next((c for c in ranked if c.classification == pref), None)
            if hit is not None:
                primary = hit
                break
        if primary is None:
            primary = ranked[0]

    primary_payload = None
    if primary is not None:
        primary_payload = {
            "number": primary.number,
            "classification": primary.classification,
            "analytical_confidence": primary.analytical_confidence,
            "score": primary.total_score,
            "reason": primary.classification_reason,
            "table1_sources": primary.evidence.table1_sources,
            "table2_confirmers": primary.evidence.direct_confirmers,
        }

    alternatives = [
        {
            "number": c.number,
            "classification": c.classification,
            "analytical_confidence": c.analytical_confidence,
            "score": c.total_score,
        }
        for c in ranked
        if primary is None or c.number != primary.number
    ]

    evidence_summary: dict[str, Any] = {}
    if primary is not None:
        evidence_summary = {
            "table1_sources": primary.evidence.table1_sources,
            "table2_confirmers": primary.evidence.direct_confirmers,
            "independent_paths": primary.evidence.independent_path_count,
            "cross_table_support": primary.evidence.cross_table_support,
            "multi_source_support": primary.evidence.multi_source_support,
        }

    result = CompleteAnalysisResult(
        analysis_id=analysis_id,
        engine_version=ENGINE_VERSION,
        table_version=TABLE_VERSION,
        observed_numbers=observed,
        analysis_date=date_s,
        positions=list(req.positions),
        mode=req.mode,
        derivation_depth=req.derivation_depth,
        stages_completed=stages,
        graph_complete_before_discovery=("graph_complete" in stages)
        and stages.index("graph_complete") < stages.index("candidates_discovered"),
        primary_signal=primary_payload,
        alternatives=alternatives,
        ranked_candidates=[c.to_dict() for c in ranked],
        evidence_summary=evidence_summary,
        graph=graph.to_dict(),
        derivations=[p.to_dict() for p in derivations[:200]],
        signals=[s.to_dict() for s in signals],
        explanation=explanation,
        experimental=True,
        limitations=[
            "Las predicciones son experimentales basadas en relaciones.",
            "La confianza analítica no es probabilidad de acierto.",
            "No se recomienda apostar con base en este análisis.",
            "Los pesos del ranking son configurables y deben validarse con backtest.",
        ],
    )

    if persist:
        store = get_signal_store()
        store.save_analysis(analysis_id, result.to_dict())
        if signals:
            store.register_signals(signals, open_cases=True)

    return result


# Thin aliases expected by package layout
def case_engine_open_from_analysis(result: CompleteAnalysisResult) -> list[dict[str, Any]]:
    store = get_signal_store()
    cases = [
        c.to_dict()
        for c in store.cases.values()
        if c.analysis_id == result.analysis_id
    ]
    return cases


def chain_timeline(chain_id: str | None = None) -> dict[str, Any]:
    store = get_signal_store()
    cid = chain_id or store.active_chain_id
    if not cid or cid not in store.chains:
        return {"chain_id": cid, "timeline": []}
    return store.chains[cid].to_dict()
