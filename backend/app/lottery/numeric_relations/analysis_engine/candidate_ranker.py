"""Explainable candidate ranker with configurable weight profiles."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.schemas import (
    CandidateEvidence,
    Classification,
    RankProfile,
    RankedCandidate,
    ScoreComponents,
)
from app.lottery.numeric_relations.catalog import build_catalog


# Configurable weights — not claimed as predictive truth; backtest validates.
WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    RankProfile.STRICT.value: {
        "T1_SOURCE_SUPPORT": 25.0,
        "T2_CONFIRMATION_SUPPORT": 25.0,
        "CROSS_TABLE_SUPPORT": 20.0,
        "MULTIPLE_OBSERVED_SUPPORT": 8.0,
        "INDEPENDENT_PATH_SUPPORT": 10.0,
        "DIRECT_PATH_SUPPORT": 8.0,
        "MULTI_CONFIRMATION_SUPPORT": 10.0,
        "HISTORICAL_EXACT_RATE": 5.0,
        "HISTORICAL_D1_D3_RATE": 3.0,
        "HISTORICAL_D1_D7_RATE": 2.0,
        "FIRST_POSITION_SUPPORT": 2.0,
        "ANY_POSITION_SUPPORT": 1.0,
        "RECENT_PATTERN_SUPPORT": 1.0,
        "CROSS_LOTTERY_SUPPORT": 1.0,
        "CHAIN_CONTINUITY_SUPPORT": 1.0,
        "DERIVATION_DEPTH_PENALTY": -4.0,
        "AMBIGUITY_PENALTY": -6.0,
        "DUPLICATE_PATH_PENALTY": -3.0,
        "require_t1": 1.0,
        "require_t2": 1.0,
    },
    RankProfile.MANUAL_RECONSTRUCTED.value: {
        "T1_SOURCE_SUPPORT": 30.0,
        "T2_CONFIRMATION_SUPPORT": 28.0,
        "CROSS_TABLE_SUPPORT": 22.0,
        "MULTIPLE_OBSERVED_SUPPORT": 10.0,
        "INDEPENDENT_PATH_SUPPORT": 12.0,
        "DIRECT_PATH_SUPPORT": 10.0,
        "MULTI_CONFIRMATION_SUPPORT": 14.0,
        "HISTORICAL_EXACT_RATE": 4.0,
        "HISTORICAL_D1_D3_RATE": 2.0,
        "HISTORICAL_D1_D7_RATE": 1.0,
        "FIRST_POSITION_SUPPORT": 2.0,
        "ANY_POSITION_SUPPORT": 1.0,
        "RECENT_PATTERN_SUPPORT": 1.0,
        "CROSS_LOTTERY_SUPPORT": 1.0,
        "CHAIN_CONTINUITY_SUPPORT": 1.0,
        "DERIVATION_DEPTH_PENALTY": -5.0,
        "AMBIGUITY_PENALTY": -4.0,
        "DUPLICATE_PATH_PENALTY": -2.0,
        "require_t1": 1.0,
        "require_t2": 1.0,
    },
    RankProfile.BROAD.value: {
        "T1_SOURCE_SUPPORT": 18.0,
        "T2_CONFIRMATION_SUPPORT": 14.0,
        "CROSS_TABLE_SUPPORT": 12.0,
        "MULTIPLE_OBSERVED_SUPPORT": 8.0,
        "INDEPENDENT_PATH_SUPPORT": 8.0,
        "DIRECT_PATH_SUPPORT": 6.0,
        "MULTI_CONFIRMATION_SUPPORT": 6.0,
        "HISTORICAL_EXACT_RATE": 8.0,
        "HISTORICAL_D1_D3_RATE": 6.0,
        "HISTORICAL_D1_D7_RATE": 4.0,
        "FIRST_POSITION_SUPPORT": 3.0,
        "ANY_POSITION_SUPPORT": 2.0,
        "RECENT_PATTERN_SUPPORT": 3.0,
        "CROSS_LOTTERY_SUPPORT": 2.0,
        "CHAIN_CONTINUITY_SUPPORT": 2.0,
        "DERIVATION_DEPTH_PENALTY": -2.0,
        "AMBIGUITY_PENALTY": -2.0,
        "DUPLICATE_PATH_PENALTY": -1.0,
        "require_t1": 0.0,
        "require_t2": 0.0,
    },
    RankProfile.EXPERIMENTAL.value: {
        "T1_SOURCE_SUPPORT": 20.0,
        "T2_CONFIRMATION_SUPPORT": 20.0,
        "CROSS_TABLE_SUPPORT": 15.0,
        "MULTIPLE_OBSERVED_SUPPORT": 10.0,
        "INDEPENDENT_PATH_SUPPORT": 15.0,
        "DIRECT_PATH_SUPPORT": 10.0,
        "MULTI_CONFIRMATION_SUPPORT": 10.0,
        "HISTORICAL_EXACT_RATE": 10.0,
        "HISTORICAL_D1_D3_RATE": 8.0,
        "HISTORICAL_D1_D7_RATE": 5.0,
        "FIRST_POSITION_SUPPORT": 4.0,
        "ANY_POSITION_SUPPORT": 3.0,
        "RECENT_PATTERN_SUPPORT": 4.0,
        "CROSS_LOTTERY_SUPPORT": 3.0,
        "CHAIN_CONTINUITY_SUPPORT": 3.0,
        "DERIVATION_DEPTH_PENALTY": -3.0,
        "AMBIGUITY_PENALTY": -3.0,
        "DUPLICATE_PATH_PENALTY": -2.0,
        "require_t1": 0.0,
        "require_t2": 0.0,
    },
}

# Calibration lab aliases (Phase 2) — still deterministic ranking, not ML.
WEIGHT_PROFILES["conservador"] = {
    **WEIGHT_PROFILES[RankProfile.STRICT.value],
    "DERIVATION_DEPTH_PENALTY": -8.0,
    "AMBIGUITY_PENALTY": -10.0,
    "HISTORICAL_EXACT_RATE": 2.0,
}
WEIGHT_PROFILES["balanceado"] = dict(WEIGHT_PROFILES[RankProfile.MANUAL_RECONSTRUCTED.value])
WEIGHT_PROFILES["agresivo"] = {
    **WEIGHT_PROFILES[RankProfile.BROAD.value],
    "HISTORICAL_EXACT_RATE": 12.0,
    "HISTORICAL_D1_D3_RATE": 10.0,
    "DERIVATION_DEPTH_PENALTY": -1.0,
    "require_t1": 0.0,
    "require_t2": 0.0,
}
WEIGHT_PROFILES["socio"] = dict(WEIGHT_PROFILES[RankProfile.MANUAL_RECONSTRUCTED.value])
WEIGHT_PROFILES["perfil_socio"] = WEIGHT_PROFILES["socio"]


def resolve_profile(profile: str | None) -> str:
    if not profile:
        return RankProfile.MANUAL_RECONSTRUCTED.value
    p = str(profile).strip().lower()
    aliases = {
        "strict": RankProfile.STRICT.value,
        "estricto": RankProfile.STRICT.value,
        "conservador": "conservador",
        "balanceado": "balanceado",
        "agresivo": "agresivo",
        "socio": "socio",
        "perfil_socio": "socio",
        "manual": RankProfile.MANUAL_RECONSTRUCTED.value,
        "manual_reconstruido": RankProfile.MANUAL_RECONSTRUCTED.value,
        "amplio": RankProfile.BROAD.value,
        "broad": RankProfile.BROAD.value,
        "experimental": RankProfile.EXPERIMENTAL.value,
    }
    return aliases.get(p, p)


def _rate(hits: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, hits / total))


def compute_components(ev: CandidateEvidence, *, catalog=None) -> ScoreComponents:
    hist_total = max(1, int(ev.historical_activations or 0))
    d1d3 = ev.d1_hits + ev.d2_hits + ev.d3_hits
    d1d7 = d1d3 + ev.d4_hits + ev.d5_hits + ev.d6_hits + ev.d7_hits
    min_der_depth = 0
    if ev.derivation_paths and not (ev.table1_sources and ev.direct_confirmers):
        depths = [int(p.get("depth", 2)) for p in ev.derivation_paths]
        min_der_depth = min(depths) if depths else 2

    # Specificity for direct T2: smaller neighbor groups weigh more
    t2_specificity = 0.0
    if catalog is not None and not ev.table1_sources and ev.table2_sources:
        try:
            code = catalog.get_table2_code_for_number(ev.candidate_number)
            group_size = len(catalog.table2_code_to_numbers.get(code, []) or [])
            if group_size > 0:
                t2_specificity = 10.0 / float(group_size)
        except Exception:
            t2_specificity = 0.0

    return ScoreComponents(
        T1_SOURCE_SUPPORT=float(len(ev.table1_sources)),
        T2_CONFIRMATION_SUPPORT=float(len(ev.direct_confirmers)),
        CROSS_TABLE_SUPPORT=1.0 if ev.cross_table_support else 0.0,
        MULTIPLE_OBSERVED_SUPPORT=1.0 if ev.multi_source_support else 0.0,
        INDEPENDENT_PATH_SUPPORT=float(ev.independent_path_count) + t2_specificity,
        DIRECT_PATH_SUPPORT=float(ev.direct_path_count),
        MULTI_CONFIRMATION_SUPPORT=float(max(0, len(ev.direct_confirmers) - 1)),
        HISTORICAL_EXACT_RATE=_rate(ev.historical_exact_hits, hist_total)
        if ev.historical_activations
        else 0.0,
        HISTORICAL_D1_D3_RATE=_rate(d1d3, hist_total) if ev.historical_activations else 0.0,
        HISTORICAL_D1_D7_RATE=_rate(d1d7, hist_total) if ev.historical_activations else 0.0,
        FIRST_POSITION_SUPPORT=float(ev.historical_first_position_hits),
        ANY_POSITION_SUPPORT=float(ev.historical_any_position_hits),
        RECENT_PATTERN_SUPPORT=float(len(ev.recent_equivalent_cases)),
        CROSS_LOTTERY_SUPPORT=float(max(0, len(ev.lottery_distribution) - 1)),
        CHAIN_CONTINUITY_SUPPORT=0.0,
        DERIVATION_DEPTH_PENALTY=float(min_der_depth),
        AMBIGUITY_PENALTY=float(ev.ambiguity_score),
        DUPLICATE_PATH_PENALTY=float(ev.same_source_repetitions),
    )


def score_total(components: ScoreComponents, weights: dict[str, float]) -> float:
    total = 0.0
    data = components.to_dict()
    for k, v in data.items():
        w = float(weights.get(k, 0.0))
        total += w * float(v)
    return total


def _finalize_classification(
    provisional: str,
    components: ScoreComponents,
    rank: int,
    profile: str,
    weights: dict[str, float],
) -> tuple[str, str]:
    require_t1 = bool(weights.get("require_t1"))
    require_t2 = bool(weights.get("require_t2"))

    if provisional == Classification.VECINO_T2_DIRECTO.value:
        return (
            Classification.VECINO_T2_DIRECTO.value,
            "Clasificado como VECINO_T2_DIRECTO: no se eleva a fuerte oficial.",
        )

    if provisional == Classification.DERIVACION_RELEVANTE.value:
        return provisional, "Derivación relevante; no fuerte principal en perfil estricto."

    if provisional == Classification.FAMILIA_T1.value:
        if profile == RankProfile.BROAD.value:
            return provisional, "Familia T1 admitida en perfil amplio."
        return provisional, "Solo familia T1; insuficiente para fuerte en perfil actual."

    has_t1 = components.T1_SOURCE_SUPPORT > 0
    has_t2 = components.T2_CONFIRMATION_SUPPORT > 0
    if require_t1 and not has_t1:
        return (
            Classification.SIN_EVIDENCIA_SUFICIENTE.value,
            "Perfil exige relación Tabla 1.",
        )
    if require_t2 and not has_t2:
        return (
            Classification.CANDIDATO_PARCIAL.value,
            "Perfil exige confirmación Tabla 2.",
        )

    if has_t1 and has_t2:
        if rank == 1:
            return (
                Classification.FUERTE_PRINCIPAL.value,
                "Mayor respaldo estructural tras análisis completo T1×T2.",
            )
        return (
            Classification.FUERTE_SECUNDARIO.value,
            "Confirmado T1×T2 pero por debajo del principal en ranking.",
        )

    return provisional, "Clasificación provisional sin elevación a fuerte."


def rank_all_candidates(
    discovered: list[dict[str, Any]],
    *,
    profile: str = RankProfile.MANUAL_RECONSTRUCTED.value,
) -> list[RankedCandidate]:
    profile = resolve_profile(profile)
    weights = WEIGHT_PROFILES.get(profile) or WEIGHT_PROFILES[RankProfile.MANUAL_RECONSTRUCTED.value]
    catalog = build_catalog()

    has_official_shape = any(
        bool(item["evidence"].cross_table_support)
        for item in discovered
    )

    scored: list[RankedCandidate] = []
    for item in discovered:
        ev: CandidateEvidence = item["evidence"]
        comps = compute_components(ev, catalog=catalog)
        total = score_total(comps, weights)
        prov = item["provisional_classification"]

        # Prefer confirmed T1×T2 over everything else.
        # When no official cross-table hit exists, surface VECINO_T2_DIRECTO
        # above bare FAMILIA_T1 (manual reconstruction of 41+62→75).
        if profile in {
            RankProfile.STRICT.value,
            RankProfile.MANUAL_RECONSTRUCTED.value,
            "conservador",
            "balanceado",
            "socio",
        }:
            if prov == Classification.VECINO_T2_DIRECTO.value:
                total -= 50.0 if has_official_shape else -15.0
            elif prov == Classification.FAMILIA_T1.value:
                total -= 40.0
            elif prov == Classification.DERIVACION_RELEVANTE.value:
                total -= 45.0
            elif prov == Classification.CANDIDATO_PARCIAL.value and not ev.cross_table_support:
                total -= 20.0

        positives: list[str] = list(item.get("reasons") or [])
        penalties: list[str] = []
        if comps.DERIVATION_DEPTH_PENALTY:
            penalties.append(f"Penalización por profundidad de derivación={comps.DERIVATION_DEPTH_PENALTY}")
        if comps.AMBIGUITY_PENALTY:
            penalties.append(f"Penalización por ambigüedad={comps.AMBIGUITY_PENALTY}")
        if comps.DUPLICATE_PATH_PENALTY:
            penalties.append(f"Penalización por rutas duplicadas={comps.DUPLICATE_PATH_PENALTY}")

        scored.append(
            RankedCandidate(
                number=int(item["number"]),
                classification=item["provisional_classification"],
                classification_reason="; ".join(positives),
                total_score=total,
                components=comps,
                analytical_confidence=0.0,
                evidence=ev,
                positive_evidence=positives,
                penalties=penalties,
            )
        )

    def _tier(c: RankedCandidate) -> int:
        if c.components.CROSS_TABLE_SUPPORT > 0:
            return 0
        if c.classification == Classification.VECINO_T2_DIRECTO.value or (
            c.evidence.table2_sources and not c.evidence.table1_sources
        ):
            return 1 if not has_official_shape else 3
        if c.evidence.table1_sources and c.evidence.direct_confirmers:
            return 0
        return 2

    scored.sort(
        key=lambda c: (
            _tier(c),
            -c.total_score,
            -c.components.CROSS_TABLE_SUPPORT,
            -c.components.T2_CONFIRMATION_SUPPORT,
            -c.components.T1_SOURCE_SUPPORT,
            # No lexicographic number bias — real ties are handled by TiebreakEngine.
        )
    )

    for i, c in enumerate(scored, start=1):
        c.rank = i
        if i < len(scored):
            c.gap_to_next = round(c.total_score - scored[i].total_score, 4)
        else:
            c.gap_to_next = None
        final_cls, reason = _finalize_classification(
            c.classification, c.components, i, profile, weights
        )
        c.classification = final_cls
        c.classification_reason = reason

    return scored
