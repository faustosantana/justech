"""Orchestrate Phase 2 A–L without rewriting the engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.lottery.numeric_relations.analysis_engine.scientific_validation.benchmark import (
    run_benchmark,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.calibration_lab import (
    run_calibration_lab,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.dashboard import (
    build_dashboard_payload,
    write_dashboard_html,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.dataset import (
    build_blind_dataset,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.error_analysis import (
    analyze_errors,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.explainability import (
    explain_analysis_decisions,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.historical_validator import (
    run_historical_validation,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.pattern_discovery import (
    discover_patterns,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
    save_json,
    set_phase2_results,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.rule_inventory import (
    build_rule_inventory,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[6]


def run_phase2_pipeline(
    *,
    limit: int | None = 800,
    out_dir: Path | None = None,
    run_full_benchmark: bool = True,
) -> dict[str, Any]:
    """
    Default limit=800 keeps runtime practical while still running hundreds/thousands
    of analyses across calibration×benchmark variants. Pass limit=None for full set.
    """
    out = out_dir or (_root() / "artifacts" / "scientific_validation")
    out.mkdir(parents=True, exist_ok=True)

    # B — blind dataset
    dataset = build_blind_dataset()
    save_json(out / "blind_dataset_meta.json", {k: v for k, v in dataset.items() if k != "splits"})
    for split, rows in dataset["splits"].items():
        save_json(out / f"split_{split}.json", rows)

    # Use validation+test for evaluation; train reserved for pattern mining only
    train = dataset["splits"]["train"]
    val = dataset["splits"]["validation"]
    test = dataset["splits"]["test"]
    eval_set = val + test

    # C — historical validation (primary socio profile, no derivations for methodology)
    historical = run_historical_validation(
        eval_set, variant="perfil_socio", limit=limit
    )
    save_json(out / "historical_validation_socio.json", historical)

    # D — errors
    error_analysis = analyze_errors(historical["rows"])
    save_json(out / "error_analysis.json", error_analysis)

    # E — patterns from TRAIN matches (no leakage of test labels into discovery narrative)
    train_hist = run_historical_validation(train, variant="perfil_socio", limit=limit)
    patterns = discover_patterns(train_hist["rows"], min_support=5)
    save_json(out / "patterns_discovered.json", patterns)

    # F — calibration
    calibration = run_calibration_lab(eval_set, limit=limit)
    # strip nested full rows for summary size
    cal_summary = {
        k: v
        for k, v in calibration.items()
        if k != "full"
    }
    cal_summary["details"] = calibration.get("details")
    save_json(out / "calibration_lab.json", cal_summary)

    # H — benchmark
    benchmark = None
    if run_full_benchmark:
        benchmark = run_benchmark(eval_set, limit=limit)
        save_json(
            out / "benchmark.json",
            {
                "blind_benchmark_table": benchmark["blind_benchmark_table"],
                "best_blind_variant": benchmark["best_blind_variant"],
                "manual_benchmark_final": benchmark["manual_benchmark_final"],
                "note": benchmark["note"],
            },
        )

    # G — explainability samples
    explain_samples = {
        "35_14": explain_analysis_decisions([35, 14], mode="socio"),
        "39_58": explain_analysis_decisions([39, 58], mode="socio"),
        "49_44_70": explain_analysis_decisions([49, 44, 70], mode="socio"),
    }
    save_json(out / "explainability_samples.json", explain_samples)

    phase2 = {
        "dataset": {k: v for k, v in dataset.items() if k != "splits"},
        "historical": {k: v for k, v in historical.items() if k != "rows"},
        "historical_rows_path": str(out / "historical_validation_socio.json"),
        "error_analysis": error_analysis,
        "patterns": patterns,
        "calibration": cal_summary,
        "benchmark": None
        if benchmark is None
        else {
            "blind_benchmark_table": benchmark["blind_benchmark_table"],
            "best_blind_variant": benchmark["best_blind_variant"],
            "manual_benchmark_final": benchmark["manual_benchmark_final"],
        },
        "explainability_samples": explain_samples,
        "production_modified": False,
        "ml_decides_fuerte": False,
    }
    # keep rows available in memory store via historical file reload if needed
    phase2["historical"]["rows"] = historical["rows"]
    if calibration.get("full"):
        phase2["calibration"]["full"] = {
            k: {kk: vv for kk, vv in v.items() if kk != "rows"}
            for k, v in calibration["full"].items()
        }

    # A — rule inventory (after metrics)
    phase2["rule_inventory"] = build_rule_inventory(metrics=phase2)
    save_json(out / "rule_inventory.json", phase2["rule_inventory"])

    # I — dashboard
    dash = build_dashboard_payload(phase2)
    save_json(out / "dashboard.json", dash)
    write_dashboard_html(dash, out / "dashboard.html")
    phase2["dashboard"] = dash

    # compact summary without all rows
    summary = dict(phase2)
    summary["historical"] = {k: v for k, v in phase2["historical"].items() if k != "rows"}
    save_json(out / "phase2_summary.json", summary)
    set_phase2_results(summary)

    return phase2
