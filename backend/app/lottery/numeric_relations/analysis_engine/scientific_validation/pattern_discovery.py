"""Pattern discovery — only patterns backed by validation data (no invented rules)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def discover_patterns(
    validation_rows: list[dict[str, Any]],
    *,
    min_support: int = 8,
) -> dict[str, Any]:
    """
    Frequency mining over successful methodology matches.
    Does NOT invent rules — only reports counts above min_support.
    """
    matches = [r for r in validation_rows if r.get("methodology_match")]
    pair_to_fuerte: Counter[tuple[int, int, int]] = Counter()
    origin_fuerte: Counter[tuple[int, int]] = Counter()
    lottery_pair: Counter[tuple[str, str]] = Counter()
    day_offset: Counter[int] = Counter()
    position_pair: Counter[tuple[int, int]] = Counter()
    multi_confirmer: Counter[str] = Counter()

    for r in matches:
        obs = sorted(r.get("observed_numbers") or [])
        fuerte = int(r["historical_fuerte"])
        if len(obs) >= 2:
            pair_to_fuerte[(obs[0], obs[1], fuerte)] += 1
            origin_fuerte[(obs[0], fuerte)] += 1
        lottery_pair[
            (str(r.get("origin_lottery") or "?"), str(r.get("confirmer_lottery") or "?"))
        ] += 1
        position_pair[
            (int(r.get("origin_position") or 1), int(r.get("confirmer_position") or 1))
        ] += 1
        off = r.get("first_day_offset")
        if off is not None and 1 <= int(off) <= 7:
            day_offset[int(off)] += 1
        ev = r.get("evidence_summary") or {}
        n_conf = len(ev.get("table2_confirmers") or [])
        multi_confirmer[f"confirmers={n_conf}"] += 1

    def top_supported(counter: Counter, n: int = 30) -> list[dict[str, Any]]:
        out = []
        for key, cnt in counter.most_common(200):
            if cnt < min_support:
                continue
            out.append({"key": key if not isinstance(key, tuple) else list(key), "count": cnt})
            if len(out) >= n:
                break
        return out

    # Consistency: for each (o1,o2) how often same fuerte
    combo_map: dict[tuple[int, int], Counter[int]] = defaultdict(Counter)
    for (a, b, f), cnt in pair_to_fuerte.items():
        combo_map[(a, b)][f] += cnt
    stable_combos = []
    for (a, b), c in combo_map.items():
        total = sum(c.values())
        if total < min_support:
            continue
        top_f, top_n = c.most_common(1)[0]
        stable_combos.append(
            {
                "observed": [a, b],
                "dominant_fuerte": top_f,
                "dominant_count": top_n,
                "total": total,
                "consistency": round(top_n / total, 4),
            }
        )
    stable_combos.sort(key=lambda x: (-x["consistency"], -x["total"]))

    return {
        "min_support": min_support,
        "n_match_rows_used": len(matches),
        "frequent_origin_fuerte": top_supported(origin_fuerte),
        "frequent_observed_pair_fuerte": top_supported(pair_to_fuerte),
        "stable_observed_combos": stable_combos[:40],
        "lottery_pairs": top_supported(lottery_pair),
        "position_pairs": top_supported(position_pair),
        "temporal_window_D_plus": dict(sorted(day_offset.items())),
        "confirmer_cardinality": dict(multi_confirmer),
        "hypothesis_only": [
            {
                "id": "H_PENDING_SAME_DAY_MULTI_FUERTE",
                "statement": "Días con múltiples fuertes oficiales pueden requerir regla de selección parcial (notebook del socio).",
                "status": "pendiente_de_validacion",
                "evidence_in_this_run": "no inventada — ver analyst_workflow_reconstruction previa",
            },
            {
                "id": "H_PENDING_DIRECT_T2_POLICY",
                "statement": "Cuándo elevar o aislar VECINO_T2_DIRECTO frente a oficiales sigue abierto.",
                "status": "hipotesis",
            },
        ],
        "disclaimer": "Solo patrones con soporte empírico ≥ min_support. No son reglas nuevas del motor.",
    }
