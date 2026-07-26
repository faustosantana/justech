#!/usr/bin/env python3
"""CLI: run full historical manual-logic audit (FEATURED_SEVEN, read-only)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.lottery.numeric_relations.historical_audit_runner import (  # noqa: E402
    DEFAULT_DEV_DSN,
    EVIDENCE_DIR,
    run_historical_audit,
)
from app.lottery.numeric_relations.historical_manual_audit import SEED_DEFAULT  # noqa: E402


async def main() -> int:
    payload = await run_historical_audit(
        dsn=DEFAULT_DEV_DSN,
        seed=SEED_DEFAULT,
        write_files=True,
        out_dir=EVIDENCE_DIR,
    )
    s = payload["summary"]
    print(
        json.dumps(
            {
                "audit_id": payload["audit_id"],
                "dates_analyzed": s["dates_analyzed"],
                "population": s["population_cases"],
                "sample": len(payload["cases"]),
                "sample_ids": s["sample_case_ids"],
                "sample_verdicts": {c["id"]: c["verdict"] for c in payload["cases"]},
                "population_next_day": s["population_metrics"]["windows"]["next_calendar_day"],
                "baselines_lift_vs_random_k": s["random_baselines"].get(
                    "lift_official_vs_random_same_k"
                ),
                "logic_verdict": s["logic_verdict"],
                "j11a_gate": s["j11a_gate"],
                "featured": s["featured_seven"],
                "draws": s["draw_count_all"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
