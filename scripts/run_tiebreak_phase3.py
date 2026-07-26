#!/usr/bin/env python3
"""Run Phase 3 tiebreak lab and write docs/artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.lottery.numeric_relations.analysis_engine.tiebreak_lab import (  # noqa: E402
    run_phase3_lab,
)


def main() -> int:
    final = run_phase3_lab()
    print(json.dumps({k: v for k, v in final.items() if k != "hypothesis_results"}, indent=2))
    # persist empty prospective placeholder
    (ROOT / "artifacts/tiebreak/prospective_predictions.json").write_text(
        "[]", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
