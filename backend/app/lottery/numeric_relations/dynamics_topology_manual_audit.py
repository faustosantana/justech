"""Dynamics, topology and manual-rules audit — read-only PRE-J11A.

Does not modify motor, Tabla 1/2, draws, or Production.
Does not use random baselines.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import uuid4

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.deep_mathematical_audit import (
    position_in_group,
    t1_candidates_from_observed,
    t1_group_ordered,
    t2_group_ordered,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION
from app.lottery.numeric_relations.historical_manual_audit import (
    ObservedNumber,
    strengthen_official,
)

RULE_CLASSES = (
    "FUERTE_OFICIAL_UNICO",
    "FUERTE_OFICIAL_ENTRE_VARIOS",
    "VECINO_T2_DIRECTO",
    "RELACION_INDIRECTA",
    "REGLA_MANUAL_NO_DOCUMENTADA",
    "POSIBLE_ERROR_DE_TRANSCRIPCION",
    "SIN_RELACION_REPRODUCIBLE",
)


def new_audit_id() -> str:
    return str(uuid4())


def pct(a: int, b: int) -> float:
    return round(100.0 * a / b, 2) if b else 0.0


def obs_list(nums: list[int], d: date | None = None) -> list[ObservedNumber]:
    d = d or date(2020, 1, 1)
    out = []
    for i, n in enumerate(nums):
        out.append(
            ObservedNumber(
                lottery_id=f"L{i}",
                lottery_name=f"L{i}",
                draw_id=f"D{i}",
                draw_date=d,
                draw_time=None,
                position=1,
                position_label="1",
                number=int(n),
                source_reference=None,
            )
        )
    return out


@dataclass
class ManualCaseSpec:
    case_id: str
    observed: list[int]
    manual_fuerte: int
    notes: str
    whatsapp_refs: list[str] = field(default_factory=list)


MANUAL_CASES: list[ManualCaseSpec] = [
    ManualCaseSpec(
        "M1",
        [41, 41, 70],
        29,
        "41+41+70 → fuerte manual 29",
        ["libreta socio"],
    ),
    ManualCaseSpec(
        "M2",
        [41, 62],
        75,
        "41+62 → fuerte manual 75 (prev: DIRECT_T2_NEIGHBOR_SIGNAL)",
        ["libreta socio"],
    ),
    ManualCaseSpec(
        "M3",
        [49, 44, 70],
        35,
        "49+44+70 → fuerte manual 35 (motor también 22)",
        ["libreta socio"],
    ),
    ManualCaseSpec(
        "M4",
        [35, 14],
        54,
        "35+14 → 54; WhatsApp 23-jun-2026 y 22-jul-2026",
        [
            "2026-06-23 Nacional 35 + Loteka 14 → 54 next day",
            "2026-07-22 NY Día 35 + Nacional 14 → 54 en Gana Más 2026-07-23",
        ],
    ),
    ManualCaseSpec(
        "M5",
        [39, 58],
        94,
        "Manuscrito 39+58→94; auditoría también vio 39→94←84",
        ["libreta socio", "deep audit 39→94←84"],
    ),
]


def reproduce_manual_case(
    spec: ManualCaseSpec,
    *,
    catalog: TableCatalog | None = None,
) -> dict[str, Any]:
    cat = catalog or build_catalog()
    # Unique observed set preserving multiplicity note
    hits = strengthen_official(obs_list(spec.observed), catalog=cat)
    official = sorted({h.candidate for h in hits})
    hit_detail = [
        {
            "fuerte": h.candidate,
            "origin": h.generator_observed,
            "confirmers": h.confirmers,
            "n_confirmers": len(h.confirmers),
            "t1_companions_of_origin": h.table1_companions_of_generator,
            "t2_group": h.table2_group_of_candidate,
        }
        for h in hits
    ]

    mf = spec.manual_fuerte
    # Direct T2: manual fuerte is T2 neighbor of some observed, not official
    t2_links = []
    for n in sorted(set(spec.observed)):
        neigh = cat.get_table2_neighbors(n, exclude_self=True)
        if mf in neigh:
            t2_links.append(
                {
                    "observed": n,
                    "manual": mf,
                    "t2_group": t2_group_ordered(cat, n),
                    "t2_pos_observed": position_in_group(t2_group_ordered(cat, n), n),
                    "t2_pos_manual": position_in_group(t2_group_ordered(cat, n), mf),
                    "t2_dist": (
                        position_in_group(t2_group_ordered(cat, n), mf)
                        - position_in_group(t2_group_ordered(cat, n), n)
                        if position_in_group(t2_group_ordered(cat, n), mf)
                        and position_in_group(t2_group_ordered(cat, n), n)
                        else None
                    ),
                }
            )

    # Classify
    certainty = "ALTA"
    if mf in official and len(official) == 1:
        klass = "FUERTE_OFICIAL_UNICO"
        evidence = f"Motor produce únicamente {mf}."
    elif mf in official and len(official) > 1:
        klass = "FUERTE_OFICIAL_ENTRE_VARIOS"
        evidence = f"Motor produce {official}; socio eligió {mf}."
    elif t2_links and mf not in official:
        klass = "VECINO_T2_DIRECTO"
        evidence = f"{mf} es vecino T2 de { [x['observed'] for x in t2_links] } sin ruta T1×T2 oficial."
        certainty = "ALTA"
    else:
        # Check if any observed produces mf as T1 candidate without confirmer
        as_cand = [n for n in set(spec.observed) if mf in t1_candidates_from_observed(cat, n)]
        if as_cand:
            klass = "RELACION_INDIRECTA"
            evidence = f"{mf} es candidato T1 de {as_cand} pero sin confirmador oficial en el set."
            certainty = "MEDIA"
        else:
            klass = "SIN_RELACION_REPRODUCIBLE"
            evidence = "No hay ruta oficial ni vecino T2 directo."
            certainty = "BAJA"

    # M5 special: also test 39+84
    alt = None
    if spec.case_id == "M5":
        hits84 = strengthen_official(obs_list([39, 84]), catalog=cat)
        alt = {
            "pair": [39, 84],
            "official": sorted({h.candidate for h in hits84}),
            "detail": [
                {
                    "fuerte": h.candidate,
                    "origin": h.generator_observed,
                    "confirmers": h.confirmers,
                }
                for h in hits84
            ],
            "58_and_84_same_t2_group": t2_group_ordered(cat, 58) == t2_group_ordered(cat, 84),
            "t2_group_58_84_94": t2_group_ordered(cat, 94),
            "both_confirm_94": 94 in {h.candidate for h in hits}
            and 94 in {h.candidate for h in hits84},
        }
        # Both pairs officially produce 94 → not transcription error required
        if 94 in official and alt["both_confirm_94"]:
            klass = "FUERTE_OFICIAL_UNICO"
            evidence = (
                "39+58→94 es fuerte oficial. 39+84→94 también. "
                "58 y 84 son vecinos T2 del mismo grupo [58,84,94]; "
                "ambos son confirmadores válidos. No es necesario tratar 58 como error."
            )
            certainty = "ALTA"

    # M3 tie-break comparison
    tiebreak = None
    if spec.case_id == "M3":
        by_f = {h["fuerte"]: h for h in hit_detail}
        tiebreak = {
            "candidates": official,
            "manual_choice": mf,
            "comparison": {
                str(f): {
                    **by_f.get(f, {}),
                    "t1_group": t1_group_ordered(cat, f),
                    "t1_pos": position_in_group(t1_group_ordered(cat, f), f),
                    "t2_group": t2_group_ordered(cat, f),
                    "t2_pos": position_in_group(t2_group_ordered(cat, f), f),
                }
                for f in official
            },
            "hypothesis_more_confirmers": (
                by_f.get(35, {}).get("n_confirmers", 0)
                > by_f.get(22, {}).get("n_confirmers", 0)
            ),
            "hypothesis_note": (
                "35 tiene 2 confirmadores (44,70); 22 tiene 1 (70). "
                "Coincide con la elección manual en este caso. "
                "No se incorpora como regla; ver contraejemplos históricos."
            ),
        }

    return {
        "case_id": spec.case_id,
        "observed": spec.observed,
        "observed_unique": sorted(set(spec.observed)),
        "manual_fuerte": mf,
        "notes": spec.notes,
        "whatsapp_refs": spec.whatsapp_refs,
        "methodology_version": METHODOLOGY_VERSION,
        "official_fuertes": official,
        "hit_detail": hit_detail,
        "direct_t2_links": t2_links,
        "classification": klass,
        "evidence": evidence,
        "certainty": certainty,
        "m5_alternate_84": alt,
        "m3_tiebreak": tiebreak,
        "geometry": {
            n: {
                "t1_candidates": t1_candidates_from_observed(cat, n),
                "t1_group": t1_group_ordered(cat, n),
                "t1_code": cat.table1_number_to_code.get(n),
                "t2_group": t2_group_ordered(cat, n),
                "t2_code": cat.table2_number_to_code.get(n),
            }
            for n in sorted(set(spec.observed) | {mf})
        },
    }


def relative_number(cat: TableCatalog, fuerte: int, dist: int) -> int | None:
    group = t1_group_ordered(cat, fuerte)
    pf = position_in_group(group, fuerte)
    if pf is None:
        return None
    for n in group:
        if position_in_group(group, n) - pf == dist:
            return n
    return None


def detect_sequence_flags(
    *,
    first_day: dict[int, int],
    fuerte: int,
    n_m1: int | None,
    n_p1: int | None,
    n_m2: int | None,
    n_p2: int | None,
) -> list[str]:
    flags = []
    fday = first_day.get(fuerte)
    if n_m1 and fuerte in first_day and n_m1 in first_day:
        if first_day[fuerte] < first_day[n_m1]:
            flags.append("F→-1")
        if first_day[n_m1] < first_day[fuerte]:
            flags.append("-1→F")
    if n_p1 and fuerte in first_day and n_p1 in first_day:
        if first_day[fuerte] < first_day[n_p1]:
            flags.append("F→+1")
        if first_day[n_p1] < first_day[fuerte]:
            flags.append("+1→F")
    if n_m2 and fuerte in first_day and n_m2 in first_day and first_day[fuerte] < first_day[n_m2]:
        flags.append("F→-2")
    if n_p2 and fuerte in first_day and n_p2 in first_day and first_day[fuerte] < first_day[n_p2]:
        flags.append("F→+2")
    if (
        n_m1
        and n_m2
        and fuerte in first_day
        and n_m1 in first_day
        and n_m2 in first_day
        and first_day[fuerte] < first_day[n_m1] < first_day[n_m2]
    ):
        flags.append("F→-1→-2")
    if (
        n_p1
        and n_p2
        and fuerte in first_day
        and n_p1 in first_day
        and n_p2 in first_day
        and first_day[fuerte] < first_day[n_p1] < first_day[n_p2]
    ):
        flags.append("F→+1→+2")
    if (
        n_m1
        and n_m2
        and fuerte in first_day
        and n_m1 in first_day
        and n_m2 in first_day
        and first_day[fuerte] < first_day[n_m1] < first_day[n_m2]
        and False
    ):
        pass
    if (
        n_m1
        and n_m2
        and fuerte in first_day
        and n_m1 in first_day
        and n_m2 in first_day
        and first_day[fuerte] < first_day[n_m1]
        and first_day[n_m2] < first_day[fuerte]
    ):
        flags.append("F→-1→-2→F_partial")  # incomplete marker unused
    # F → -1 → F (reappearance of fuerte after -1)
    if n_m1 and fuerte in first_day and n_m1 in first_day:
        # need second appearance of fuerte after -1 — handled by caller with full apps
        pass
    return flags


__all__ = [
    "RULE_CLASSES",
    "MANUAL_CASES",
    "ManualCaseSpec",
    "METHODOLOGY_VERSION",
    "new_audit_id",
    "pct",
    "obs_list",
    "reproduce_manual_case",
    "relative_number",
    "detect_sequence_flags",
    "strengthen_official",
    "t1_group_ordered",
    "t2_group_ordered",
    "t1_candidates_from_observed",
    "position_in_group",
    "build_catalog",
]
