#!/usr/bin/env python3
"""Short durable detach smoke worker (no LLM). Writes run-scoped heartbeat + summary."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(os.environ.get("SHADOW_OUT", ".")).resolve()
OUT.mkdir(parents=True, exist_ok=True)
DURATION = float(os.environ.get("SMOKE_DURATION_SEC", "75"))
HB_EVERY = float(os.environ.get("SMOKE_HEARTBEAT_SEC", "10"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    started = time.time()
    (OUT / "started_at").write_text(_now() + "\n", encoding="utf-8")
    n = 0
    while True:
        elapsed = time.time() - started
        n += 1
        hb = {
            "n": n,
            "elapsed_s": round(elapsed, 2),
            "eta_s": max(0, round(DURATION - elapsed, 2)),
            "at": _now(),
            "alive": True,
        }
        (OUT / "heartbeat.json").write_text(json.dumps(hb, indent=2) + "\n", encoding="utf-8")
        print(f"HEARTBEAT n={n} elapsed_s={int(elapsed)} eta_s={int(hb['eta_s'])}", flush=True)
        if elapsed >= DURATION:
            break
        time.sleep(min(HB_EVERY, max(0.5, DURATION - elapsed)))

    summary = {
        "kind": "JOB_SMOKE",
        "PASS": True,
        "duration_s": round(time.time() - started, 2),
        "heartbeats": n,
        "run_dir": str(OUT),
        "completed_at": _now(),
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("SUMMARY", json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
