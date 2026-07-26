"""Motor Validation Lab — explain-only reconstruction (does NOT modify the NR motor).

Reconstruye Tabla 1/2, compañeros, vecinos, cruces e intersecciones para un
conjunto de observaciones del mismo día y compara contra un "Fuerte" manual
opcional. Usa únicamente el catálogo oficial y relaciones derivadas.
"""

from __future__ import annotations

from datetime import date
from itertools import combinations
from typing import Any
from uuid import UUID

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION


def _companions(cat: TableCatalog, n: int) -> list[int]:
    return list(cat.get_table1_companions(int(n)))


def _neighbors(cat: TableCatalog, n: int, *, exclude_self: bool = True) -> list[int]:
    return list(cat.get_table2_neighbors(int(n), exclude_self=exclude_self))


def reconstruct_number(cat: TableCatalog, n: int) -> dict[str, Any]:
    n = int(n)
    t2 = cat.get_table2_code_for_number(n)
    return {
        "number": n,
        "motor_mother_code": n,
        "table1_code_of_number": cat.table1_number_to_code[n],
        "companions_tabla1": _companions(cat, n),
        "peers_same_table1_code_as_number": list(
            cat.table1_code_to_numbers.get(cat.table1_number_to_code[n], [])
        ),
        "table2_code": t2,
        "neighbors_tabla2": _neighbors(cat, n),
        "table2_group": list(cat.table2_code_to_numbers.get(t2, [])),
    }


def _hypotheses(cat: TableCatalog, obs: list[int], manual_fuerte: int | None) -> list[dict[str, Any]]:
    uniq = list(dict.fromkeys(int(x) for x in obs))
    out: list[dict[str, Any]] = []

    # A
    hits_a: set[int] = set()
    edges_a: list[dict[str, Any]] = []
    for a, b in combinations(uniq, 2):
        for left, right in ((a, b), (b, a)):
            inter = set(_companions(cat, left)) & set(_neighbors(cat, right))
            hits_a |= inter
            edges_a.append(
                {
                    "companions_of": left,
                    "neighbors_of": right,
                    "intersection": sorted(inter),
                }
            )
    out.append(
        {
            "id": "A",
            "name": "Intersección compañeros(a) ∩ vecinos(b)",
            "produced": sorted(hits_a),
            "edges": edges_a,
            "hit_manual": (manual_fuerte in hits_a) if manual_fuerte is not None else None,
        }
    )

    # F — forma del motor: candidato = compañero(N); confirmador = otro observado ∈ vecinos(candidato)
    hits_f: set[int] = set()
    detail_f: list[dict[str, Any]] = []
    for a in uniq:
        others = set(uniq) - {a}
        for cand in _companions(cat, a):
            conf = set(_neighbors(cat, cand)) & others
            if conf:
                hits_f.add(cand)
                detail_f.append(
                    {
                        "observed_N": a,
                        "candidate": cand,
                        "confirmers_from_other_observations": sorted(conf),
                    }
                )
    out.append(
        {
            "id": "F",
            "name": "Candidato T1 confirmado por otro observado (forma del motor oficial)",
            "produced": sorted(hits_f),
            "detail": detail_f,
            "hit_manual": (manual_fuerte in hits_f) if manual_fuerte is not None else None,
        }
    )

    # B neighbors ∩ neighbors
    hits_b: set[int] = set()
    for a, b in combinations(uniq, 2):
        hits_b |= set(_neighbors(cat, a)) & set(_neighbors(cat, b))
    out.append(
        {
            "id": "B",
            "name": "Intersección vecinos(a) ∩ vecinos(b)",
            "produced": sorted(hits_b),
            "hit_manual": (manual_fuerte in hits_b) if manual_fuerte is not None else None,
        }
    )

    # E / G — fuerte es vecino de algún observado
    hits_e: set[int] = set()
    for a in uniq:
        hits_e |= set(_neighbors(cat, a))
    out.append(
        {
            "id": "E",
            "name": "Vecinos T2 de cualquier observado",
            "produced": sorted(hits_e),
            "hit_manual": (manual_fuerte in hits_e) if manual_fuerte is not None else None,
        }
    )

    # D companions any
    hits_d: set[int] = set()
    for a in uniq:
        hits_d |= set(_companions(cat, a))
    out.append(
        {
            "id": "D",
            "name": "Compañeros T1 de cualquier observado",
            "produced": sorted(hits_d),
            "hit_manual": (manual_fuerte in hits_d) if manual_fuerte is not None else None,
        }
    )

    return out


def build_mathematical_ranking(hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ranking explicativo por peso de evidencia (no es el score del motor v1)."""
    weights = {"F": 5, "A": 4, "B": 2, "E": 1, "D": 1}
    scores: dict[int, float] = {}
    sources: dict[int, list[str]] = {}
    for h in hypotheses:
        w = weights.get(h["id"], 1)
        for n in h.get("produced") or []:
            scores[n] = scores.get(n, 0.0) + w
            sources.setdefault(n, []).append(h["id"])
    ranking = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [
        {"number": n, "evidence_weight": s, "hypotheses": sources[n]}
        for n, s in ranking
    ]


def run_validation_lab(
    *,
    observed: list[dict[str, Any]],
    manual_fuerte: int | None = None,
    as_of_date: date | None = None,
    catalog: TableCatalog | None = None,
) -> dict[str, Any]:
    """
    observed: [{lottery_name?, lottery_id?, number: int}, ...]
    """
    cat = catalog or build_catalog()
    nums = [int(o["number"]) for o in observed]
    if not nums:
        raise ValueError("Debe indicar al menos un número observado")
    for n in nums:
        if n < 1 or n > 100:
            raise ValueError(f"Número fuera de rango 1..100: {n}")

    per_number = {str(n): reconstruct_number(cat, n) for n in dict.fromkeys(nums)}
    if manual_fuerte is not None:
        per_number[str(int(manual_fuerte))] = reconstruct_number(cat, int(manual_fuerte))

    hyps = _hypotheses(cat, nums, manual_fuerte)
    ranking = build_mathematical_ranking(hyps)

    motor_shaped = next((h for h in hyps if h["id"] == "F"), None)
    motor_top = (motor_shaped or {}).get("produced") or []
    motor_result = motor_top[0] if len(motor_top) == 1 else motor_top

    coincidence: str | None = None
    if manual_fuerte is not None:
        if motor_shaped and motor_shaped.get("hit_manual") and len(motor_shaped.get("produced") or []) == 1:
            coincidence = "SI"
        elif motor_shaped and motor_shaped.get("hit_manual"):
            coincidence = "SI_CON_OTROS_CANDIDATOS"
        elif any(h.get("hit_manual") for h in hyps if h["id"] in ("A", "E")):
            coincidence = "PARCIAL_RELACION_ALTERNATIVA"
        else:
            coincidence = "NO"

    explanation = None
    if motor_shaped and manual_fuerte is not None and motor_shaped.get("hit_manual"):
        detail = [
            d for d in (motor_shaped.get("detail") or []) if d.get("candidate") == int(manual_fuerte)
        ]
        explanation = {
            "relation": "Número observado N → compañeros Tabla1 (candidatos) → "
            "cada candidato consulta vecinos Tabla2 → si un confirmador "
            "(otro número observado el mismo día) aparece en esos vecinos, "
            "solo el candidato de Tabla1 se fortalece.",
            "detail": detail,
            "methodology_version": METHODOLOGY_VERSION,
        }

    return {
        "lab": "Motor Validation Lab",
        "read_only": True,
        "modifies_motor": False,
        "methodology_version": METHODOLOGY_VERSION,
        "as_of_date": as_of_date.isoformat() if as_of_date else None,
        "observations": observed,
        "observed_numbers": nums,
        "manual_fuerte": manual_fuerte,
        "tables_per_number": per_number,
        "crosses_and_intersections": hyps,
        "mathematical_ranking": ranking,
        "motor_shaped_result": motor_result,
        "coincidence": coincidence,
        "explanation": explanation,
        "notes": [
            "Este laboratorio no altera Tablas ni el motor.",
            "El endpoint /analyze oficial opera sobre UN solo observed_number y ranking histórico; "
            "aquí se explica el cruce multi-observación del mismo día con la misma geometría T1×T2.",
        ],
    }
