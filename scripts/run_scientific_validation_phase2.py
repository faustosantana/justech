#!/usr/bin/env python3
"""Run Phase 2 scientific validation pipeline (DEV). Does not touch Production."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.lottery.numeric_relations.analysis_engine.scientific_validation.pipeline import (  # noqa: E402
    run_phase2_pipeline,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=500, help="Max scenarios per split evaluation")
    ap.add_argument("--full", action="store_true", help="No limit (all scenarios)")
    ap.add_argument("--no-benchmark", action="store_true")
    args = ap.parse_args()
    limit = None if args.full else args.limit
    result = run_phase2_pipeline(
        limit=limit, run_full_benchmark=not args.no_benchmark
    )
    summary = {
        "dataset_counts": (result.get("dataset") or {}).get("counts"),
        "historical_match_rate": (result.get("historical") or {}).get("methodology_match_rate"),
        "n_analyses": (result.get("historical") or {}).get("n_analyses"),
        "best_profile": (result.get("calibration") or {}).get("best_methodology_reproduction"),
        "best_variant": (result.get("benchmark") or {}).get("best_blind_variant"),
        "failures": (result.get("error_analysis") or {}).get("n_failures"),
        "production_modified": False,
        "ml_decides_fuerte": False,
        "artifacts": str(ROOT / "artifacts" / "scientific_validation"),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
