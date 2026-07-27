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
from app.lottery.numeric_relations.analysis_engine.same_day_context import (
    find_same_day_cross_confirmations,
    same_day_context_from_dict,
)
from app.lottery.numeric_relations.analysis_engine.historical_relation_evidence import (
    analyze_historical_relations,
)
from app.lottery.numeric_relations.analysis_engine.signal_tracker import get_signal_store
from app.lottery.numeric_relations.analysis_engine.tiebreak_engine import (
    DEFAULT_PRACTICAL_THRESHOLD,
    apply_selected_tiebreak,
)


def run_complete_analysis(
    request: AnalysisRequest | dict[str, Any],
    *,
    catalog: TableCatalog | None = None,
    persist: bool = True,
    include_table2: bool | None = None,
    enable_tiebreak: bool = True,
    practical_tie_threshold: float = DEFAULT_PRACTICAL_THRESHOLD,
) -> CompleteAnalysisResult:
    stages: list[str] = []
    cat = catalog or build_catalog()
    raw = request if isinstance(request, dict) else None
    req = normalize_request(request)
    stages.append("normalized")

    analysis_id = new_id("an")
    # Seeds: primary observed number(s). Explicit confirmers from same_day_confirmers
    # or, in legacy multi-number requests without day context, all numbers stay mutual.
    seed_numbers = unique_observed(req.numbers)
    explicit_confirmers = unique_observed(list(req.same_day_confirmers or []))
    day_context_payload = None
    if raw and isinstance(raw.get("same_day_context"), dict):
        day_context_payload = raw.get("same_day_context")
    if raw and raw.get("day_context") and not day_context_payload:
        day_context_payload = raw.get("day_context")

    confirmer_numbers: list[int] | None = None
    same_day_meta: dict[int, dict[str, Any]] = {}
    if explicit_confirmers or day_context_payload:
        # Same-day / confirmer mode: seeds generate T1; confirmers only confirm via T2.
        confirmer_numbers = [
            n for n in explicit_confirmers if n not in seed_numbers
        ]
        if day_context_payload:
            # Metadata for UI/audit from all appearances; confirmers stay position-filtered.
            for app in day_context_payload.get("appearances") or []:
                try:
                    n = int(app.get("number"))
                except (TypeError, ValueError):
                    continue
                same_day_meta[n] = {
                    "lottery": app.get("lottery"),
                    "position": app.get("position"),
                    "draw_id": app.get("draw_id"),
                }
            for n in day_context_payload.get("confirmer_numbers") or []:
                try:
                    v = int(n)
                except (TypeError, ValueError):
                    continue
                if v not in seed_numbers and v not in confirmer_numbers:
                    confirmer_numbers.append(v)
        # Also treat numbers[1:] as confirmers when day mode is active (manual "with").
        if len(seed_numbers) > 1 and confirmer_numbers is not None:
            primary = seed_numbers[0]
            rest = seed_numbers[1:]
            seed_numbers = [primary]
            for n in rest:
                if n not in confirmer_numbers:
                    confirmer_numbers.append(n)

    observed = unique_observed(
        seed_numbers + (confirmer_numbers or [])
        if confirmer_numbers is not None
        else seed_numbers
    )
    date_s = req.date.isoformat() if req.date else None
    use_t2 = True if include_table2 is None else bool(include_table2)
    if isinstance(request, dict) and "include_table2" in request:
        use_t2 = bool(request["include_table2"])

    # --- FULL GRAPH (no candidate selection) ---
    graph = build_complete_relationship_graph(
        seed_numbers if confirmer_numbers is not None else observed,
        catalog=cat,
        derivation_depth=req.derivation_depth,
        include_table2=use_t2,
        date=date_s,
        position=",".join(req.positions),
        confirmer_numbers=confirmer_numbers,
        same_day_meta=same_day_meta or None,
    )
    stages.append("graph_built")

    same_day_cross = find_same_day_cross_confirmations(
        seed_numbers,
        confirmer_numbers or [],
        catalog=cat,
        day_context=same_day_context_from_dict(day_context_payload),
        date_s=date_s,
    )
    if same_day_cross:
        stages.append("same_day_cross_detected")

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

    if isinstance(request, dict) and "enable_tiebreak" in request:
        enable_tiebreak = bool(request["enable_tiebreak"])
    if isinstance(request, dict) and "practical_tie_threshold" in request:
        practical_tie_threshold = float(request["practical_tie_threshold"])

    tiebreak_decisions: list[dict[str, Any]] = []
    if enable_tiebreak:
        ranked, decisions = apply_selected_tiebreak(
            ranked,
            observed_numbers=list(seed_numbers),
            practical_threshold=practical_tie_threshold,
            enable=True,
        )
        tiebreak_decisions = [d.to_dict() for d in decisions]
        stages.append("tiebreak_applied")

    for c in ranked:
        c.analytical_confidence = compute_analytical_confidence(
            c, ranked=ranked, observed_count=len(seed_numbers)
        )
    stages.append("confidence_assigned")

    explanation = explain_analysis(
        observed=seed_numbers,
        ranked=ranked,
        level=req.explanation_level,
        same_day_cross=[e.to_dict() for e in same_day_cross],
    )
    stages.append("explanation_built")

    signals = []
    if req.create_signals and ranked:
        signals = create_experimental_signals(
            ranked,
            analysis_id=analysis_id,
            observed_numbers=seed_numbers,
            analysis_date=req.date,
            lotteries=req.lotteries,
            positions=req.positions,
            mode=req.mode,
            derivation_depth=req.derivation_depth,
        )
        stages.append("experimental_signals_created")

    # Multi-fuerte unresolved: surface first EMPATE as primary payload, keep peers in alternatives
    multi = [c for c in ranked if c.classification == "EMPATE_MULTI_FUERTE"]
    primary = next(
        (
            c
            for c in ranked
            if c.classification in {"FUERTE_PRINCIPAL", "FUERTE_T1_T2_MISMO_DIA"}
        ),
        None,
    )
    if primary is None and multi:
        primary = multi[0]
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
            "same_day_cross_support": primary.evidence.same_day_cross_support,
            "multi_fuerte_peers": [c.number for c in multi] if multi else [],
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
            "same_day_cross_support": primary.evidence.same_day_cross_support,
        }

    tiebreak_payload = {
        "enabled": enable_tiebreak,
        "practical_threshold": practical_tie_threshold,
        "decisions": tiebreak_decisions,
        "unresolved_multi": bool(multi),
        "multi_fuerte_numbers": [c.number for c in multi],
    }

    result = CompleteAnalysisResult(
        analysis_id=analysis_id,
        engine_version=ENGINE_VERSION,
        table_version=TABLE_VERSION,
        observed_numbers=seed_numbers,
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
            "Empates estructurales no resueltos se reportan como EMPATE_MULTI_FUERTE.",
            "El cruce del mismo día usa las posiciones configuradas (por defecto primera).",
            "El histórico describe comportamientos anteriores; no altera la prioridad de Tabla 1.",
        ],
        tiebreak=tiebreak_payload,
        same_day_context=day_context_payload,
        same_day_cross=[e.to_dict() for e in same_day_cross],
    )

    # Historical evidence layer (explanatory only — does not change ranking / T1 priority).
    historical_evidence = None
    hist_rows = None
    if raw and isinstance(raw.get("historical_draws"), list):
        hist_rows = raw.get("historical_draws")
    if hist_rows and primary is not None and seed_numbers:
        try:
            origin_x = int(seed_numbers[0])
            confirmer_y = None
            if confirmer_numbers:
                confirmer_y = int(confirmer_numbers[0])
            elif len(seed_numbers) > 1:
                confirmer_y = int(seed_numbers[1])
            elif primary.evidence.direct_confirmers:
                confirmer_y = int(primary.evidence.direct_confirmers[0])
            # Rival: strongest non-T1 neighbor if present (e.g. 07), else first alternative
            rival_meta = None
            for c in ranked:
                if c.number == primary.number:
                    continue
                if c.classification == "VECINO_T2_DIRECTO" or (
                    not c.evidence.table1_sources and c.evidence.direct_confirmers
                ):
                    rival_meta = {
                        "number": c.number,
                        "table1_sources": c.evidence.table1_sources,
                        "table2_confirmers": c.evidence.direct_confirmers,
                        "same_day_cross_support": c.evidence.same_day_cross_support,
                        "independent_routes": c.evidence.independent_path_count,
                    }
                    break
            if rival_meta is None and alternatives:
                a0 = next((c for c in ranked if c.number == alternatives[0]["number"]), None)
                if a0 is not None:
                    rival_meta = {
                        "number": a0.number,
                        "table1_sources": a0.evidence.table1_sources,
                        "table2_confirmers": a0.evidence.direct_confirmers,
                        "same_day_cross_support": a0.evidence.same_day_cross_support,
                        "independent_routes": a0.evidence.independent_path_count,
                    }
            lots = []
            positions_meta = []
            for cross in same_day_cross:
                if cross.companion_c == primary.number:
                    if cross.lottery_x:
                        lots.append(cross.lottery_x)
                    if cross.lottery_y:
                        lots.append(cross.lottery_y)
                    if cross.position_x:
                        positions_meta.append(cross.position_x)
                    if cross.position_y:
                        positions_meta.append(cross.position_y)
            historical_evidence = analyze_historical_relations(
                hist_rows,
                origin_x=origin_x,
                confirmer_y=confirmer_y,
                candidate_c=primary.number,
                alternatives=[a["number"] for a in alternatives[:8]],
                catalog=cat,
                period=(raw or {}).get("historical_period") or "all",
                positions=None,  # all positions by default
                primary_meta={
                    "table1_sources": primary.evidence.table1_sources,
                    "table2_confirmers": primary.evidence.direct_confirmers,
                    "same_day_cross_support": primary.evidence.same_day_cross_support,
                    "lotteries": lots,
                    "positions": positions_meta,
                    "independent_routes": primary.evidence.independent_path_count,
                },
                rival_meta=rival_meta,
            )
            stages.append("historical_evidence_built")
            result.stages_completed = stages
            result.historical_evidence = historical_evidence
            # Enrich explanation with historical narrative (no ranking change).
            narr = historical_evidence.get("narrative") or {}
            if isinstance(explanation, dict):
                explanation = {
                    **explanation,
                    "historical": narr,
                    "conclusion": narr.get("conclusion") or explanation.get("conclusion"),
                    "evidence_current": narr.get("evidence_current"),
                    "historical_behavior": narr.get("historical_behavior"),
                    "comparison": narr.get("comparison"),
                    "warning": narr.get("warning"),
                    "summary": " ".join(
                        p
                        for p in [
                            narr.get("conclusion"),
                            narr.get("historical_behavior"),
                            narr.get("comparison"),
                            narr.get("warning"),
                        ]
                        if p
                    )
                    or explanation.get("summary"),
                }
                result.explanation = explanation
        except Exception:
            # Historical layer must never break structural analysis.
            result.historical_evidence = {
                "error": "historical_layer_unavailable",
                "ranking_unchanged": True,
                "table1_priority": True,
            }

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
