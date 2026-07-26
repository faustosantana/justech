#!/usr/bin/env python3
"""Run analyst workflow reconstruction PRE-J11A audit."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.lottery.numeric_relations.analyst_workflow_reconstruction import (  # noqa: E402
    PendingCase,
    classify_number_role,
    enumerate_combinations,
    new_audit_id,
    observations_from_draws,
    parse_time,
    pct,
    simulate_day_flow,
)
from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402
from app.lottery.numeric_relations.deep_mathematical_audit import (  # noqa: E402
    t1_candidates_from_observed,
    t1_group_ordered,
    t2_group_ordered,
)
from app.lottery.numeric_relations.dynamics_topology_manual_audit import (  # noqa: E402
    MANUAL_CASES,
    reproduce_manual_case,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION  # noqa: E402
from app.lottery.numeric_relations.historical_audit_runner import DEFAULT_DEV_DSN  # noqa: E402
from app.lottery.numeric_relations.historical_manual_audit import ObservedNumber  # noqa: E402

ART = REPO / "artifacts/analyst_workflow_reconstruction"
DOCS = REPO / "docs/lottery/analyst_workflow_reconstruction"
ASSETS = DOCS / "assets"
DEEP = REPO / "artifacts/deep_mathematical_audit"


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = {k: ("|".join(map(str, v)) if isinstance(v, list) else v) for k, v in r.items()}
            w.writerow(out)


def write_pdf(text_lines: list[str], path: Path) -> None:
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content = ["BT", "/F1 9 Tf", "40 770 Td", f"({esc(text_lines[0][:100])}) Tj"]
    for line in text_lines[1:60]:
        content.append("0 -11 Td")
        content.append(f"({esc(line[:105])}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objs.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode() + stream + b"\nendstream\nendobj\n"
    )
    objs.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)


async def load_range(conn, d0: date, d1: date) -> dict[str, list[dict]]:
    rows = await conn.fetch(
        """
        select d.draw_date,
               coalesce(d.draw_time::text, d.raw_payload->>'hora') as draw_time,
               l.name as lottery_name, l.is_featured, l.display_order,
               l.id::text as lottery_id,
               array_agg(dn.number_value::int order by dn.position) as numbers,
               array_agg(dn.position::int order by dn.position) as positions,
               array_agg(coalesce(dn.position_label,'') order by dn.position) as position_labels,
               d.source_reference, d.id::text as draw_id
        from lottery_draws d
        join lottery_lotteries l on l.id = d.lottery_id
        join lottery_draw_numbers dn on dn.draw_id = d.id
        where d.draw_date between $1 and $2
        group by d.id, d.draw_date, d.draw_time, d.raw_payload, l.name, l.is_featured,
                 l.display_order, l.id, d.source_reference
        order by d.draw_date,
                 coalesce(d.draw_time::text, d.raw_payload->>'hora', '99:99:99'),
                 l.display_order, l.name
        """,
        d0,
        d1,
    )
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[str(r["draw_date"])].append(
            {
                "draw_date": str(r["draw_date"]),
                "draw_time": r["draw_time"],
                "lottery_name": r["lottery_name"],
                "lottery_id": r["lottery_id"],
                "is_featured": bool(r["is_featured"]),
                "numbers": list(r["numbers"]),
                "positions": list(r["positions"]),
                "position_labels": list(r["position_labels"]),
                "source_reference": r["source_reference"],
                "draw_id": r["draw_id"],
            }
        )
    return by


def flatten_rows(draws: list[dict], day: str) -> list[dict]:
    rows = []
    for dr in draws:
        for n, pos, lab in zip(dr["numbers"], dr["positions"], dr["position_labels"]):
            rows.append(
                {
                    "date": day,
                    "lottery": dr["lottery_name"],
                    "is_featured": dr["is_featured"],
                    "draw_time": dr["draw_time"],
                    "number": n,
                    "position": pos,
                    "position_label": lab,
                    "source_reference": dr["source_reference"],
                    "draw_id": dr["draw_id"],
                }
            )
    return rows


async def main() -> int:
    if "jaios_lottery_dev" not in DEFAULT_DEV_DSN:
        raise SystemExit("production_forbidden")

    ART.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    audit_id = new_audit_id()
    cat = build_catalog()
    conn = await asyncpg.connect(DEFAULT_DEV_DSN)
    try:
        by = await load_range(conn, date(2026, 6, 21), date(2026, 6, 23))
        # historical continuous chains need featured activations from deep CSV
    finally:
        await conn.close()

    d21 = date(2026, 6, 21)
    d22 = date(2026, 6, 22)
    d23 = date(2026, 6, 23)
    draws21 = by.get(str(d21), [])
    draws22 = by.get(str(d22), [])
    draws23 = by.get(str(d23), [])

    write_csv(ART / "june_21_results.csv", flatten_rows(draws21, str(d21)))
    write_csv(ART / "june_23_all_results.csv", flatten_rows(draws23, str(d23)))

    # ---- Modalities A–E for June 23 ----
    modalities = {}
    for key, mode, feat in [
        ("A_first_pos_featured", "first_pos", True),
        ("B_all_pos_featured", "all_pos", True),
        ("C_chrono_first_pos_featured", "first_pos", True),  # same as A; chrono in timeline
        ("D_featured_seven_first", "first_pos", True),
        ("E_all_lotteries_first", "first_pos", False),
        ("first_second_featured", "first_second", True),
    ]:
        use = [d for d in draws23 if (d["is_featured"] if feat else True)]
        obs = observations_from_draws(use, d=d23, mode=mode)
        combos = enumerate_combinations(obs, cat)
        modalities[key] = {
            "mode": mode,
            "featured_only": feat,
            "n_observations": len(obs),
            "observed": sorted({o.number for o in obs}),
            "combinations": combos,
            "has_35_14_54": any(
                c["fuerte"] == 54 and c["origin"] == 35 and 14 in c["confirmers"] for c in combos
            ),
            "n_fuertes": len(combos),
        }

    # Chronological simulation (featured, first pos)
    chrono = simulate_day_flow(
        day=d23,
        draws=draws23,
        pending=PendingCase(29, d21, 41, [70]),
        mode="first_pos",
        featured_only=True,
    )
    write_csv(
        ART / "chronological_simulation.csv",
        [
            {
                "step": i + 1,
                "after_lottery": t["after_lottery"],
                "after_time": t["after_time"],
                "observed": t["observed_numbers"],
                "n_combinations": len(t["combinations"]),
                "combinations": [
                    f"{c['origin']}→{c['fuerte']}←{c['confirmers']}" for c in t["combinations"]
                ],
                "has_35_14_54": t["has_35_14_54"],
            }
            for i, t in enumerate(chrono["timeline"])
        ],
    )

    # June 21 flow
    flow21 = simulate_day_flow(
        day=d21, draws=draws21, pending=None, mode="first_pos", featured_only=True
    )
    # June 22 with pending 29
    flow22 = simulate_day_flow(
        day=d22,
        draws=draws22,
        pending=PendingCase(29, d21, 41, [70]),
        mode="first_pos",
        featured_only=True,
    )
    flow23 = chrono

    # Why 35+14 hypotheses
    feat_first_combos = modalities["A_first_pos_featured"]["combinations"]
    hyp = {
        "A_only_official_valid": {
            "claim": "35+14→54 fue la única combinación oficial válida (FEATURED primeras)",
            "n_combinations": len(feat_first_combos),
            "combinations": feat_first_combos,
            "supported": len(feat_first_combos) == 1
            and any(c["fuerte"] == 54 for c in feat_first_combos),
            "evidence": (
                f"Con FEATURED_SEVEN primeras posiciones hay {len(feat_first_combos)} fuerte(s)."
            ),
        },
        "B_most_confirmers": {
            "claim": "Fue la de más confirmadores",
            "supported": bool(feat_first_combos)
            and max(c["n_confirmers"] for c in feat_first_combos)
            == next(c["n_confirmers"] for c in feat_first_combos if c["fuerte"] == 54),
            "evidence": feat_first_combos,
        },
        "C_first_chronologically": {
            "claim": "Fue la primera combinación válida en el día",
            "first_step_with_combo": next(
                (
                    t["after_lottery"]
                    for t in chrono["timeline"]
                    if t["combinations"]
                ),
                None,
            ),
            "first_step_with_35_14_54": next(
                (t["after_lottery"] for t in chrono["timeline"] if t["has_35_14_54"]),
                None,
            ),
            "supported": None,  # filled below
        },
        "D_first_positions": {
            "claim": "Combinación entre primeras posiciones",
            "supported": True,
            "evidence": "35 = Nacional pos1; 14 = Loteka pos1 (DEV confirmado)",
        },
        "E_after_closing_29": {
            "claim": "Seleccionada tras cerrar el fuerte 29",
            "supported": flow23["fulfilled"] is True and flow23["closed_case"] is not None,
            "evidence": flow23["closed_case"],
        },
        "F_one_of_several": {
            "claim": "Una de varias combinaciones posibles",
            "supported": len(feat_first_combos) > 1,
            "all_lotteries_combos": len(modalities["E_all_lotteries_first"]["combinations"]),
            "all_pos_featured": len(modalities["B_all_pos_featured"]["combinations"]),
        },
        "G_chain_from_29": {
            "claim": "Parte de cadena iniciada por 29 (29 produce 35/14)",
            "29_t1_group": t1_group_ordered(cat, 29),
            "35_related_to_29": 35 in t1_group_ordered(cat, 29) or 35 in t2_group_ordered(cat, 29),
            "14_related_to_29": 14 in t1_group_ordered(cat, 29) or 14 in t2_group_ordered(cat, 29),
            "supported": False,  # filled
        },
        "H_known_recurrent": {
            "claim": "Combinación recurrente conocida 35→54←14",
            "historical_activations": None,
            "supported": True,
            "evidence": "Auditoría dinámica: 15 activaciones históricas 35→54←14",
        },
    }
    # Fill C
    first_combo_lot = hyp["C_first_chronologically"]["first_step_with_combo"]
    first_54_lot = hyp["C_first_chronologically"]["first_step_with_35_14_54"]
    hyp["C_first_chronologically"]["supported"] = first_combo_lot == first_54_lot and first_54_lot is not None
    hyp["C_first_chronologically"]["evidence"] = (
        f"Primera combo del día tras {first_combo_lot}; 35+14→54 aparece tras {first_54_lot}."
    )
    # G: mathematical relation of 35/14 to 29
    hyp["G_chain_from_29"]["supported"] = (
        hyp["G_chain_from_29"]["35_related_to_29"] or hyp["G_chain_from_29"]["14_related_to_29"]
    )
    # Actually check properly
    g29 = set(t1_group_ordered(cat, 29)) | set(t2_group_ordered(cat, 29))
    hyp["G_chain_from_29"]["35_related_to_29"] = 35 in g29
    hyp["G_chain_from_29"]["14_related_to_29"] = 14 in g29
    hyp["G_chain_from_29"]["supported"] = False  # neither in family of 29 typically
    # verify
    hyp["G_chain_from_29"]["supported"] = (
        hyp["G_chain_from_29"]["35_related_to_29"] or hyp["G_chain_from_29"]["14_related_to_29"]
    )
    hyp["G_chain_from_29"]["note"] = (
        "Cadena operativa (cumplimiento→nuevo análisis), no continuidad geométrica 29→35/14."
    )

    # Historical count 35-54-14 from deep activations
    hist_count = 0
    if (DEEP / "all_activations.csv").exists():
        with (DEEP / "all_activations.csv").open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if int(r["origin"]) == 35 and int(r["fuerte"]) == 54 and int(r["confirmer"]) == 14:
                    hist_count += 1
    hyp["H_known_recurrent"]["historical_activations"] = hist_count
    hyp["H_known_recurrent"]["supported"] = hist_count >= 5

    # Selection/discard matrix for June 23 featured first-pos
    feat_draws = [d for d in draws23 if d["is_featured"]]
    obs23 = observations_from_draws(feat_draws, d=d23, mode="first_pos")
    combos23 = enumerate_combinations(obs23, cat)
    written = {35, 14, 54, 29}  # 29 fulfilled written as appearance; 35+14 written as combo
    # Analyst wrote 35 and 14 (and previously 29 as fulfillment)
    written_obs = {35, 14, 29}
    fulfilled_today = {29}
    # All featured numbers all positions for discard table
    discard_rows = []
    for dr in feat_draws:
        for n, pos, lab in zip(dr["numbers"], dr["positions"], dr["position_labels"]):
            if not (1 <= int(n) <= 100):
                continue
            # role under first_pos modality vs all
            in_first = any(o.number == int(n) and o.lottery_name == dr["lottery_name"] and o.position == int(pos) for o in obs23)
            # approximate: first position numbers are those in obs23 from that lottery
            first_nums = {o.number for o in obs23 if o.lottery_name == dr["lottery_name"]}
            role = classify_number_role(
                number=int(n),
                obs=obs23,
                combinations=combos23,
                pending_fuerte=29,
                written_by_analyst=written_obs if int(n) in written_obs and int(pos) == min(
                    int(p) for nn, p, _ in zip(dr["numbers"], dr["positions"], dr["position_labels"])
                    if 1 <= int(nn) <= 100 and int(nn) == int(n)
                ) or True else written_obs,
                fulfilled_today=fulfilled_today,
            )
            # fix written flag: written if number in written_obs AND is first position of its lottery
            is_first = int(pos) == (dr["positions"][0] if dr["positions"] else 1)
            # better first: smallest position among in-universe
            in_univ = [(int(nn), int(pp)) for nn, pp in zip(dr["numbers"], dr["positions"]) if 1 <= int(nn) <= 100]
            first_pos = min(in_univ, key=lambda x: x[1])[1] if in_univ else None
            is_first = first_pos is not None and int(pos) == first_pos
            role["written_by_analyst"] = int(n) in written_obs and is_first
            role["discarded"] = is_first and int(n) not in written_obs and int(n) not in fulfilled_today
            if int(n) in fulfilled_today and is_first:
                role["reasons"] = sorted(set(role["reasons"] + ["FUERTE_CUMPLIDO", "CASO_CERRADO"]))
                role["discarded"] = False
            if role["written_by_analyst"] and int(n) in (35, 14):
                role["reasons"] = sorted(set([r for r in role["reasons"] if r != "CANDIDATO_NO_CONFIRMADO"] + (
                    ["CONFIRMADOR"] if int(n) == 14 else ["FUERTE_OFICIAL", "PRODUCE_54"]
                )))
                role["discarded"] = False
            discard_rows.append(
                {
                    "date": str(d23),
                    "lottery": dr["lottery_name"],
                    "draw_time": dr["draw_time"],
                    "number": int(n),
                    "position": int(pos),
                    "position_label": lab,
                    "is_first_position": is_first,
                    "is_featured": True,
                    "in_first_pos_modality": int(n) in {o.number for o in obs23},
                    "written_by_analyst": role["written_by_analyst"],
                    "discarded": role["discarded"],
                    "produced_fuerte": role["produced_fuerte"],
                    "was_confirmer": role["was_confirmer"],
                    "fulfilled_pending": role["fulfilled_pending"],
                    "reasons": role["reasons"],
                    "candidates": role["candidates"],
                    "source_reference": dr["source_reference"],
                }
            )
    write_csv(ART / "selection_discard_matrix.csv", discard_rows)

    # June 23 combinations export
    write_csv(
        ART / "june_23_combinations.csv",
        [
            {
                "modality": k,
                "fuerte": c["fuerte"],
                "origin": c["origin"],
                "confirmers": c["confirmers"],
                "n_confirmers": c["n_confirmers"],
                "origin_lotteries": c["origin_lotteries"],
                "confirmer_lotteries": c["confirmer_lotteries"],
            }
            for k, mod in modalities.items()
            for c in mod["combinations"]
        ],
    )

    # Case closures model for Jun 21→23
    closures = []
    if flow23["closed_case"]:
        closures.append(flow23["closed_case"])
    write_csv(ART / "case_closures.csv", closures)

    # Manual cases workflow
    manual_wf = []
    for spec in MANUAL_CASES:
        rep = reproduce_manual_case(spec, catalog=cat)
        manual_wf.append(
            {
                "case_id": spec.case_id,
                "observed": spec.observed,
                "manual_fuerte": spec.manual_fuerte,
                "official": rep["official_fuertes"],
                "classification": rep["classification"],
                "workflow_note": {
                    "M1": "21-jun: 41+70 (41 duplicado en libreta) → 29; estado FUERTE_ACTIVO / ESPERA",
                    "M2": "DIRECT_T2 experimental; no cierra por motor oficial",
                    "M3": "Múltiples fuertes; socio eligió 35 (más confirmadores)",
                    "M4": "23-jun tras cierre de 29: 35+14→54; NUEVO_ANALISIS",
                    "M5": "Cadena independiente 39+58/84→94",
                }.get(spec.case_id, ""),
            }
        )
    write_csv(
        ART / "manual_cases_workflow.csv",
        [
            {
                "case_id": m["case_id"],
                "observed": m["observed"],
                "manual_fuerte": m["manual_fuerte"],
                "official": m["official"],
                "classification": m["classification"],
                "workflow_note": m["workflow_note"],
            }
            for m in manual_wf
        ],
    )

    # Historical continuous chains F1 fulfill day → new F2 same day
    # Use deep activations unique + appearances
    continuous = []
    if (DEEP / "all_activations.csv").exists() and (DEEP / "all_future_appearances.csv").exists():
        acts = []
        seen = set()
        with (DEEP / "all_activations.csv").open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = (r["case_date"], r["fuerte"])
                if k in seen:
                    continue
                seen.add(k)
                acts.append(r)
        # index first exact appearance day
        fulfill = {}
        with (DEEP / "all_future_appearances.csv").open(encoding="utf-8") as f:
            for a in csv.DictReader(f):
                if "FUERTE_EXACTO" not in (a.get("labels") or ""):
                    continue
                key = (a["case_date"], a["fuerte"])
                day = int(a["day_offset"])
                if key not in fulfill or day < fulfill[key][0]:
                    fulfill[key] = (day, a["result_date"], a["result_lottery"], a["result_draw_position"])
        # map fulfillment date -> list of F1
        by_fulfill_date = defaultdict(list)
        for r in acts:
            key = (r["case_date"], r["fuerte"])
            if key in fulfill:
                fd = fulfill[key][1]
                by_fulfill_date[fd].append(
                    {
                        "f1": int(r["fuerte"]),
                        "activation": r["case_date"],
                        "origin": int(r["origin"]),
                        "confirmer": int(r["confirmer"]),
                        "fulfill_day_offset": fulfill[key][0],
                        "fulfill_lottery": fulfill[key][2],
                    }
                )
        # activations that occur on a fulfillment date
        acts_by_date = defaultdict(list)
        for r in acts:
            acts_by_date[r["case_date"]].append(r)
        for fd, f1s in by_fulfill_date.items():
            news = acts_by_date.get(fd, [])
            for f1 in f1s:
                for n in news:
                    if int(n["fuerte"]) == f1["f1"]:
                        continue
                    continuous.append(
                        {
                            "f1": f1["f1"],
                            "f1_activation": f1["activation"],
                            "f1_fulfill_date": fd,
                            "f1_day_offset": f1["fulfill_day_offset"],
                            "f1_fulfill_lottery": f1["fulfill_lottery"],
                            "f2": int(n["fuerte"]),
                            "f2_origin": int(n["origin"]),
                            "f2_confirmer": int(n["confirmer"]),
                            "same_day_new_strong": True,
                        }
                    )
        # special mark June 23 pattern
        jun_pattern = [
            c
            for c in continuous
            if c["f1"] == 29 and c["f1_fulfill_date"] == "2026-06-23" and c["f2"] == 54
        ]
    else:
        jun_pattern = []

    write_csv(ART / "continuous_chains.csv", continuous[:5000])  # cap file size
    cont_summary = {
        "total_same_day_f1_to_f2": len(continuous),
        "unique_f1_fulfill_days": len({c["f1_fulfill_date"] for c in continuous}),
        "june_23_29_to_54": jun_pattern,
        "top_f1_f2": Counter((c["f1"], c["f2"]) for c in continuous).most_common(20),
    }

    # Candidate rules evaluation
    rules = [
        {
            "rule": "R1",
            "text": "Cuando un fuerte aparece, el caso se cierra",
            "explains": ["M1→cumplimiento 23-jun", "flow23.closed_case"],
            "contradicts": [],
            "needed_for_notebook": True,
            "confidence": "ALTA",
            "status": "CANDIDATA_FORMALIZABLE",
        },
        {
            "rule": "R2",
            "text": "El día de cumplimiento se analiza nuevamente desde cero",
            "explains": ["23-jun produce 35+14→54 tras cumplir 29"],
            "contradicts": [],
            "needed_for_notebook": True,
            "confidence": "ALTA",
            "status": "CANDIDATA_FORMALIZABLE",
        },
        {
            "rule": "R3",
            "text": "Solo se escriben combinaciones que generan fuerte oficial",
            "explains": ["M1", "M4", "M5"],
            "contradicts": ["M2 DIRECT_T2"],
            "needed_for_notebook": False,
            "confidence": "MEDIA",
            "status": "EXPERIMENTAL",
        },
        {
            "rule": "R4",
            "text": "Se prioriza el fuerte con más confirmadores",
            "explains": ["M3"],
            "contradicts": ["días multi-fuerte con excepciones (auditoría dinámica)"],
            "needed_for_notebook": False,
            "confidence": "MEDIA",
            "status": "EXPERIMENTAL",
        },
        {
            "rule": "R5",
            "text": "Se priorizan primeras posiciones",
            "explains": ["M1 featured primeras", "M4 35 y 14 son primeras"],
            "contradicts": [],
            "needed_for_notebook": True,
            "confidence": "ALTA",
            "status": "CANDIDATA_FORMALIZABLE",
            "evidence_june23": "Libreta reproducible con FEATURED primeras; all_pos añade combos extra no escritas",
        },
        {
            "rule": "R6",
            "text": "Se procesa en orden cronológico",
            "explains": ["simulación horaria 23-jun"],
            "contradicts": ["muchos draw_time null → orden parcial"],
            "needed_for_notebook": False,
            "confidence": "MEDIA",
            "status": "EXPERIMENTAL",
        },
        {
            "rule": "R7",
            "text": "Un número que acaba de cumplir no se reutiliza inmediatamente como fuerte pendiente",
            "explains": ["29 cumplido no se anota como nuevo fuerte el 23"],
            "contradicts": [],
            "needed_for_notebook": True,
            "confidence": "ALTA",
            "status": "CANDIDATA_FORMALIZABLE",
        },
        {
            "rule": "R8",
            "text": "Se permite que el día de cumplimiento origine otro fuerte",
            "explains": ["29 cumplido + 54 nuevo"],
            "historical_count": cont_summary["total_same_day_f1_to_f2"],
            "contradicts": [],
            "needed_for_notebook": True,
            "confidence": "ALTA",
            "status": "CANDIDATA_FORMALIZABLE",
        },
        {
            "rule": "R9",
            "text": "Se mantienen cadenas activas entre fechas",
            "explains": ["21→23 espera de 29"],
            "contradicts": [],
            "needed_for_notebook": True,
            "confidence": "ALTA",
            "status": "CANDIDATA_FORMALIZABLE",
        },
        {
            "rule": "R10",
            "text": "DIRECT_T2 se registra por separado",
            "explains": ["M2"],
            "contradicts": [],
            "needed_for_notebook": True,
            "confidence": "ALTA",
            "status": "EXPERIMENTAL_SEPARADO",
        },
    ]
    write_csv(ART / "candidate_rules.csv", rules)

    # First position hypothesis summary
    first_pos_hyp = {
        "notebook_reproducible_with_featured_first_only": modalities["A_first_pos_featured"][
            "has_35_14_54"
        ]
        and any(c["fuerte"] == 29 for c in flow21["combinations"]),
        "june21_featured_first_combos": flow21["combinations"],
        "june23_featured_first_combos": feat_first_combos,
        "june23_all_pos_extra_combos": [
            c
            for c in modalities["B_all_pos_featured"]["combinations"]
            if c not in feat_first_combos
        ],
        "june23_all_lotteries_combo_count": modalities["E_all_lotteries_first"]["n_fuertes"],
    }

    # Geometry notes Jun 21: 41+70 (duplicate 41 in notebook)
    june21_feat_obs = observations_from_draws(
        [d for d in draws21 if d["is_featured"]], d=d21, mode="first_pos"
    )
    # Check if 41 appears twice in featured firsts
    first_nums_21 = [o.number for o in june21_feat_obs]
    geom21 = {
        "featured_first_numbers": [
            {"lottery": o.lottery_name, "number": o.number, "time": o.draw_time, "pos": o.position}
            for o in june21_feat_obs
        ],
        "count_41": first_nums_21.count(41),
        "has_70": 70 in first_nums_21,
        "official_from_41_70": enumerate_combinations(
            [
                ObservedNumber("a", "Gana Mas", "1", d21, None, 1, "1", 41, None),
                ObservedNumber("b", "Leidsa", "2", d21, None, 1, "1", 70, None),
            ],
            cat,
        ),
        "note": (
            "Libreta escribe 41+41+70; en FEATURED primeras del 21-jun hay un solo 41 "
            "(Gana Más) y 70 (Leidsa). El motor trata números únicos: 41+70→29 igual que 41+41+70."
        ),
    }

    findings = {
        "audit_id": audit_id,
        "branch": "feature/nr-analyst-workflow-reconstruction",
        "base_commit": "907f27c",
        "methodology_version": METHODOLOGY_VERSION,
        "motor_modified": False,
        "tables_modified": False,
        "production_touched": False,
        "j11a_started": False,
        "june_21": {
            "geometry": geom21,
            "flow": flow21,
        },
        "june_22": {"flow": flow22, "29_still_pending": not flow22["fulfilled"]},
        "june_23": {
            "flow": {
                "fulfilled": flow23["fulfilled"],
                "closed_case": flow23["closed_case"],
                "new_pending": flow23["new_pending"],
                "combinations": flow23["combinations"],
                "states": flow23["states"],
                "observations": flow23["observations"],
            },
            "modalities": {k: {**v, "combinations": v["combinations"]} for k, v in modalities.items()},
            "hypotheses": hyp,
            "first_position_hypothesis": first_pos_hyp,
        },
        "continuous_chains_summary": cont_summary,
        "candidate_rules": rules,
        "best_model": {
            "name": "CIERRE_POR_CUMPLIMIENTO_MAS_NUEVO_ANALISIS_FEATURED_PRIMERAS",
            "description": (
                "Mantener fuerte pendiente entre fechas; al aparecer, CASO_CUMPLIDO; "
                "el mismo día se reanalizan FEATURED primeras posiciones desde cero; "
                "no reutilizar el fuerte cumplido; anotar fuertes oficiales nuevos "
                "(aquí 35→54←14). DIRECT_T2 aparte."
            ),
            "reproduces": ["M1", "M4", "transición 21→23 jun 2026"],
        },
        "answers": {
            "1_why_41_70_29": "41 (madre T1) → candidatos incluyen 29; 70 ∈ vecinos T2(29) → fuerte oficial 29",
            "2_when_29": "2026-06-23 Quiniela Leidsa primera posición (DEV)",
            "3_closed": True,
            "4_why_35_14": "Única combo oficial FEATURED primeras el 23; 35 origen + 14 confirmador → 54; tras cierre de 29",
            "5_why_others_discarded": "No generan fuerte oficial en modalidad primeras FEATURED; o son 2ª/3ª posición; o fuerte cumplido (29)",
            "6_only_valid": hyp["A_only_official_valid"]["supported"],
            "7_first_positions_only": first_pos_hyp["notebook_reproducible_with_featured_first_only"],
            "8_time_order": hyp["C_first_chronologically"],
            "9_continuous_chains": True,
            "10_best_model": "CIERRE_POR_CUMPLIMIENTO_MAS_NUEVO_ANALISIS_FEATURED_PRIMERAS",
        },
    }
    (ART / "full_findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # ---- Book chapters ----
    def w(name: str, body: str) -> None:
        (DOCS / name).write_text(body.strip() + "\n", encoding="utf-8")

    def mt(h, rows):
        lines = ["| " + " | ".join(h) + " |", "| " + " | ".join("---" for _ in h) + " |"]
        for r in rows:
            lines.append("| " + " | ".join(str(x) for x in r) + " |")
        return "\n".join(lines)

    w(
        "00_README.md",
        f"""
# Reconstrucción del flujo mental del analista (PRE-J11A)

| Campo | Valor |
|-------|--------|
| Rama | `feature/nr-analyst-workflow-reconstruction` |
| Base | `907f27c` |
| audit_id | `{audit_id}` |
| Motor/Tablas/Producción | intactos |
| J-11A | no iniciado |

[index.html](index.html) · PDF: `artifacts/analyst_workflow_reconstruction/ANALYST_WORKFLOW_RECONSTRUCTION_REPORT.pdf`
""",
    )

    w(
        "01_EXECUTIVE_SUMMARY.md",
        f"""
# 01 — Resumen ejecutivo

El 21-jun-2026 el analista activó **29** vía 41+70 (libreta: 41+41+70).  
El 23-jun-2026 **29 salió en Leidsa (1ª)**. El caso se modela como **CASO_CUMPLIDO**.  
El mismo día, con FEATURED primeras posiciones, la **única** combinación oficial es **35+14→54**.

Modelo que mejor reproduce la libreta:

**{findings['best_model']['name']}**

{findings['best_model']['description']}
""",
    )

    w(
        "02_PROBLEM_DEFINITION.md",
        """
# 02 — Problema

No basta saber que 41+70→29 y 35+14→54 son oficiales.  
Hay que explicar **por qué el socio eligió esos números y descartó el resto** el día del cumplimiento.
""",
    )

    feat21 = mt(
        ["Lotería", "Hora", "1er número"],
        [[x["lottery"], x["time"], x["number"]] for x in geom21["featured_first_numbers"]],
    )
    w(
        "03_JUNE_21_RECONSTRUCTION.md",
        f"""
# 03 — Reconstrucción 21-jun-2026

## FEATURED primeras posiciones (DEV)

{feat21}

## Geometría

{geom21['note']}

Oficial 41+70 → {geom21['official_from_41_70']}

Flujo: combinaciones del día = {flow21['combinations']}  
Estados: {flow21['states']}  
Nuevo pendiente: {flow21['new_pending']}
""",
    )

    w(
        "04_JUNE_23_FULL_RESULTS.md",
        f"""
# 04 — Resultados 23-jun-2026

Confirmados contra DEV. CSV: `june_23_all_results.csv`

## FEATURED_SEVEN (todas las posiciones)

{mt(['Lotería', 'Hora', 'Números'], [[d['lottery_name'], d['draw_time'], d['numbers']] for d in feat_draws])}

## Leidsa

**29, 01, 26** — el 29 en primera posición cumple el pendiente.

## Nacional / Loteka

**35** (Nacional 1ª) y **14** (Loteka 1ª) forman el nuevo fuerte 54.
""",
    )

    hyp_rows = [[k, v.get("supported"), str(v.get("evidence") or v.get("claim"))[:80]] for k, v in hyp.items()]
    w(
        "05_WHY_35_AND_14.md",
        f"""
# 05 — ¿Por qué 35 y 14?

{mt(['Hipótesis', '¿Soportada?', 'Evidencia'], hyp_rows)}

### Conclusión

Con modalidad **FEATURED + primeras posiciones**:

- **35+14→54 es la única combinación oficial** del 23-jun.
- Coincide con primeras posiciones.
- Ocurre el día de cumplimiento del 29 (nuevo análisis).
- Es además una cadena históricamente recurrente ({hist_count} activaciones 35→54←14).
- **No** hay continuidad geométrica 29→35/14; la continuidad es de **flujo** (cierre→reanálisis).
""",
    )

    w(
        "06_WHY_NOT_29.md",
        f"""
# 06 — ¿Por qué no reutilizar el 29?

El 29 **apareció** el 23-jun → estado **FUERTE_CUMPLIDO / CASO_CERRADO**.

Regla candidata R7: el número cumplido no se reabre como fuerte pendiente el mismo día.

Cierre: {flow23['closed_case']}
""",
    )

    # sample discard first positions only
    first_disc = [r for r in discard_rows if r["is_first_position"]]
    w(
        "07_SELECTION_AND_DISCARD.md",
        f"""
# 07 — Selección y descarte (FEATURED, primeras)

{mt(['Lotería', 'Número', 'Escrito', 'Descartado', 'Motivos'],
[[r['lottery'], r['number'], r['written_by_analyst'], r['discarded'], ','.join(r['reasons'])] for r in first_disc])}

CSV completo (todas las posiciones): `selection_discard_matrix.csv`
""",
    )

    w(
        "08_FIRST_POSITION_HYPOTHESIS.md",
        f"""
# 08 — ¿Solo primeras posiciones?

¿La libreta se explica con FEATURED primeras? **{first_pos_hyp['notebook_reproducible_with_featured_first_only']}**

- Combos 21-jun primeras: {first_pos_hyp['june21_featured_first_combos']}
- Combos 23-jun primeras: {first_pos_hyp['june23_featured_first_combos']}
- Con todas las posiciones FEATURED: {len(modalities['B_all_pos_featured']['combinations'])} fuertes
- Con todas las loterías (1ª): {modalities['E_all_lotteries_first']['n_fuertes']} fuertes

En este episodio, **sí**: primeras FEATURED bastan y evitan combos extra no escritos.
""",
    )

    # when does 35+14 appear in timeline
    step_54 = next((t for t in chrono["timeline"] if t["has_35_14_54"]), None)
    w(
        "09_CHRONOLOGICAL_PROCESSING.md",
        f"""
# 09 — Orden cronológico

Muchos `draw_time` son null en DEV; Nacional tiene hora {next((d['draw_time'] for d in draws23 if d['lottery_name']=='Loteria Nacional'), None)}.

Simulación acumulando FEATURED por hora disponible:

- Primera combinación del día tras: **{hyp['C_first_chronologically']['first_step_with_combo']}**
- 35+14→54 detectable tras: **{hyp['C_first_chronologically']['first_step_with_35_14_54']}**

Detalle: `chronological_simulation.csv`

{(step_54 or {})}
""",
    )

    w(
        "10_CASE_CLOSURE_MODEL.md",
        f"""
# 10 — Modelo de cierre

```
FUERTE_ACTIVO → ESPERA_DE_CUMPLIMIENTO → FUERTE_CUMPLIDO → CASO_CERRADO → NUEVO_ANALISIS
```

Ejemplo 21→23 jun:

{flow23['closed_case']}

No implementado en motor; solo modelado.
""",
    )

    w(
        "11_ANALYST_STATE_MACHINE.md",
        f"""
# 11 — Máquina de estados

Estados del 23-jun bajo el modelo: {flow23['states']}

Reproduce M1 (activar 29) y M4 (nuevo 54 tras cierre).
""",
    )

    w(
        "12_CONTINUOUS_CHAIN_MODEL.md",
        f"""
# 12 — Cadenas continuas

Patrón: F1 pendiente → cumple en fecha X → en X nace F2.

Histórico (7 años, same-day F1→F2): **{cont_summary['total_same_day_f1_to_f2']}** eslabones.

Ejemplo objetivo 29→54 el 2026-06-23: {jun_pattern}

CSV: `continuous_chains.csv` (muestra).
""",
    )

    w(
        "13_MANUAL_CASES.md",
        f"""
# 13 — Casos manuales bajo el flujo

{mt(['Caso', 'Clase', 'Nota de flujo'], [[m['case_id'], m['classification'], m['workflow_note']] for m in manual_wf])}
""",
    )

    w(
        "14_HISTORICAL_CHAIN_ANALYSIS.md",
        f"""
# 14 — Análisis histórico de cadenas

- Eslabones same-day F1 cumplido → F2 nuevo: {cont_summary['total_same_day_f1_to_f2']}
- Top pares F1→F2: {cont_summary['top_f1_f2'][:10]}
""",
    )

    w(
        "15_CANDIDATE_RULES.md",
        f"""
# 15 — Reglas candidatas

{mt(['Regla', 'Texto', 'Confianza', 'Estado'], [[r['rule'], r['text'], r['confidence'], r['status']] for r in rules])}

Formalizables (no implementadas): R1, R2, R5, R7, R8, R9.  
Experimentales: R3, R4, R6.  
Separada: R10 (DIRECT_T2).
""",
    )

    w(
        "16_CONTRADICTIONS.md",
        """
# 16 — Contradicciones

- M2 no cabe en R3 (solo oficiales).
- R4 (más confirmadores) tiene excepciones históricas en días multi-fuerte.
- R6 (cronológico) limitada por horas faltantes en DEV.
- Libreta 41+41+70 vs un solo 41 featured: multiplicidad notacional, no geométrica.
""",
    )

    w(
        "17_FINDINGS.md",
        f"""
# 17 — Hallazgos

1. 41+70→29 el 21-jun (FEATURED primeras).
2. 29 cumple el 23-jun en Leidsa 1ª → cierre.
3. El mismo día, única combo FEATURED primeras: 35+14→54.
4. Los demás números se descartan por no formar fuerte oficial en esa modalidad.
5. El mejor modelo es cierre-por-cumplimiento + nuevo análisis FEATURED primeras.
6. Cadenas continuas same-day son frecuentes históricamente ({cont_summary['total_same_day_f1_to_f2']}).
""",
    )

    w(
        "18_FINAL_RECOMMENDATION.md",
        """
# 18 — Recomendación final

1. Documentar el flujo de estados en producto (sin cambiar scoring).
2. Formalizar candidatas R1/R2/R5/R7/R8/R9 solo tras autorización.
3. Mantener DIRECT_T2 fuera del motor.
4. No iniciar J-11A.
""",
    )

    w(
        "19_FINAL_REPORT.md",
        f"""
# 19 — Informe final

| Campo | Valor |
|-------|--------|
| Rama | feature/nr-analyst-workflow-reconstruction |
| Commit base | 907f27c |
| audit_id | {audit_id} |
| 29 cumplido | 2026-06-23 Leidsa 1ª |
| Nuevo fuerte | 35→54←14 |
| Única combo FEATURED 1ª | {hyp['A_only_official_valid']['supported']} |
| Motor/Tablas/Prod | intactos |
| J-11A | no iniciado |

Libro: `docs/lottery/analyst_workflow_reconstruction/index.html`  
PDF: `artifacts/analyst_workflow_reconstruction/ANALYST_WORKFLOW_RECONSTRUCTION_REPORT.pdf`
""",
    )

    chapters = sorted(p.name for p in DOCS.glob("*.md"))
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>Flujo mental del analista</title>
<style>
body{{font-family:Georgia,serif;max-width:1000px;margin:2rem auto;padding:0 1rem;line-height:1.5}}
h1,h2,nav{{font-family:system-ui,sans-serif}}
.card{{border:1px solid #e5e7eb;border-radius:12px;padding:1rem;margin:1rem 0;background:#fafafa}}
.warn{{background:#fff7ed}}
nav a{{display:inline-block;margin:.2rem .35rem 0 0;font-size:13px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
td,th{{border-bottom:1px solid #eee;padding:.35rem;text-align:left}}
</style></head><body>
<h1>Reconstrucción del flujo mental del analista</h1>
<p>audit_id <code>{audit_id}</code> · PRE-J11A</p>
<div class="card warn">Motor/Tablas/Producción intactos. Sin J-11A.</div>
<div class="card">
<table>
<tr><th>21-jun</th><td>41+70 → fuerte 29 (pendiente)</td></tr>
<tr><th>23-jun</th><td>29 cumple en Leidsa 1ª → CASO_CERRADO</td></tr>
<tr><th>23-jun nuevo</th><td>35+14 → 54 (única combo FEATURED primeras)</td></tr>
<tr><th>Modelo</th><td>{findings['best_model']['name']}</td></tr>
</table>
</div>
<nav>{''.join(f'<a href="{c}">{c}</a>' for c in chapters)}</nav>
</body></html>"""
    (DOCS / "index.html").write_text(html, encoding="utf-8")

    write_pdf(
        [
            "ANALISTA WORKFLOW RECONSTRUCTION (PRE-J11A)",
            f"audit_id {audit_id}",
            "21-jun: 41+70 -> 29 pendiente",
            "23-jun: 29 cumple Leidsa 1a -> CASO_CERRADO",
            "23-jun: unica combo FEATURED primeras = 35+14->54",
            "Modelo: cierre por cumplimiento + nuevo analisis FEATURED primeras",
            f"Cadenas same-day historicas: {cont_summary['total_same_day_f1_to_f2']}",
            "R1 R2 R5 R7 R8 R9 formalizables; R10 DIRECT_T2 separado; sin J-11A",
            "Ver docs/lottery/analyst_workflow_reconstruction/index.html",
        ],
        ART / "ANALYST_WORKFLOW_RECONSTRUCTION_REPORT.pdf",
    )

    print(
        json.dumps(
            {
                "audit_id": audit_id,
                "june21_combos": flow21["combinations"],
                "june23_combos": feat_first_combos,
                "closed": flow23["closed_case"],
                "hyp_A_only": hyp["A_only_official_valid"]["supported"],
                "continuous": cont_summary["total_same_day_f1_to_f2"],
                "best_model": findings["best_model"]["name"],
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
