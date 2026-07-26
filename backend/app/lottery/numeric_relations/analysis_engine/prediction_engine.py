"""Experimental prediction engine — labels predictions as experimental."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.lottery.numeric_relations.analysis_engine.schemas import (
    ENGINE_VERSION,
    ExperimentalSignal,
    RankedCandidate,
    SignalStatus,
    new_id,
)


EXPERIMENTAL_DISCLAIMER = (
    "PREDICCIÓN EXPERIMENTAL BASADA EN RELACIONES. "
    "No constituye recomendación de apuesta ni probabilidad de ganar."
)


def create_experimental_signals(
    ranked: list[RankedCandidate],
    *,
    analysis_id: str,
    observed_numbers: list[int],
    analysis_date: date | None,
    lotteries: list[str],
    positions: list[str],
    mode: str,
    derivation_depth: int,
    max_signals: int = 5,
) -> list[ExperimentalSignal]:
    signals: list[ExperimentalSignal] = []
    alternatives = [c.number for c in ranked]
    date_s = analysis_date.isoformat() if analysis_date else None

    for c in ranked[:max_signals]:
        if c.classification in {"SIN_EVIDENCIA_SUFICIENTE"}:
            continue
        signals.append(
            ExperimentalSignal(
                signal_id=new_id("sig"),
                number=c.number,
                classification=c.classification,
                score=c.total_score,
                analytical_confidence=c.analytical_confidence,
                supporting_evidence={
                    "table1_sources": c.evidence.table1_sources,
                    "table2_confirmers": c.evidence.direct_confirmers,
                    "independent_paths": c.evidence.independent_path_count,
                    "cross_table_support": c.evidence.cross_table_support,
                    "classification_reason": c.classification_reason,
                    "disclaimer": EXPERIMENTAL_DISCLAIMER,
                },
                observed_numbers=list(observed_numbers),
                analysis_date=date_s or "",
                analysis_id=analysis_id,
                lotteries=list(lotteries),
                positions=list(positions),
                mode=mode,
                derivation_depth=derivation_depth,
                estimated_window=["D+1", "D+2", "D+3", "D+4", "D+5", "D+6", "D+7"],
                historical_profile={
                    "historical_activations": c.evidence.historical_activations,
                    "historical_exact_hits": c.evidence.historical_exact_hits,
                    "d1_hits": c.evidence.d1_hits,
                    "d2_hits": c.evidence.d2_hits,
                    "d3_hits": c.evidence.d3_hits,
                    "d4_hits": c.evidence.d4_hits,
                    "d5_hits": c.evidence.d5_hits,
                    "d6_hits": c.evidence.d6_hits,
                    "d7_hits": c.evidence.d7_hits,
                },
                alternatives=[n for n in alternatives if n != c.number],
                engine_version=ENGINE_VERSION,
                status=SignalStatus.ACTIVO.value,
                experimental=True,
            )
        )
    return signals


def prediction_summary(signals: list[ExperimentalSignal]) -> dict[str, Any]:
    return {
        "experimental": True,
        "disclaimer": EXPERIMENTAL_DISCLAIMER,
        "count": len(signals),
        "active": sum(1 for s in signals if s.status == SignalStatus.ACTIVO.value),
        "signals": [s.to_dict() for s in signals],
    }
