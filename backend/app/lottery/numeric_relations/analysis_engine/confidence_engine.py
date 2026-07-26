"""Analytical confidence (structural backing) — NOT win probability."""

from __future__ import annotations

from app.lottery.numeric_relations.analysis_engine.schemas import RankedCandidate


def compute_analytical_confidence(
    candidate: RankedCandidate,
    *,
    ranked: list[RankedCandidate],
    observed_count: int,
) -> float:
    """
    Returns 0..100 structural backing score.

    Never present as probability of winning a draw.
    """
    comps = candidate.components
    score = 35.0

    score += min(20.0, comps.T1_SOURCE_SUPPORT * 10.0)
    score += min(20.0, comps.T2_CONFIRMATION_SUPPORT * 10.0)
    if comps.CROSS_TABLE_SUPPORT:
        score += 12.0
    score += min(8.0, comps.INDEPENDENT_PATH_SUPPORT * 3.0)
    score += min(5.0, max(0.0, observed_count - 1) * 2.0)

    if comps.HISTORICAL_EXACT_RATE:
        score += 5.0 * comps.HISTORICAL_EXACT_RATE

    # Gap vs second candidate
    if candidate.rank == 1 and len(ranked) >= 2:
        gap = candidate.total_score - ranked[1].total_score
        score += min(8.0, max(0.0, gap) / 5.0)
    elif candidate.rank == 1 and len(ranked) == 1:
        score += 6.0

    score -= min(15.0, comps.AMBIGUITY_PENALTY * 3.0)
    score -= min(10.0, comps.DERIVATION_DEPTH_PENALTY * 2.0)
    score -= min(8.0, comps.DUPLICATE_PATH_PENALTY)

    if candidate.classification == "VECINO_T2_DIRECTO":
        score = min(score, 55.0)
    if candidate.classification == "FAMILIA_T1":
        score = min(score, 50.0)
    if candidate.classification == "DERIVACION_RELEVANTE":
        score = min(score, 45.0)

    return round(max(0.0, min(100.0, score)), 1)


def confidence_label(value: float) -> str:
    return f"RESPALDO ESTRUCTURAL: {value:.1f}/100 (no es probabilidad de acierto)"
