"""Orchestrates Historical Manual Logic Audit (read-only, DEV-safe)."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import asyncpg

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION
from app.lottery.numeric_relations.historical_manual_audit import (
    ObservedNumber,
    SEED_DEFAULT,
    WINDOWS,
    build_case_card,
    new_audit_id,
    random_baselines,
    select_ten_cases,
    summarize_population,
)

DEFAULT_DEV_DSN = "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev"
EVIDENCE_DIR = (
    Path(__file__).resolve().parents[4] / "docs/lottery/historical_audit/evidence"
)

# In-memory audit store (process-local; cancelable)
_STORE: dict[str, dict[str, Any]] = {}
_CANCEL: set[str] = set()


def get_audit(audit_id: str) -> dict[str, Any] | None:
    return _STORE.get(audit_id)


def list_audits() -> list[dict[str, Any]]:
    return [
        {
            "audit_id": a["audit_id"],
            "status": a.get("status"),
            "created_at": a.get("created_at"),
            "logic_verdict": a.get("summary", {}).get("logic_verdict"),
        }
        for a in _STORE.values()
    ]


def cancel_audit(audit_id: str) -> bool:
    if audit_id not in _STORE:
        return False
    _CANCEL.add(audit_id)
    _STORE[audit_id]["status"] = "cancelled"
    return True


def load_precomputed_into_store() -> dict[str, Any] | None:
    """Load last evidence artifacts as an idempotent audit snapshot."""
    summary_path = EVIDENCE_DIR / "audit_summary.json"
    cases_path = EVIDENCE_DIR / "audit_sample_10_plus.json"
    if not summary_path.exists() or not cases_path.exists():
        return None
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    audit_id = str(summary.get("audit_id") or new_audit_id())
    payload = {
        "audit_id": audit_id,
        "trace_id": audit_id,
        "status": "completed",
        "created_at": "precomputed",
        "production_forbidden": True,
        "read_only": True,
        "summary": summary,
        "cases": cases,
        "progress": {"pct": 100, "phase": "done"},
    }
    _STORE[audit_id] = payload
    return payload


async def load_featured_draws(conn) -> list[dict]:
    rows = await conn.fetch(
        """
        select l.id::text as lottery_id, l.name as lottery_name,
               d.id::text as draw_id, d.draw_date, d.draw_time::text as draw_time,
               d.source_reference,
               array_agg(dn.number_value::int order by dn.position) as numbers,
               array_agg(dn.position order by dn.position) as positions,
               array_agg(dn.position_label order by dn.position) as position_labels
        from lottery_draws d
        join lottery_lotteries l on l.id = d.lottery_id
        join lottery_draw_numbers dn on dn.draw_id = d.id
        where l.is_featured = true
        group by l.id, l.name, d.id, d.draw_date, d.draw_time, d.source_reference
        order by d.draw_date, d.draw_time nulls first, l.name
        """
    )
    return [dict(r) for r in rows]


def first_obs_for_date(day_draws: list[dict], d: date) -> list[ObservedNumber]:
    obs: list[ObservedNumber] = []
    for dr in day_draws:
        if not dr["numbers"]:
            continue
        chosen = None
        for n, pos, lab in zip(dr["numbers"], dr["positions"], dr["position_labels"]):
            if 1 <= int(n) <= 100:
                chosen = (int(n), int(pos), str(lab))
                break
        if chosen is None:
            continue
        n, pos, lab = chosen
        obs.append(
            ObservedNumber(
                lottery_id=dr["lottery_id"],
                lottery_name=dr["lottery_name"],
                draw_id=dr["draw_id"],
                draw_date=d,
                draw_time=dr.get("draw_time"),
                position=pos,
                position_label=lab,
                number=n,
                source_reference=dr.get("source_reference"),
            )
        )
    return obs


def find_obs(
    day_draws: list[dict], d: date, lottery_name: str, number: int
) -> ObservedNumber | None:
    for dr in day_draws:
        if dr["lottery_name"] != lottery_name:
            continue
        for n, pos, lab in zip(dr["numbers"], dr["positions"], dr["position_labels"]):
            if int(n) == int(number):
                return ObservedNumber(
                    lottery_id=dr["lottery_id"],
                    lottery_name=dr["lottery_name"],
                    draw_id=dr["draw_id"],
                    draw_date=d,
                    draw_time=dr.get("draw_time"),
                    position=int(pos),
                    position_label=str(lab),
                    number=int(number),
                    source_reference=dr.get("source_reference"),
                )
    return None


def _decide_verdicts(baselines: dict[str, Any]) -> tuple[str, str]:
    off = baselines.get("official_t1_x_t2", {})
    lift_k = baselines.get("lift_official_vs_random_same_k")
    hr = off.get("hit_rate") or 0
    if lift_k is not None and lift_k >= 1.5 and hr >= 0.2:
        logic = "A_LOGICAMENTE_VALIDADA"
    elif lift_k is not None and lift_k >= 1.2 and hr >= 0.12:
        logic = "B_PROMETEDORA_REQUIERE_MAS_MUESTRA"
    elif lift_k is not None and lift_k >= 1.05:
        logic = "C_SIN_VENTAJA_ESTADISTICA_SUFICIENTE"
    else:
        logic = "D_RECHAZADA"
    # J-11A: allow proceed only when not rejected; near-1 lift → still GO with caution (B/C)
    if logic == "D_RECHAZADA":
        j11a = "NO_GO_PARA_J11A"
    elif logic == "C_SIN_VENTAJA_ESTADISTICA_SUFICIENTE":
        j11a = "NO_GO_PARA_J11A"
    else:
        j11a = "GO_PARA_J11A"
    return logic, j11a


def write_evidence(
    *,
    out_dir: Path,
    report: dict[str, Any],
    selected: list[dict[str, Any]],
    pop_stats: dict[str, Any],
    baselines: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit_summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (out_dir / "audit_sample_10_plus.json").write_text(
        json.dumps(selected, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (out_dir / "audit_population_metrics.json").write_text(
        json.dumps(pop_stats, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (out_dir / "audit_baselines.json").write_text(
        json.dumps(baselines, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    csv_path = out_dir / "audit_sample_cases.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "date",
                "label",
                "verdict",
                "fuerte_oficial",
                "resultado_unico",
                "n_obs",
                "next_chrono",
                "same_day",
                "next_day",
                "next_7",
                "known_manual_fuerte",
            ],
        )
        w.writeheader()
        for c in selected:
            w.writerow(
                {
                    "id": c["id"],
                    "date": c["date"],
                    "label": c.get("label"),
                    "verdict": c["verdict"],
                    "fuerte_oficial": json.dumps(c.get("fuerte_oficial")),
                    "resultado_unico": c.get("resultado_unico"),
                    "n_obs": len(c.get("observations") or []),
                    "next_chrono": c["windows"]["next_chronological_draw"]["hit"],
                    "same_day": c["windows"]["same_day_other_draws"]["hit"],
                    "next_day": c["windows"]["next_calendar_day"]["hit"],
                    "next_7": c["windows"]["next_7_featured_draws"]["hit"],
                    "known_manual_fuerte": c.get("known_manual_fuerte"),
                }
            )


async def run_historical_audit(
    *,
    dsn: str = DEFAULT_DEV_DSN,
    seed: int = SEED_DEFAULT,
    write_files: bool = True,
    out_dir: Path | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    audit_id: str | None = None,
) -> dict[str, Any]:
    """Full population audit + seeded 10+ case sample. Read-only vs DB."""
    if "jaios_lottery_dev" not in dsn and "lottery_dev" not in dsn:
        raise ValueError("production_forbidden: DSN must point to DEV lottery DB")

    aid = audit_id or new_audit_id()
    _STORE[aid] = {
        "audit_id": aid,
        "trace_id": aid,
        "status": "running",
        "progress": {"pct": 0, "phase": "load"},
        "production_forbidden": True,
        "read_only": True,
    }

    cat = build_catalog()
    conn = await asyncpg.connect(dsn)
    try:
        if aid in _CANCEL:
            _STORE[aid]["status"] = "cancelled"
            return _STORE[aid]
        draws = await load_featured_draws(conn)
        draw_count = await conn.fetchval("select count(*) from lottery_draws")
        featured = await conn.fetchval(
            "select count(*) from lottery_lotteries where is_featured"
        )
    finally:
        await conn.close()

    if int(featured) != 7:
        raise RuntimeError(f"FEATURED_SEVEN invariant broken: featured={featured}")

    by_date: dict[date, list[dict]] = defaultdict(list)
    for drow in draws:
        dd = drow["draw_date"]
        if date_from and dd < date_from:
            continue
        if date_to and dd > date_to:
            continue
        by_date[dd].append(drow)

    # Re-filter draws list to period for window chrono consistency within filtered set
    draws_f = [d for d in draws if d["draw_date"] in by_date]

    _STORE[aid]["progress"] = {"pct": 20, "phase": "population"}
    population: list[dict] = []
    dates_analyzed = 0
    combinations_note = 0
    for d in sorted(by_date.keys()):
        if aid in _CANCEL:
            _STORE[aid]["status"] = "cancelled"
            return _STORE[aid]
        day = by_date[d]
        obs = first_obs_for_date(day, d)
        if len(obs) < 2:
            continue
        dates_analyzed += 1
        combinations_note += len(obs) * (len(obs) - 1)
        population.append(
            build_case_card(
                case_id=f"POP-{d.isoformat()}",
                case_date=d,
                observations=obs,
                catalog=cat,
                all_draws_sorted=draws_f,
                by_date=by_date,
                label="full_day_first_positions",
            )
        )

    _STORE[aid]["progress"] = {"pct": 70, "phase": "anchors"}
    anchors: list[dict] = []
    d1 = date(2026, 6, 21)
    day1 = by_date.get(d1, [])
    c1_obs = []
    for name, num in (("Gana Mas", 41), ("Loteria Nacional", 41), ("Quiniela Leidsa", 70)):
        o = find_obs(day1, d1, name, num)
        if o:
            c1_obs.append(o)
    if len(c1_obs) >= 2:
        anchors.append(
            build_case_card(
                case_id="ANCHOR-C1",
                case_date=d1,
                observations=c1_obs,
                catalog=cat,
                all_draws_sorted=draws_f,
                by_date=by_date,
                label="C1_manual_subset",
                known_manual_fuerte=29,
            )
        )
    c3_obs = []
    for name, num in (("Quiniela Real", 49), ("Loteria Nacional", 44), ("Quiniela Leidsa", 70)):
        o = find_obs(day1, d1, name, num)
        if o:
            c3_obs.append(o)
    if len(c3_obs) >= 2:
        anchors.append(
            build_case_card(
                case_id="ANCHOR-C3",
                case_date=d1,
                observations=c3_obs,
                catalog=cat,
                all_draws_sorted=draws_f,
                by_date=by_date,
                label="C3_manual_subset",
                known_manual_fuerte=35,
            )
        )
    d4 = date(2026, 6, 23)
    c4_obs = []
    for name, num in (("Loteria Nacional", 35), ("Quiniela Loteka", 14)):
        o = find_obs(by_date.get(d4, []), d4, name, num)
        if o:
            c4_obs.append(o)
    if len(c4_obs) >= 2:
        anchors.append(
            build_case_card(
                case_id="ANCHOR-C4",
                case_date=d4,
                observations=c4_obs,
                catalog=cat,
                all_draws_sorted=draws_f,
                by_date=by_date,
                label="C4_manual_subset",
                known_manual_fuerte=54,
            )
        )
    d5 = date(2026, 7, 22)
    c5_obs = []
    for name, num in (("New York 2:30", 35), ("Loteria Nacional", 14)):
        o = find_obs(by_date.get(d5, []), d5, name, num)
        if o:
            c5_obs.append(o)
    if len(c5_obs) >= 2:
        anchors.append(
            build_case_card(
                case_id="ANCHOR-C5",
                case_date=d5,
                observations=c5_obs,
                catalog=cat,
                all_draws_sorted=draws_f,
                by_date=by_date,
                label="C5_manual_subset",
                known_manual_fuerte=54,
            )
        )

    c2_obs2 = []
    for name, num in (("Gana Mas", 41), ("Quiniela Loteka", 62)):
        o = find_obs(day1, d1, name, num)
        if o:
            c2_obs2.append(o)
    c2_card = None
    if len(c2_obs2) >= 2:
        c2_card = build_case_card(
            case_id="ANCHOR-C2",
            case_date=d1,
            observations=c2_obs2,
            catalog=cat,
            all_draws_sorted=draws_f,
            by_date=by_date,
            label="C2_direct_t2_rejected",
            known_manual_fuerte=75,
        )
        official_nums = {h["candidate"] for h in c2_card.get("official_strengthened") or []}
        if 75 not in official_nums:
            c2_card["verdict"] = "DIRECT_T2_RECHAZADO"
            c2_card["explanation"] = (
                "Manual 75 no es fuerte oficial. 62→75 es DIRECT_T2_NEIGHBOR_SIGNAL rechazada. "
                + c2_card.get("explanation", "")
            )

    selected, sel_meta = select_ten_cases(population, anchors=anchors, seed=seed)
    if c2_card and not any(c.get("label") == "C2_direct_t2_rejected" for c in selected):
        selected.append(c2_card)
        for i, c in enumerate(selected, start=1):
            c["id"] = f"HIST-{i:03d}"
        sel_meta["quotas_achieved"]["total"] = len(selected)
        sel_meta["c2_forced_include"] = True

    pop_stats = summarize_population(population)
    sample_stats = summarize_population(selected)
    baselines = random_baselines(population, by_date=by_date, seed=seed)
    logic, j11a = _decide_verdicts(baselines)

    total_strengthened = sum(len(c.get("official_strengthened") or []) for c in population)
    total_t1 = sum(
        len(o.get("table1_companions") or [])
        for c in population
        for o in c["observations"]
    )

    report = {
        "audit_id": aid,
        "trace_id": aid,
        "methodology_version": METHODOLOGY_VERSION,
        "production_forbidden": True,
        "motor_modified": False,
        "tables_modified": False,
        "draw_count_all": int(draw_count),
        "featured_seven": int(featured),
        "featured_draws_loaded": len(draws_f),
        "dates_analyzed": dates_analyzed,
        "population_cases": len(population),
        "generator_pair_upper_bound": combinations_note,
        "total_t1_companion_slots_scanned": total_t1,
        "total_official_strengthened_instances": total_strengthened,
        "seed": seed,
        "selection": sel_meta,
        "population_metrics": pop_stats,
        "sample_metrics": sample_stats,
        "random_baselines": baselines,
        "windows": list(WINDOWS),
        "sample_case_ids": [c["id"] for c in selected],
        "logic_verdict": logic,
        "j11a_gate": j11a,
        "same_day_note": (
            "For full_day_first_positions unit, same_day_other_draws is structurally empty "
            "(all featured draws that day are case inputs)."
        ),
    }

    if write_files:
        write_evidence(
            out_dir=out_dir or EVIDENCE_DIR,
            report=report,
            selected=selected,
            pop_stats=pop_stats,
            baselines=baselines,
        )

    payload = {
        "audit_id": aid,
        "trace_id": aid,
        "status": "completed",
        "progress": {"pct": 100, "phase": "done"},
        "production_forbidden": True,
        "read_only": True,
        "summary": report,
        "cases": selected,
    }
    _STORE[aid] = payload
    return payload
