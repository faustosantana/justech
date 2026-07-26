#!/usr/bin/env python3
"""Run Complete Analysis Engine backtest on manual reconstruction scenarios."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.lottery.numeric_relations.analysis_engine.backtest_engine import (  # noqa: E402
    manual_case_scenarios,
    run_backtest,
)
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (  # noqa: E402
    run_complete_analysis,
)


def main() -> int:
    out_dir = ROOT / "artifacts" / "complete_analysis_engine"
    out_dir.mkdir(parents=True, exist_ok=True)

    rankings = []
    for sc in manual_case_scenarios():
        r = run_complete_analysis(
            {
                "numbers": sc["numbers"],
                "date": sc["date"],
                "mode": "manual_reconstruido",
                "create_signals": False,
            },
            persist=False,
        )
        primary = r.primary_signal or {}
        rankings.append(
            {
                "id": sc["id"],
                "inputs": sc["numbers"],
                "expected": sc["expected"],
                "produced": primary.get("number"),
                "classification": primary.get("classification"),
                "match": primary.get("number") == sc["expected"],
                "ranked": [
                    {
                        "n": c["number"],
                        "cls": c["classification"],
                        "score": c["total_score"],
                        "confidence": c["analytical_confidence"],
                    }
                    for c in r.ranked_candidates[:5]
                ],
                "evidence_summary": r.evidence_summary,
                "graph_complete_before_discovery": r.graph_complete_before_discovery,
            }
        )

    bt = run_backtest(manual_case_scenarios(), profile="manual_reconstruido")
    (out_dir / "manual_case_rankings.json").write_text(
        json.dumps(rankings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "backtest_manual_cases.json").write_text(
        json.dumps(bt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"rankings": rankings, "backtest_id": bt["backtest_id"]}, indent=2))
    return 0 if all(x["match"] for x in rankings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
