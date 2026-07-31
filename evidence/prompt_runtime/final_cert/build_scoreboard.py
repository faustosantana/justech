#!/usr/bin/env python3
"""Build Legacy vs Studio scoreboard from Shadow RESULTS.json (no runtime changes)."""
from __future__ import annotations

import json
import statistics
from pathlib import Path


def pct(arr, p):
    if not arr:
        return None
    a = sorted(arr)
    return a[min(len(a) - 1, int(p / 100 * (len(a) - 1)))]


def analyze(path: Path) -> dict:
    data = json.loads(path.read_text())
    results = data["results"]
    eligible = [r for r in results if r.get("eligible_shadow")]
    legacy_words = [(r.get("legacy_stats") or {}).get("words") or 0 for r in results]
    studio_words = [(r.get("studio_stats") or {}).get("words") or 0 for r in eligible]
    legacy_ms = [r.get("legacy_latency_ms") or 0 for r in results]
    studio_ms = [r.get("studio_latency_ms") or 0 for r in eligible]
    return {
        "source": str(path),
        "n": len(results),
        "eligible": len(eligible),
        "factual_avg": round(sum(r.get("factual_score") or 0 for r in eligible) / max(1, len(eligible)), 4),
        "subject_avg": round(sum(r.get("subject_score") or 0 for r in eligible) / max(1, len(eligible)), 4),
        "clarity_avg": round(sum(r.get("clarity") or 0 for r in eligible) / max(1, len(eligible)), 4),
        "hallucinations": sum(1 for r in results if r.get("hallucination")),
        "extra_subjects": sum(1 for r in results if r.get("extra_subjects")),
        "missing_subjects": sum(1 for r in results if r.get("missing_subjects")),
        "altered_subjects": sum(1 for r in results if r.get("altered_subjects")),
        "fallback": sum(1 for r in results if r.get("fallback")),
        "legacy_words_avg": round(sum(legacy_words) / max(1, len(legacy_words)), 1),
        "studio_words_avg": round(sum(studio_words) / max(1, len(studio_words)), 1) if studio_words else None,
        "legacy_ms_p50": pct(legacy_ms, 50),
        "legacy_ms_p95": pct(legacy_ms, 95),
        "studio_ms_p50": pct(studio_ms, 50),
        "studio_ms_p95": pct(studio_ms, 95),
        "studio_guard_pass": sum(1 for r in eligible if r.get("studio_guard_passed") is True),
        "studio_guard_fail": sum(1 for r in eligible if r.get("studio_guard_passed") is False),
        "PASS": data.get("summary", {}).get("PASS"),
    }


def md(score: dict) -> str:
    return f"""# Legacy vs Studio Scoreboard

**Source:** `{score['source']}`  
**Frozen prompt:** 7.0.0-rc3.4  

| Metric | Legacy (visible) | Studio (shadow) |
|--------|------------------|-----------------|
| Cases | {score['n']} | eligible {score['eligible']} |
| Factual score (avg) | template/guard path | {score['factual_avg']} |
| Subject score (avg) | n/a (visible uses formatter) | {score['subject_avg']} |
| Clarity (avg heuristic) | — | {score['clarity_avg']} |
| Avg words | {score['legacy_words_avg']} | {score['studio_words_avg']} |
| Latency p50 (ms) | {score['legacy_ms_p50']} | {score['studio_ms_p50']} |
| Latency p95 (ms) | {score['legacy_ms_p95']} | {score['studio_ms_p95']} |
| Hallucinations | — | {score['hallucinations']} |
| Extra subjects | — | {score['extra_subjects']} |
| Missing subjects | — | {score['missing_subjects']} |
| Altered subjects | — | {score['altered_subjects']} |
| Fallback | {score['fallback']} | (included) |
| Guard pass/fail | — | {score['studio_guard_pass']}/{score['studio_guard_fail']} |

**Suite PASS:** {score['PASS']}
"""


if __name__ == "__main__":
    import sys

    p = Path(sys.argv[1])
    s = analyze(p)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else p.parent / "SCOREBOARD.json"
    out.write_text(json.dumps(s, indent=2) + "\n")
    md_path = out.with_suffix(".md") if out.suffix == ".json" else Path(str(out) + ".md")
    # Prefer docs path when provided as third arg
    if len(sys.argv) > 3:
        md_path = Path(sys.argv[3])
    md_path.write_text(md(s))
    print(json.dumps(s, indent=2))
