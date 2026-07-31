#!/usr/bin/env bash
# Batched Shadow certification (clears chat session quota every BATCH_SIZE cases).
set -euo pipefail
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
SUITE_NAME="${1:-SHADOW200}"
BATCH_SIZE="${BATCH_SIZE:-10}"
HASH="${EXPECTED_HASH:-41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9}"
UID_CLEAR=$(python3 -c "import json;print(json.load(open('/tmp/routing3_auth.json'))['uid'])")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$ROOT/evidence/prompt_runtime/final_cert/${SUITE_NAME}_${STAMP}"
mkdir -p "$OUT"
echo "$OUT" > /tmp/shadow_cert_out_dir.txt
: > "$OUT/run.log"

TOTAL=$(python3 -c "import json;print(len(json.load(open('$ROOT/evidence/prompt_runtime/final_cert/${SUITE_NAME}.json'))['cases']))")
echo "suite=$SUITE_NAME total=$TOTAL out=$OUT uid=$UID_CLEAR" | tee -a "$OUT/run.log"

clear_quota() {
  # UUID via env avoids shell quoting traps that truncate the literal mid-string.
  docker exec -e UID_CLEAR="$UID_CLEAR" jaios-lottery-pg-dev bash -lc \
    'psql -U jaios -d jaios_lottery_dev -v ON_ERROR_STOP=1 -c "DELETE FROM lottery_chat_messages WHERE session_id IN (SELECT id FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid); DELETE FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid;"' \
    >/dev/null
}

docker cp /tmp/routing3_auth.json jaios-workspace-dev-api:/tmp/routing3_auth.json
docker cp "$ROOT/evidence/prompt_runtime/final_cert/${SUITE_NAME}.json" jaios-workspace-dev-api:/tmp/SUITE.json
docker cp "$ROOT/evidence/prompt_runtime/final_cert/run_shadow_cert.py" jaios-workspace-dev-api:/tmp/run_shadow_cert.py

starts=$(python3 - <<PY
n=int("$TOTAL"); bs=int("$BATCH_SIZE")
print(" ".join(str(i) for i in range(0,n,bs)))
PY
)

for start in $starts; do
  clear_quota
  echo "=== BATCH start=$start ===" | tee -a "$OUT/run.log"
  docker exec -e PYTHONUNBUFFERED=1 -e CASE_START=$start -e CASE_LIMIT=$BATCH_SIZE \
    -e SUITE_PATH=/tmp/SUITE.json -e SHADOW_OUT=/tmp/shadow_batch \
    -e EXPECTED_HASH="$HASH" \
    -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
    jaios-workspace-dev-api bash -lc 'mkdir -p /tmp/shadow_batch && cd /app && PYTHONPATH=/app python -u /tmp/run_shadow_cert.py' \
    | tee -a "$OUT/run.log"
  docker cp jaios-workspace-dev-api:/tmp/shadow_batch/RESULTS.json "$OUT/batch_${start}.json"
done

python3 - <<PY
import json
from pathlib import Path
out = Path("$OUT")
results=[]
for p in sorted(out.glob("batch_*.json"), key=lambda x: int(x.stem.split("_")[1])):
    results.extend(json.loads(p.read_text())["results"])
eligible=[x for x in results if x.get("eligible_shadow")]
summary={
  "suite":"$SUITE_NAME",
  "n":len(results),
  "eligible_shadow":len(eligible),
  "studio_guard_pass":sum(1 for x in eligible if x.get("studio_guard_passed") is True),
  "studio_guard_fail":sum(1 for x in eligible if x.get("studio_guard_passed") is False),
  "extra_subjects_cases":sum(1 for x in results if x.get("extra_subjects")),
  "hallucinations":sum(1 for x in results if x.get("hallucination")),
  "fallback_true":sum(1 for x in results if x.get("fallback")),
  "errors":sum(1 for x in results if x.get("error")),
  "hash_mismatch":sum(1 for x in eligible if x.get("hash_ok") is False),
  "avg_factual":round(sum(x.get("factual_score") or 0 for x in eligible)/max(1,len(eligible)),4),
  "avg_subject":round(sum(x.get("subject_score") or 0 for x in eligible)/max(1,len(eligible)),4),
  "avg_clarity":round(sum(x.get("clarity") or 0 for x in eligible)/max(1,len(eligible)),4),
  "avg_legacy_words":round(sum((x.get("legacy_stats") or {}).get("words") or 0 for x in results)/max(1,len(results)),1),
  "avg_studio_words":round(sum((x.get("studio_stats") or {}).get("words") or 0 for x in eligible)/max(1,len(eligible)),1) if eligible else None,
  "avg_legacy_ms":round(sum(x.get("legacy_latency_ms") or 0 for x in results)/max(1,len(results)),1),
  "avg_studio_ms":round(sum(x.get("studio_latency_ms") or 0 for x in eligible)/max(1,len(eligible)),1) if eligible else None,
}
if eligible:
  lats=sorted(x.get("studio_latency_ms") or 0 for x in eligible)
  walls=sorted(x.get("legacy_latency_ms") or 0 for x in results)
  def pct(a,p):
    return a[min(len(a)-1, int(p/100*(len(a)-1)))]
  summary.update({
    "studio_p50_ms":pct(lats,50),"studio_p95_ms":pct(lats,95),"studio_p99_ms":pct(lats,99),
    "wall_p50_ms":pct(walls,50),"wall_p95_ms":pct(walls,95),"wall_p99_ms":pct(walls,99),
  })
summary["PASS"]=(
  summary["errors"]==0 and summary["extra_subjects_cases"]==0 and summary["hallucinations"]==0
  and summary["studio_guard_fail"]==0 and summary["hash_mismatch"]==0
  and summary["eligible_shadow"]>0 and summary["studio_guard_pass"]==summary["eligible_shadow"]
)
(out/"RESULTS.json").write_text(json.dumps({"summary":summary,"results":results},indent=2,ensure_ascii=False)+"\n")
print(json.dumps(summary,indent=2,ensure_ascii=False))
fails=[r for r in results if r.get("hallucination") or r.get("studio_guard_passed") is False or r.get("error")]
print("FAILS", [(r.get("case_id"), (r.get("studio_guard_reason") or r.get("error") or "")[:120]) for r in fails[:30]])
PY
