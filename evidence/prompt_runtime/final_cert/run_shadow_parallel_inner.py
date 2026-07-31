#!/usr/bin/env python3
"""Parallel shadow cert orchestrator — runs inside the API container (one docker exec)."""
from __future__ import annotations

import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Reuse the sequential harness helpers by importing as module after path setup.
import run_shadow_cert as harness

OUT = Path(os.environ.get("SHADOW_OUT", "/tmp/shadow_cert_out"))
OUT.mkdir(parents=True, exist_ok=True)
WORKERS = int(os.environ.get("WORKERS", "4"))
SUITE = Path(os.environ.get("SUITE_PATH", "/tmp/SUITE.json"))


def run_slice(start: int, limit: int, wid: int) -> list[dict]:
    out_dir = OUT / f"w{wid}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = json.loads(SUITE.read_text())["cases"][start : start + limit]
    results = []
    for c in cases:
        sid = None
        try:
            sid = harness.new_session(f"shadow-{c['id']}")
            for u in c.get("setup") or []:
                harness.send(sid, u)
            r = harness.send(sid, c["user"])
            row = harness.extract_row(c, r)
        except Exception as exc:  # noqa: BLE001
            row = {
                "case_id": c["id"],
                "group": c.get("group"),
                "error": str(exc)[:500],
                "factual_score": 0.0,
                "subject_score": 0.0,
                "clarity": 0.0,
                "hallucination": True,
                "fallback": True,
                "eligible_shadow": False,
                "trace": traceback.format_exc()[-400:],
            }
        if sid:
            try:
                harness.api("DELETE", f"/lottery/chat/sessions/{sid}")
            except Exception:  # noqa: BLE001
                pass
        results.append(row)
        print(
            f"W{wid}",
            c["id"],
            row.get("provider_used") or "ERR",
            "guard=",
            row.get("studio_guard_passed"),
            "hall=",
            row.get("hallucination"),
            "lat=",
            int(row.get("legacy_latency_ms") or 0),
            flush=True,
        )
        (out_dir / "PARTIAL.json").write_text(
            json.dumps({"results": results}, indent=2, ensure_ascii=False) + "\n"
        )
    return results


def main() -> None:
    cases = json.loads(SUITE.read_text())["cases"]
    n = len(cases)
    w = max(1, WORKERS)
    base, rem = n // w, n % w
    slices = []
    start = 0
    for i in range(w):
        size = base + (1 if i < rem else 0)
        slices.append((i, start, size))
        start += size

    print(f"parallel workers={w} total={n} slices={slices}", flush=True)
    all_results: list[dict] = []
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs = {ex.submit(run_slice, start, limit, wid): wid for wid, start, limit in slices if limit}
        for fut in as_completed(futs):
            wid = futs[fut]
            try:
                part = fut.result()
                all_results.extend(part)
                print(f"WORKER_DONE {wid} n={len(part)}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"WORKER_FAIL {wid} {exc}", flush=True)
                all_results.append(
                    {
                        "case_id": f"WORKER{wid}",
                        "error": str(exc)[:500],
                        "hallucination": True,
                        "eligible_shadow": False,
                    }
                )

    def sort_key(r):
        cid = str(r.get("case_id") or "")
        digits = "".join(ch for ch in cid if ch.isdigit())
        return (int(digits) if digits else 0, cid)

    results = sorted(all_results, key=sort_key)
    eligible = [x for x in results if x.get("eligible_shadow")]

    def pct(arr, p):
        if not arr:
            return None
        a = sorted(arr)
        return a[min(len(a) - 1, int(p / 100 * (len(a) - 1)))]

    summary = {
        "n": len(results),
        "eligible_shadow": len(eligible),
        "studio_guard_pass": sum(1 for x in eligible if x.get("studio_guard_passed") is True),
        "studio_guard_fail": sum(1 for x in eligible if x.get("studio_guard_passed") is False),
        "extra_subjects_cases": sum(1 for x in results if x.get("extra_subjects")),
        "hallucinations": sum(1 for x in results if x.get("hallucination")),
        "fallback_true": sum(1 for x in results if x.get("fallback")),
        "errors": sum(1 for x in results if x.get("error")),
        "hash_mismatch": sum(1 for x in eligible if x.get("hash_ok") is False),
        "avg_factual": round(sum(x.get("factual_score") or 0 for x in eligible) / max(1, len(eligible)), 4),
        "avg_subject": round(sum(x.get("subject_score") or 0 for x in eligible) / max(1, len(eligible)), 4),
        "avg_clarity": round(sum(x.get("clarity") or 0 for x in eligible) / max(1, len(eligible)), 4),
        "avg_legacy_words": round(
            sum((x.get("legacy_stats") or {}).get("words") or 0 for x in results) / max(1, len(results)), 1
        ),
        "avg_studio_words": round(
            sum((x.get("studio_stats") or {}).get("words") or 0 for x in eligible) / max(1, len(eligible)), 1
        )
        if eligible
        else None,
        "avg_legacy_ms": round(sum(x.get("legacy_latency_ms") or 0 for x in results) / max(1, len(results)), 1),
        "avg_studio_ms": round(sum(x.get("studio_latency_ms") or 0 for x in eligible) / max(1, len(eligible)), 1)
        if eligible
        else None,
        "workers": w,
    }
    if eligible:
        summary.update(
            {
                "studio_p50_ms": pct([x.get("studio_latency_ms") or 0 for x in eligible], 50),
                "studio_p95_ms": pct([x.get("studio_latency_ms") or 0 for x in eligible], 95),
                "studio_p99_ms": pct([x.get("studio_latency_ms") or 0 for x in eligible], 99),
                "wall_p50_ms": pct([x.get("legacy_latency_ms") or 0 for x in results], 50),
                "wall_p95_ms": pct([x.get("legacy_latency_ms") or 0 for x in results], 95),
                "wall_p99_ms": pct([x.get("legacy_latency_ms") or 0 for x in results], 99),
            }
        )
    summary["PASS"] = (
        summary["errors"] == 0
        and summary["extra_subjects_cases"] == 0
        and summary["hallucinations"] == 0
        and summary["studio_guard_fail"] == 0
        and summary["hash_mismatch"] == 0
        and summary["eligible_shadow"] > 0
        and summary["studio_guard_pass"] == summary["eligible_shadow"]
        and summary["n"] == n
    )
    (OUT / "RESULTS.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n"
    )
    print("SUMMARY", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
