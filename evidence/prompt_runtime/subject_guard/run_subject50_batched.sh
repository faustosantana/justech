#!/usr/bin/env bash
# Run Subject50 in batches of 10, clearing chat quota between batches.
set -euo pipefail
BACKUP=$(cat /tmp/prti_phase3_backup.txt)
OUT="$BACKUP/subject50"
mkdir -p "$OUT"
HASH="${EXPECTED_HASH:-34b8114fc5840ac6725fc9c3c65b7ed3ef7cb62ce078c398e699b5eb7c9a154e}"
UID_CLEAR=e520ca09-882a-4e8f-8d73-8045dc3c6245
: > "$OUT/batched_run.log"

clear_quota() {
  docker exec jaios-lottery-pg-dev psql -U jaios -d jaios_lottery_dev -v ON_ERROR_STOP=1 -c "
DELETE FROM lottery_chat_messages WHERE session_id IN (
  SELECT id FROM lottery_chat_sessions WHERE user_id='${UID_CLEAR}'
);
DELETE FROM lottery_chat_sessions WHERE user_id='${UID_CLEAR}';
" >/dev/null
}

docker cp /tmp/routing3_auth.json jaios-workspace-dev-api:/tmp/routing3_auth.json
docker cp /Users/faustosantana/Projects/justech-forensic-audit/evidence/prompt_runtime/subject_guard/SUBJECT50.json jaios-workspace-dev-api:/tmp/SUBJECT50.json
docker cp /Users/faustosantana/Projects/justech-forensic-audit/evidence/prompt_runtime/subject_guard/run_subject50.py jaios-workspace-dev-api:/tmp/run_subject50.py

for start in 0 10 20 30 40; do
  clear_quota
  echo "=== BATCH start=$start ===" | tee -a "$OUT/batched_run.log"
  docker exec -e PYTHONUNBUFFERED=1 -e CASE_START=$start -e CASE_LIMIT=10 \
    -e SUITE_PATH=/tmp/SUBJECT50.json -e SUBJECT_OUT=/tmp/subject50_batch \
    -e EXPECTED_HASH="$HASH" \
    -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
    jaios-workspace-dev-api bash -lc 'mkdir -p /tmp/subject50_batch && cd /app && PYTHONPATH=/app python -u /tmp/run_subject50.py' \
    | tee -a "$OUT/batched_run.log"
  docker cp jaios-workspace-dev-api:/tmp/subject50_batch/SUBJECT50_RESULTS.json "$OUT/batch_${start}.json"
done

python3 - <<'PY'
import json
from pathlib import Path
out = Path(open("/tmp/prti_phase3_backup.txt").read().strip()) / "subject50"
results = []
for start in (0, 10, 20, 30, 40):
    p = out / f"batch_{start}.json"
    results.extend(json.loads(p.read_text())["results"])
shadowed = [x for x in results if x.get("studio_guard_passed") is not None]
summary = {
    "n": len(results),
    "with_shadow": len(shadowed),
    "subject_pass": sum(1 for x in results if x.get("subject_pass") is True),
    "subject_fail": sum(1 for x in results if x.get("subject_pass") is False),
    "subject_na": sum(1 for x in results if x.get("subject_pass") is None),
    "extra_subjects_cases": sum(1 for x in results if x.get("extra_subjects")),
    "missing_subjects_cases": sum(1 for x in results if x.get("missing_subjects")),
    "altered_subjects_cases": sum(1 for x in results if x.get("altered_subjects")),
    "fallback_true": sum(
        1 for x in results if (x.get("prompt_runtime") or {}).get("fallback_used") is True
    ),
    "errors": sum(1 for x in results if x.get("error")),
    "avg_legacy_words": round(
        sum((x.get("legacy_stats") or {}).get("words") or 0 for x in results) / max(1, len(results)), 1
    ),
    "avg_studio_words": round(
        sum((x.get("studio_stats") or {}).get("words") or 0 for x in shadowed) / max(1, len(shadowed)), 1
    )
    if shadowed
    else None,
    "avg_legacy_ms": round(sum(x.get("legacy_latency_ms") or 0 for x in results) / max(1, len(results)), 1),
    "avg_studio_ms": round(
        sum(x.get("studio_latency_ms") or 0 for x in shadowed) / max(1, len(shadowed)), 1
    )
    if shadowed
    else None,
}
eligible = [x for x in results if x.get("subject_pass") is not None]
summary["eligible"] = len(eligible)
summary["pass_rate"] = f"{summary['subject_pass']}/{len(eligible)}" if eligible else "0/0"
summary["PASS"] = (
    bool(eligible)
    and summary["subject_pass"] == len(eligible)
    and summary["extra_subjects_cases"] == 0
    and summary["errors"] == 0
)
(out / "SUBJECT50_RESULTS.json").write_text(
    json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n"
)
print(json.dumps(summary, indent=2, ensure_ascii=False))
fails = [r for r in results if r.get("subject_pass") is False]
print("FAILS", [(r["case_id"], (r.get("studio_guard_reason") or r.get("error") or "")[:100]) for r in fails])
PY
