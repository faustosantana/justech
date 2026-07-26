#!/usr/bin/env python3
"""Read-only scientific validation of NR motor vs manual cases.

Does NOT modify motor, tables, or formulas. Writes JSON evidence under docs/lottery/validation/.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg

# Ensure backend root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION  # noqa: E402
from app.lottery.numeric_relations.validation_lab import run_validation_lab  # noqa: E402

DEV_DSN = "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev"
OUT_DIR = ROOT.parent / "docs" / "lottery" / "validation" / "evidence"

LOTTERY_ALIASES = {
    "GM": "Gana Mas",
    "Gana Mas": "Gana Mas",
    "Ganó Más": "Gana Mas",
    "Nacional": "Loteria Nacional",
    "Leidsa": "Quiniela Leidsa",
    "Loteka": "Quiniela Loteka",
    "Real": "Quiniela Real",
    "New York Día": "New York 2:30",
    "New York Dia": "New York 2:30",
    "NY Día": "New York 2:30",
    "NY 2:30": "New York 2:30",
    "NY 10:30": "New York 10:30",
}


@dataclass
class ManualCase:
    id: str
    date: date
    observations: list[tuple[str, int]]  # (alias, number)
    manual_fuerte: int
    next_day_check: tuple[str, int] | None = None  # (lottery alias, expected number)


CASES = [
    ManualCase(
        "C1",
        date(2026, 6, 21),
        [("GM", 41), ("Nacional", 41), ("Leidsa", 70)],
        29,
    ),
    ManualCase(
        "C2",
        date(2026, 6, 21),
        [("Nacional", 41), ("Loteka", 62)],
        75,
    ),
    ManualCase(
        "C3",
        date(2026, 6, 21),
        [("Real", 49), ("Nacional", 44), ("Leidsa", 70)],
        35,
    ),
    ManualCase(
        "C4",
        date(2026, 6, 23),
        [("Nacional", 35), ("Loteka", 14)],
        54,
        next_day_check=("any_featured", 54),
    ),
    ManualCase(
        "C5",
        date(2026, 7, 22),
        [("New York Día", 35), ("Nacional", 14)],
        54,
        next_day_check=("GM", 54),
    ),
]


def companions(cat, n: int) -> set[int]:
    return set(cat.get_table1_companions(n))


def neighbors(cat, n: int, *, exclude_self: bool = True) -> set[int]:
    return set(cat.get_table2_neighbors(n, exclude_self=exclude_self))


def t1_peers(cat, n: int) -> set[int]:
    code = cat.table1_number_to_code[n]
    return set(cat.table1_code_to_numbers.get(code, []))


def hyp_A_comp_neigh(cat, obs: list[int], fuerte: int) -> dict[str, Any]:
    hits: set[int] = set()
    edges: list[dict[str, Any]] = []
    for a, b in combinations(obs, 2):
        for left, right in ((a, b), (b, a)):
            inter = companions(cat, left) & neighbors(cat, right)
            hits |= inter
            if fuerte in inter:
                edges.append(
                    {
                        "companions_of": left,
                        "neighbors_of": right,
                        "intersection": sorted(inter),
                    }
                )
    return {
        "id": "A",
        "name": "companions(a) ∩ neighbors(b) for pair of same-day observations",
        "hit": fuerte in hits,
        "produced": sorted(hits),
        "edges_for_fuerte": edges,
    }


def hyp_F_cand_confirmed(cat, obs: list[int], fuerte: int) -> dict[str, Any]:
    """Official motor relation shape: candidate=T1 companion of N; confirmer=T2 neighbor of candidate;
    other same-day observed numbers act as potential confirmers."""
    hits: set[int] = set()
    detail: list[dict[str, Any]] = []
    uniq = list(dict.fromkeys(obs))
    for a in uniq:
        others = set(uniq) - {a}
        for cand in companions(cat, a):
            conf = neighbors(cat, cand) & others
            if conf:
                hits.add(cand)
                if cand == fuerte:
                    detail.append(
                        {
                            "observed_N": a,
                            "candidate": cand,
                            "confirmers_from_other_obs": sorted(conf),
                        }
                    )
    return {
        "id": "F",
        "name": "candidate companions(N) confirmed when another same-day obs ∈ neighbors(candidate)",
        "hit": fuerte in hits,
        "produced": sorted(hits),
        "detail_for_fuerte": detail,
    }


def hyp_B_neigh_neigh(cat, obs: list[int], fuerte: int) -> dict[str, Any]:
    hits: set[int] = set()
    for a, b in combinations(obs, 2):
        hits |= neighbors(cat, a) & neighbors(cat, b)
    return {
        "id": "B",
        "name": "neighbors(a) ∩ neighbors(b)",
        "hit": fuerte in hits,
        "produced": sorted(hits),
    }


def hyp_C_comp_comp(cat, obs: list[int], fuerte: int) -> dict[str, Any]:
    hits: set[int] = set()
    for a, b in combinations(obs, 2):
        hits |= companions(cat, a) & companions(cat, b)
    return {
        "id": "C",
        "name": "companions(a) ∩ companions(b)",
        "hit": fuerte in hits,
        "produced": sorted(hits),
    }


def hyp_D_in_companions(cat, obs: list[int], fuerte: int) -> dict[str, Any]:
    hits: set[int] = set()
    for a in obs:
        hits |= companions(cat, a)
    return {
        "id": "D",
        "name": "manual Fuerte ∈ companions(any observed) [necessary but weak]",
        "hit": fuerte in hits,
        "produced": sorted(hits),
    }


def hyp_E_neighbor_of_obs(cat, obs: list[int], fuerte: int) -> dict[str, Any]:
    hits: set[int] = set()
    for a in obs:
        hits |= neighbors(cat, a)
    return {
        "id": "E",
        "name": "manual Fuerte ∈ neighbors(any observed)",
        "hit": fuerte in hits,
        "produced": sorted(hits),
    }


def hyp_G_t2_pair(cat, obs: list[int], fuerte: int) -> dict[str, Any]:
    """Predictor: if an observed number has exactly one T2 neighbor, emit that neighbor.

    This is a fair predictive form of the T2 pair relation (not membership cheating).
    """
    produced: set[int] = set()
    pairs = []
    for a in obs:
        neigh = neighbors(cat, a)
        pairs.append({"observed": a, "neighbors": sorted(neigh), "singleton": len(neigh) == 1})
        if len(neigh) == 1:
            produced |= neigh
    return {
        "id": "G",
        "name": "Singleton T2 neighbor of an observed number (pair predictor)",
        "hit": fuerte in produced,
        "produced": sorted(produced),
        "pairs": pairs,
    }


def hyp_H_t1_code_peers(cat, obs: list[int], fuerte: int) -> dict[str, Any]:
    hits: set[int] = set()
    for a, b in combinations(obs, 2):
        hits |= t1_peers(cat, a) & t1_peers(cat, b)
    return {
        "id": "H",
        "name": "t1_peers(a) ∩ t1_peers(b) (shared Tabla1 code of the drawn numbers)",
        "hit": fuerte in hits,
        "produced": sorted(hits),
    }


HYPOTHESES = [
    hyp_A_comp_neigh,
    hyp_F_cand_confirmed,
    hyp_B_neigh_neigh,
    hyp_C_comp_comp,
    hyp_D_in_companions,
    hyp_E_neighbor_of_obs,
    hyp_G_t2_pair,
    hyp_H_t1_code_peers,
]


async def load_name_map(conn) -> dict[str, str]:
    rows = await conn.fetch(
        "SELECT id::text AS id, name FROM lottery_lotteries WHERE is_featured = true"
    )
    return {r["name"]: r["id"] for r in rows}


async def draws_on_date(conn, d: date) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT l.name, l.id::text AS lottery_id, d.id::text AS draw_id, d.draw_date,
               array_agg(dn.number_value::int ORDER BY dn.position) AS numbers
        FROM lottery_draws d
        JOIN lottery_lotteries l ON l.id = d.lottery_id
        JOIN lottery_draw_numbers dn ON dn.draw_id = d.id
        WHERE d.draw_date = $1 AND l.is_featured = true
        GROUP BY l.name, l.id, d.id, d.draw_date
        ORDER BY l.name
        """,
        d,
    )
    return [dict(r) for r in rows]


async def number_appeared_on(
    conn, d: date, number: int, lottery_name: str | None = None
) -> list[dict[str, Any]]:
    # number_value is stored as text in DEV schema
    num_s = str(int(number)).zfill(2) if False else str(int(number))
    if lottery_name and lottery_name != "any_featured":
        rows = await conn.fetch(
            """
            SELECT l.name, d.draw_date,
                   array_agg(dn.number_value ORDER BY dn.position) AS numbers
            FROM lottery_draws d
            JOIN lottery_lotteries l ON l.id = d.lottery_id
            JOIN lottery_draw_numbers dn ON dn.draw_id = d.id
            WHERE d.draw_date = $1 AND l.name = $2 AND l.is_featured = true
            GROUP BY l.name, d.draw_date
            HAVING $3::text = ANY(array_agg(dn.number_value::text))
                OR $4::text = ANY(array_agg(lpad(dn.number_value::text, 2, '0')))
                OR $3::int = ANY(array_agg(dn.number_value::int))
            """,
            d,
            lottery_name,
            num_s,
            num_s.zfill(2),
        )
    else:
        rows = await conn.fetch(
            """
            SELECT l.name, d.draw_date,
                   array_agg(dn.number_value ORDER BY dn.position) AS numbers
            FROM lottery_draws d
            JOIN lottery_lotteries l ON l.id = d.lottery_id
            JOIN lottery_draw_numbers dn ON dn.draw_id = d.id
            WHERE d.draw_date = $1 AND l.is_featured = true
            GROUP BY l.name, d.draw_date
            HAVING $2::int = ANY(array_agg(dn.number_value::int))
            """,
            d,
            number,
        )
    return [dict(r) for r in rows]


def reconstruct_tables(cat, numbers: list[int]) -> dict[str, Any]:
    out = {}
    for n in numbers:
        t1_code_of_n = cat.table1_number_to_code[n]
        comps = sorted(companions(cat, n))
        t2 = cat.get_table2_code_for_number(n)
        neigh = sorted(neighbors(cat, n))
        out[str(n)] = {
            "observed": n,
            "motor_mother_code": n,
            "table1_code_of_number": t1_code_of_n,
            "table1_companions_mother_eq_n": comps,
            "table1_peers_same_code_as_number": sorted(t1_peers(cat, n)),
            "table2_code": t2,
            "table2_neighbors": neigh,
            "table2_group": list(cat.table2_code_to_numbers.get(t2, [])),
        }
    return out


def motor_single_obs_ranking_without_db(cat, n: int) -> dict[str, Any]:
    """Structural ranking without history: all companions with their neighbor lists (score=0)."""
    comps = sorted(companions(cat, n))
    ranking = []
    for c in comps:
        ranking.append(
            {
                "number": c,
                "neighbors": sorted(neighbors(cat, c)),
                "score_without_history": 0,
                "is_manual_fuerte": c == None,  # filled later
            }
        )
    return {"observed": n, "companions": comps, "structural_candidates": ranking}


async def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cat = build_catalog()
    conn = await asyncpg.connect(DEV_DSN)
    try:
        name_to_id = await load_name_map(conn)
        case_reports: list[dict[str, Any]] = []
        hyp_stats: dict[str, Counter] = {
            h.__name__: Counter() for h in HYPOTHESES  # type: ignore
        }
        # remap to hyp ids
        hyp_stats = {}

        for case in CASES:
            obs_nums = [n for _, n in case.observations]
            uniq_obs = list(dict.fromkeys(obs_nums))
            draws = await draws_on_date(conn, case.date)
            draw_map = {d["name"]: d for d in draws}

            # Verify observations exist in history
            obs_evidence = []
            for alias, num in case.observations:
                lname = LOTTERY_ALIASES[alias]
                drow = draw_map.get(lname)
                present = bool(drow and num in (drow.get("numbers") or []))
                obs_evidence.append(
                    {
                        "alias": alias,
                        "lottery": lname,
                        "number": num,
                        "present_in_db": present,
                        "draw_numbers": list(drow["numbers"]) if drow else None,
                        "lottery_id": name_to_id.get(lname),
                    }
                )

            tables = reconstruct_tables(cat, uniq_obs + [case.manual_fuerte])

            hyp_results = []
            for fn in HYPOTHESES:
                hr = fn(cat, uniq_obs, case.manual_fuerte)
                hyp_results.append(hr)
                hid = hr["id"]
                hyp_stats.setdefault(hid, Counter())
                hyp_stats[hid]["cases"] += 1
                if hr["hit"]:
                    hyp_stats[hid]["hits"] += 1
                else:
                    hyp_stats[hid]["misses"] += 1
                # false positives: produced numbers that are not fuerte — count set size excluding fuerte
                fps = [x for x in hr.get("produced", []) if x != case.manual_fuerte]
                hyp_stats[hid]["false_positive_items"] += len(fps)
                if hr["hit"] and len(hr.get("produced", [])) == 1:
                    hyp_stats[hid]["exact_singleton"] += 1

            # Official motor: per observed number, structural + note that history scoring
            # needs occurrences of THAT number — we run analyze via in-memory if we load draws
            motor_per_obs = []
            for alias, num in case.observations:
                lname = LOTTERY_ALIASES[alias]
                lid = name_to_id.get(lname)
                comps = sorted(companions(cat, num))
                rank_pos = comps.index(case.manual_fuerte) + 1 if case.manual_fuerte in comps else None
                motor_per_obs.append(
                    {
                        "observed": num,
                        "lottery": lname,
                        "lottery_id": lid,
                        "companions": comps,
                        "manual_fuerte_in_companions": case.manual_fuerte in comps,
                        "manual_fuerte_companion_index": rank_pos,
                        "note": (
                            "Official /analyze ranks companions by historical confirmer hits "
                            "on past occurrences of this single observed number; it does not "
                            "natively ingest multi-lottery same-day observation sets."
                        ),
                    }
                )

            # Does any hypothesis produce fuerte uniquely?
            matching = [h for h in hyp_results if h["hit"]]
            exact = [
                h
                for h in matching
                if h.get("produced") == [case.manual_fuerte]
                or (case.manual_fuerte in h.get("produced", []) and len(h.get("produced", [])) == 1)
            ]

            # Prefer A and F for "motor-shaped" explanation
            motor_shaped = [h for h in matching if h["id"] in ("A", "F")]

            next_day = None
            if case.next_day_check:
                alias, expected = case.next_day_check
                lname = (
                    LOTTERY_ALIASES.get(alias, "any_featured")
                    if alias != "any_featured"
                    else "any_featured"
                )
                hits = await number_appeared_on(
                    conn,
                    case.date + timedelta(days=1),
                    expected,
                    lname if lname != "any_featured" else None,
                )
                next_day = {
                    "date": (case.date + timedelta(days=1)).isoformat(),
                    "expected_number": expected,
                    "lottery_filter": lname,
                    "appeared": bool(hits),
                    "hits": hits,
                }

            lab = run_validation_lab(
                observed=[
                    {"number": n, "lottery_name": LOTTERY_ALIASES[a]}
                    for a, n in case.observations
                ],
                manual_fuerte=case.manual_fuerte,
                as_of_date=case.date,
                catalog=cat,
            )

            # DB-corrected: use first number of named lottery that day when present
            db_obs = []
            for alias, num in case.observations:
                lname = LOTTERY_ALIASES[alias]
                drow = draw_map.get(lname)
                if drow and drow.get("numbers"):
                    first = int(drow["numbers"][0])
                    db_obs.append({"alias": alias, "lottery": lname, "stated": num, "db_first": first, "match": first == num})
                else:
                    db_obs.append({"alias": alias, "lottery": lname, "stated": num, "db_first": None, "match": False})

            # Divergence diagnosis vs official single-N motor
            any_companion = any(m["manual_fuerte_in_companions"] for m in motor_per_obs)
            coincidence = bool(motor_shaped)
            if exact:
                coincidence_label = "SI (hipótesis exacta singleton)"
            elif coincidence:
                coincidence_label = "SI (relación motor-shaped; puede haber otros candidatos en el conjunto)"
            elif any(h["id"] in ("E", "G") and h["hit"] for h in hyp_results) and not coincidence:
                coincidence_label = "NO_MOTOR_SHAPED (solo vecino T2 u otra relación débil)"
            elif any_companion:
                coincidence_label = "PARCIAL (Fuerte es compañero T1 de algún observado, sin cruce confirmador completo en este recorte)"
            else:
                coincidence_label = "NO"

            report = {
                "case_id": case.id,
                "date": case.date.isoformat(),
                "observations": [
                    {"alias": a, "lottery": LOTTERY_ALIASES[a], "number": n}
                    for a, n in case.observations
                ],
                "manual_fuerte": case.manual_fuerte,
                "observation_db_evidence": obs_evidence,
                "db_first_number_check": db_obs,
                "draws_that_day_featured": draws,
                "table_reconstruction": tables,
                "hypotheses": hyp_results,
                "validation_lab": lab,
                "motor_per_observed_number": motor_per_obs,
                "matching_hypotheses": [h["id"] for h in matching],
                "exact_singleton_hypotheses": [h["id"] for h in exact],
                "motor_shaped_matches": [h["id"] for h in motor_shaped],
                "coincidence": coincidence_label,
                "lab_coincidence": lab.get("coincidence"),
                "next_day_verification": next_day,
                "methodology_version_reference": METHODOLOGY_VERSION,
                "dev_db_max_note": "DEV max draw_date may be before some case dates",
            }
            case_reports.append(report)
            (OUT_DIR / f"{case.id}.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(case.id, coincidence_label, "matches", report["matching_hypotheses"])

        # Aggregate stats
        stats_rows = []
        for hid, ctr in sorted(hyp_stats.items()):
            cases_n = ctr["cases"]
            tp = ctr["hits"]  # case-level: fuerte recovered
            fn = ctr["misses"]
            # precision at case level if we treat "produced non-empty including fuerte" as positive prediction
            # For set-valued predictors, define:
            # - TP: fuerte in produced
            # - FP rate proxy: avg |produced \ {fuerte}|
            precision = tp / cases_n if cases_n else 0.0
            recall = tp / cases_n if cases_n else 0.0  # same at case granularity for recovery
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall)
                else 0.0
            )
            exact_rate = ctr.get("exact_singleton", 0) / cases_n if cases_n else 0.0
            avg_fp_items = ctr["false_positive_items"] / cases_n if cases_n else 0.0
            stats_rows.append(
                {
                    "hypothesis": hid,
                    "cases": cases_n,
                    "coincidences_fuerte_recovered": tp,
                    "false_negatives_cases": fn,
                    "success_pct": round(100 * tp / cases_n, 1) if cases_n else 0,
                    "exact_singleton_pct": round(100 * exact_rate, 1),
                    "avg_extra_numbers_when_fired": round(avg_fp_items, 2),
                    "precision_case_recovery": round(precision, 3),
                    "recall_case_recovery": round(recall, 3),
                    "f1_case_recovery": round(f1, 3),
                    "evidence_level": (
                        "alta"
                        if tp == cases_n and exact_rate >= 0.6
                        else "media"
                        if tp == cases_n
                        else "baja"
                        if tp > 0
                        else "nula"
                    ),
                }
            )

        summary = {
            "methodology_version": METHODOLOGY_VERSION,
            "production_forbidden": True,
            "motor_modified": False,
            "tables_modified": False,
            "draw_count_dev": await conn.fetchval("SELECT COUNT(*) FROM lottery_draws"),
            "cases": [
                {
                    "id": r["case_id"],
                    "manual_fuerte": r["manual_fuerte"],
                    "coincidence": r["coincidence"],
                    "matching_hypotheses": r["matching_hypotheses"],
                    "exact_singleton_hypotheses": r["exact_singleton_hypotheses"],
                }
                for r in case_reports
            ],
            "hypothesis_stats": stats_rows,
        }
        (OUT_DIR / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
