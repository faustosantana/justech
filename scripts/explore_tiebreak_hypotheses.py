#!/usr/bin/env python3
"""Explore tiebreak hypotheses on Phase-2 eval rows (DEV)."""

from __future__ import annotations

import json
from pathlib import Path

from app.lottery.numeric_relations.analysis_engine import run_complete_analysis
from app.lottery.numeric_relations.catalog import build_catalog

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    hist = json.loads(
        (ROOT / "artifacts/scientific_validation/historical_validation_socio.json").read_text()
    )
    splits: dict = {}
    for sp in ("train", "validation", "test"):
        for r in json.loads(
            (ROOT / f"artifacts/scientific_validation/split_{sp}.json").read_text()
        ):
            splits[r["scenario_id"]] = r
    cat = build_catalog()

    # Cache analyses
    cache = {}
    for r in hist["rows"]:
        key = (tuple(r["observed_numbers"]), r["date"])
        if key not in cache:
            cache[key] = run_complete_analysis(
                {
                    "numbers": r["observed_numbers"],
                    "date": r["date"],
                    "mode": "socio",
                    "derivation_depth": 0,
                    "create_signals": False,
                },
                persist=False,
                catalog=cat,
            )

    def pick(r, *, prefer_origin_t1=False, prefer_max=False, prefer_min=False, prefer_fewer_paths=False):
        res = cache[(tuple(r["observed_numbers"]), r["date"])]
        ranked = [
            c
            for c in res.ranked_candidates
            if c["classification"]
            in ("FUERTE_PRINCIPAL", "FUERTE_SECUNDARIO", "CANDIDATO_CONFIRMADO")
        ] or res.ranked_candidates
        if not ranked:
            return None, False
        if len(ranked) >= 2 and abs(ranked[0]["total_score"] - ranked[1]["total_score"]) < 1e-9:
            tied = [
                c
                for c in ranked
                if abs(c["total_score"] - ranked[0]["total_score"]) < 1e-9
            ]
            sc = splits[r["scenario_id"]]

            def key(c):
                parts = []
                if prefer_origin_t1:
                    parts.append(
                        0 if sc["origin"] in c["evidence"]["table1_sources"] else 1
                    )
                if prefer_fewer_paths:
                    parts.append(c["evidence"]["total_path_count"])
                if prefer_max:
                    parts.append(-c["number"])
                elif prefer_min:
                    parts.append(c["number"])
                else:
                    parts.append(c["number"])
                return tuple(parts)

            tied = sorted(tied, key=key)
            return tied[0]["number"], True
        return ranked[0]["number"], False

    configs = [
        ("baseline_lex_min", {}),
        ("origin_t1_then_min", dict(prefer_origin_t1=True, prefer_min=True)),
        ("origin_t1_then_max", dict(prefer_origin_t1=True, prefer_max=True)),
        ("prefer_max", dict(prefer_max=True)),
        ("fewer_paths_min", dict(prefer_fewer_paths=True, prefer_min=True)),
        ("fewer_paths_max", dict(prefer_fewer_paths=True, prefer_max=True)),
        (
            "origin_t1_fewer_paths_max",
            dict(prefer_origin_t1=True, prefer_fewer_paths=True, prefer_max=True),
        ),
        (
            "origin_t1_fewer_paths_min",
            dict(prefer_origin_t1=True, prefer_fewer_paths=True, prefer_min=True),
        ),
    ]
    for name, kw in configs:
        n_ok = 0
        n_tie_ok = 0
        n_tie = 0
        for r in hist["rows"]:
            p, was_tie = pick(r, **kw)
            if was_tie:
                n_tie += 1
                if p == r["historical_fuerte"]:
                    n_tie_ok += 1
            if p == r["historical_fuerte"]:
                n_ok += 1
        print(
            f"{name}: top1={n_ok}/250 ({n_ok/250:.3f}) ties={n_tie} tie_ok={n_tie_ok}/{n_tie}"
        )


if __name__ == "__main__":
    main()
