"""Phase 3 — audit 14 errors, feature matrix, hypothesis lab, final benchmark."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.tiebreak_engine import (
    DEFAULT_PRACTICAL_THRESHOLD,
    apply_hypothesis,
    detect_tie_group,
)
from app.lottery.numeric_relations.catalog import build_catalog

ROOT = Path(__file__).resolve().parents[5]
# parents: tiebreak_engine is in analysis_engine; this file will live in scripts
# Actually this module is under analysis_engine/tiebreak_lab.py


HYPOTHESES = [
    "TIEBREAK_MORE_INDEPENDENT_SOURCES",
    "TIEBREAK_STRONGER_CROSS_TABLE",
    "TIEBREAK_MORE_DIRECT_T2_CONFIRMERS",
    "TIEBREAK_MORE_DIRECT_T1_SOURCES",
    "TIEBREAK_LOWER_DEPTH",
    "TIEBREAK_FEWER_DUPLICATE_PATHS",
    "TIEBREAK_FIRST_POSITION_SUPPORT",
    "TIEBREAK_SHORT_WINDOW_HISTORY",
    "TIEBREAK_EXACT_HISTORY",
    "TIEBREAK_RECENT_EQUIVALENT_CASES",
    "TIEBREAK_SOURCE_ORDER",
    "TIEBREAK_REPEATED_INPUT",
    "TIEBREAK_PROFILE_SOCIO",
]


def _repo() -> Path:
    return Path(__file__).resolve().parents[5]


def load_splits() -> dict[str, list[dict[str, Any]]]:
    root = _repo()
    out = {}
    for sp in ("train", "validation", "test"):
        out[sp] = json.loads(
            (root / "artifacts/scientific_validation" / f"split_{sp}.json").read_text()
        )
    return out


def load_phase2_errors() -> list[dict[str, Any]]:
    root = _repo()
    err = json.loads(
        (root / "artifacts/scientific_validation/error_analysis.json").read_text()
    )
    hist = json.loads(
        (
            root / "artifacts/scientific_validation/historical_validation_socio.json"
        ).read_text()
    )
    by_id = {r["scenario_id"]: r for r in hist["rows"]}
    splits = {}
    for rows in load_splits().values():
        for r in rows:
            splits[r["scenario_id"]] = r
    cases = []
    for c in err["sample_cases"]:
        sc = splits[c["scenario_id"]]
        hr = by_id[c["scenario_id"]]
        cases.append({**c, **sc, "eval_row": hr})
    return cases


def audit_error_cases(limit_analysis: bool = False) -> list[dict[str, Any]]:
    cat = build_catalog()
    cases = load_phase2_errors()
    audited = []
    for c in cases:
        nums = [c["origin"], c["confirmer"]]  # generator-first for audit fidelity
        res = run_complete_analysis(
            {
                "numbers": nums,
                "date": c["case_date"],
                "mode": "socio",
                "derivation_depth": 0,
                "create_signals": False,
                "enable_tiebreak": False,
            },
            persist=False,
            catalog=cat,
            enable_tiebreak=False,
        )
        ranked = {x["number"]: x for x in res.ranked_candidates}
        chosen = c["chosen"]
        hist_f = c["historical_outcome_fuerte"]
        ch = ranked.get(chosen)
        hf = ranked.get(hist_f)

        def pack(row: dict[str, Any] | None) -> dict[str, Any] | None:
            if not row:
                return None
            ev = row["evidence"]
            return {
                "number": row["number"],
                "rank": row["rank"],
                "score": row["total_score"],
                "classification": row["classification"],
                "table1_sources": ev["table1_sources"],
                "direct_confirmers": ev["direct_confirmers"],
                "independent_path_count": ev["independent_path_count"],
                "same_source_repetitions": ev["same_source_repetitions"],
                "direct_path_count": ev["direct_path_count"],
                "total_path_count": ev["total_path_count"],
                "cross_table_support": ev["cross_table_support"],
                "multi_source_support": ev["multi_source_support"],
                "ambiguity_score": ev["ambiguity_score"],
                "components": row.get("components"),
            }

        audited.append(
            {
                "scenario_id": c["scenario_id"],
                "date": c["case_date"],
                "year": c.get("year"),
                "lotteries": [c.get("origin_lottery"), c.get("confirmer_lottery")],
                "positions": [c.get("origin_position"), c.get("confirmer_position")],
                "observed_numbers_sorted": c["observed_numbers"],
                "observed_generator_first": nums,
                "origin": c["origin"],
                "confirmer": c["confirmer"],
                "chosen_by_motor_phase2": chosen,
                "historical_fuerte": hist_f,
                "hist_rank_phase2": c.get("hist_rank_in_motor"),
                "score_gap": (ch["total_score"] - hf["total_score"])
                if ch and hf
                else None,
                "real_tie": bool(
                    ch and hf and abs(ch["total_score"] - hf["total_score"]) < 1e-9
                ),
                "chosen_detail": pack(ch),
                "historical_detail": pack(hf),
                "alternatives": [
                    {"number": x["number"], "score": x["total_score"], "cls": x["classification"]}
                    for x in res.ranked_candidates[:6]
                ],
                "input_order": nums,
                "frequency_notes": {
                    "n_confirmers_activation": c.get("n_confirmers"),
                    "n_fuertes_same_day": c.get("n_fuertes_same_day"),
                },
            }
        )
    return audited


def build_feature_matrix(audited: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for a in audited:
        ch = a["chosen_detail"] or {}
        hf = a["historical_detail"] or {}
        rows.append(
            {
                "scenario_id": a["scenario_id"],
                "date": a["date"],
                "chosen": a["chosen_by_motor_phase2"],
                "historical": a["historical_fuerte"],
                "real_tie": a["real_tie"],
                "score_gap": a["score_gap"],
                "diff_t1_sources": len(hf.get("table1_sources") or [])
                - len(ch.get("table1_sources") or []),
                "diff_t2_confirmers": len(hf.get("direct_confirmers") or [])
                - len(ch.get("direct_confirmers") or []),
                "diff_independent_paths": (hf.get("independent_path_count") or 0)
                - (ch.get("independent_path_count") or 0),
                "diff_duplicate_paths": (hf.get("same_source_repetitions") or 0)
                - (ch.get("same_source_repetitions") or 0),
                "diff_total_paths": (hf.get("total_path_count") or 0)
                - (ch.get("total_path_count") or 0),
                "hist_has_origin_as_t1": a["origin"]
                in (hf.get("table1_sources") or []),
                "chosen_has_origin_as_t1": a["origin"]
                in (ch.get("table1_sources") or []),
                "both_cross_table": bool(ch.get("cross_table_support"))
                and bool(hf.get("cross_table_support")),
                "competitors_tied": 2 if a["real_tie"] else 1,
            }
        )
    return rows


def _pick_from_result(
    res: Any,
    *,
    hypothesis: str | None,
    allow_multi: bool,
    threshold: float,
    observed: list[int],
) -> dict[str, Any]:
    ranked = list(res.ranked_candidates)
    if hypothesis:
        ordered, decisions = apply_hypothesis(
            ranked,
            hypothesis=hypothesis,
            observed_numbers=observed,
            practical_threshold=threshold,
            allow_multi_fuerte=allow_multi and hypothesis == "TIEBREAK_PROFILE_SOCIO",
        )
    else:
        ordered, decisions = ranked, []
    multi = [c for c in ordered if c.get("classification") == "EMPATE_MULTI_FUERTE"]
    if multi:
        top_nums = [c["number"] for c in multi]
        primary = None
    else:
        top_nums = [c["number"] for c in ordered[:3]]
        primary = ordered[0]["number"] if ordered else None
    return {
        "primary": primary,
        "top_nums": top_nums,
        "multi": [c["number"] for c in multi],
        "decisions": [d.to_dict() if hasattr(d, "to_dict") else d for d in decisions],
        "ranked": ordered,
    }


def evaluate_split(
    scenarios: list[dict[str, Any]],
    *,
    hypothesis: str | None,
    allow_multi: bool = False,
    threshold: float = DEFAULT_PRACTICAL_THRESHOLD,
    generator_first: bool = True,
    enable_engine_tiebreak: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    cat = build_catalog()
    use = scenarios if limit is None else scenarios[:limit]
    top1 = top2 = top3 = hist_in_cands = multi_n = 0
    rows = []
    for sc in use:
        nums = (
            [sc["origin"], sc["confirmer"]]
            if generator_first
            else list(sc["observed_numbers"])
        )
        res = run_complete_analysis(
            {
                "numbers": nums,
                "date": sc["case_date"],
                "mode": "socio",
                "derivation_depth": 0,
                "create_signals": False,
                "enable_tiebreak": enable_engine_tiebreak,
            },
            persist=False,
            catalog=cat,
            enable_tiebreak=enable_engine_tiebreak,
        )
        if enable_engine_tiebreak:
            ordered = res.ranked_candidates
            multi = [c for c in ordered if c["classification"] == "EMPATE_MULTI_FUERTE"]
            primary = None if multi else (ordered[0]["number"] if ordered else None)
            top_nums = (
                [c["number"] for c in multi]
                if multi
                else [c["number"] for c in ordered[:3]]
            )
            pick = {
                "primary": primary,
                "top_nums": top_nums,
                "multi": [c["number"] for c in multi],
            }
        else:
            pick = _pick_from_result(
                res,
                hypothesis=hypothesis,
                allow_multi=allow_multi,
                threshold=threshold,
                observed=nums,
            )
        hf = sc["historical_fuerte"]
        cand_nums = {c["number"] for c in res.ranked_candidates}
        hist_in_cands += int(hf in cand_nums)
        multi_n += int(bool(pick["multi"]))
        if pick["multi"]:
            if hf in pick["multi"]:
                top2 += 1
                top3 += 1
            # top1 unresolved — not counted as top1 hit
        else:
            top1 += int(pick["primary"] == hf)
            top2 += int(hf in pick["top_nums"][:2])
            top3 += int(hf in pick["top_nums"][:3])
        rows.append(
            {
                "scenario_id": sc["scenario_id"],
                "historical": hf,
                "primary": pick["primary"],
                "multi": pick["multi"],
                "hit_top1": pick["primary"] == hf if not pick["multi"] else False,
                "hit_top2": hf in (pick["multi"] or pick["top_nums"][:2]),
            }
        )
    n = len(use) or 1
    return {
        "n": len(use),
        "top1": top1,
        "top1_rate": top1 / n,
        "top2": top2,
        "top2_rate": top2 / n,
        "top3": top3,
        "top3_rate": top3 / n,
        "hist_in_candidates_rate": hist_in_cands / n,
        "multi_fuerte_rate": multi_n / n,
        "rows": rows,
    }


def run_phase3_lab(*, out_dir: Path | None = None) -> dict[str, Any]:
    root = _repo()
    out = out_dir or (root / "artifacts" / "tiebreak")
    out.mkdir(parents=True, exist_ok=True)

    audited = audit_error_cases()
    (out / "error_cases.json").write_text(
        json.dumps(audited, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    matrix = build_feature_matrix(audited)
    (out / "feature_matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out / "feature_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        if matrix:
            w = csv.DictWriter(f, fieldnames=list(matrix[0].keys()))
            w.writeheader()
            w.writerows(matrix)

    splits = load_splits()
    # TEST LOCKED for selection — only train explore + validation choose
    train = splits["train"]
    val = splits["validation"]
    test = splits["test"]

    # Baseline without tiebreak (sorted observed as Phase2)
    baseline_val = evaluate_split(
        val, hypothesis=None, generator_first=False, limit=200
    )

    hyp_results = {}
    for h in HYPOTHESES:
        tr = evaluate_split(
            train, hypothesis=h, allow_multi=False, generator_first=True, limit=250
        )
        va = evaluate_split(
            val, hypothesis=h, allow_multi=False, generator_first=True, limit=200
        )
        hyp_results[h] = {
            "train": {k: v for k, v in tr.items() if k != "rows"},
            "validation": {k: v for k, v in va.items() if k != "rows"},
            # test intentionally omitted from selection
            "test_locked": True,
        }

    # Socio + multi on val
    socio_multi_val = evaluate_split(
        val,
        hypothesis="TIEBREAK_PROFILE_SOCIO",
        allow_multi=True,
        generator_first=True,
        limit=200,
    )
    hyp_results["TIEBREAK_PROFILE_SOCIO_MULTI"] = {
        "validation": {k: v for k, v in socio_multi_val.items() if k != "rows"},
        "test_locked": True,
    }

    # Select by validation top2 then top1 (no test)
    selectable = {
        k: v
        for k, v in hyp_results.items()
        if k != "TIEBREAK_PROFILE_SOCIO_MULTI"
    }
    best = max(
        selectable.items(),
        key=lambda kv: (
            kv[1]["validation"]["top2_rate"],
            kv[1]["validation"]["top1_rate"],
        ),
    )[0]

    # Final test evaluation ONLY now
    baseline_test = evaluate_split(
        test, hypothesis=None, generator_first=False, limit=200
    )
    selected_test = evaluate_split(
        test,
        hypothesis=best,
        allow_multi=False,
        generator_first=True,
        limit=200,
    )
    selected_multi_test = evaluate_split(
        test,
        hypothesis="TIEBREAK_PROFILE_SOCIO",
        allow_multi=True,
        generator_first=True,
        limit=200,
    )
    engine_test = evaluate_split(
        test,
        hypothesis=None,
        enable_engine_tiebreak=True,
        generator_first=True,
        limit=200,
    )

    # Impact on the original 14
    error_ids = {a["scenario_id"] for a in audited}
    def score_on_errors(eval_rows):
        sub = [r for r in eval_rows if r["scenario_id"] in error_ids]
        if not sub:
            # errors may be in val+test of phase2 sample of 250 — remap via dates
            return {"n": 0}
        return {
            "n": len(sub),
            "top1": sum(r["hit_top1"] for r in sub),
            "top2": sum(r["hit_top2"] for r in sub),
        }

    # Re-eval the 14 with engine
    err_scenarios = []
    all_sc = {r["scenario_id"]: r for rows in splits.values() for r in rows}
    for a in audited:
        err_scenarios.append(all_sc[a["scenario_id"]])
    err_baseline = evaluate_split(
        err_scenarios, hypothesis=None, generator_first=False
    )
    err_selected = evaluate_split(
        err_scenarios,
        hypothesis="TIEBREAK_PROFILE_SOCIO",
        allow_multi=True,
        generator_first=True,
    )

    final = {
        "baseline_validation": {k: v for k, v in baseline_val.items() if k != "rows"},
        "hypothesis_results": hyp_results,
        "selected_rule_for_top1": best,
        "selected_operational_rule": "TIEBREAK_PROFILE_SOCIO + EMPATE_MULTI_FUERTE",
        "practical_threshold": DEFAULT_PRACTICAL_THRESHOLD,
        "validation_selected": {k: v for k, v in selectable[best]["validation"].items()},
        "validation_socio_multi": {
            k: v for k, v in socio_multi_val.items() if k != "rows"
        },
        "test_baseline": {k: v for k, v in baseline_test.items() if k != "rows"},
        "test_selected_single": {k: v for k, v in selected_test.items() if k != "rows"},
        "test_socio_multi": {
            k: v for k, v in selected_multi_test.items() if k != "rows"
        },
        "test_engine_integrated": {k: v for k, v in engine_test.items() if k != "rows"},
        "original_14": {
            "baseline": {k: v for k, v in err_baseline.items() if k != "rows"},
            "socio_multi": {k: v for k, v in err_selected.items() if k != "rows"},
        },
        "production_modified": False,
        "test_used_for_selection": False,
    }
    (out / "hypothesis_results.json").write_text(
        json.dumps(hyp_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "final_benchmark.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return final


if __name__ == "__main__":
    print(json.dumps(run_phase3_lab(), indent=2, ensure_ascii=False)[:3000])
