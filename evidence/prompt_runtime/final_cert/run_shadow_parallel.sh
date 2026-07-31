#!/usr/bin/env bash
# Parallel Shadow certification (WORKERS concurrent ranges; session deleted per case).
# Compatible with macOS bash 3.2.
set -euo pipefail
DOCKER="${DOCKER:-/usr/local/bin/docker}"
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
SUITE_NAME="${1:-SHADOW200}"
WORKERS="${WORKERS:-4}"
HASH="${EXPECTED_HASH:-41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9}"
UID_CLEAR=$(python3 -c "import json;print(json.load(open('/tmp/routing3_auth.json'))['uid'])")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$ROOT/evidence/prompt_runtime/final_cert/${SUITE_NAME}_${STAMP}"
mkdir -p "$OUT"
echo "$OUT" > /tmp/shadow_cert_out_dir.txt
: > "$OUT/run.log"

TOTAL=$(python3 -c "import json;print(len(json.load(open('$ROOT/evidence/prompt_runtime/final_cert/${SUITE_NAME}.json'))['cases']))")
echo "suite=$SUITE_NAME total=$TOTAL workers=$WORKERS out=$OUT uid=$UID_CLEAR docker=$DOCKER" | tee -a "$OUT/run.log"

clear_quota() {
  "$DOCKER" exec -e UID_CLEAR="$UID_CLEAR" jaios-lottery-pg-dev bash -lc \
    'psql -U jaios -d jaios_lottery_dev -v ON_ERROR_STOP=1 -c "DELETE FROM lottery_chat_messages WHERE session_id IN (SELECT id FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid); DELETE FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid;"' \
    >/dev/null
}

"$DOCKER" cp /tmp/routing3_auth.json jaios-workspace-dev-api:/tmp/routing3_auth.json
SUITE_FILE="$ROOT/evidence/prompt_runtime/final_cert/${SUITE_NAME}.json"
PY_FILE="$ROOT/evidence/prompt_runtime/final_cert/run_shadow_cert.py"
test -f "$SUITE_FILE"
test -f "$PY_FILE"
"$DOCKER" cp "$SUITE_FILE" jaios-workspace-dev-api:/tmp/SUITE.json
"$DOCKER" cp "$PY_FILE" jaios-workspace-dev-api:/tmp/run_shadow_cert.py
clear_quota
echo "assets_copied" | tee -a "$OUT/run.log"

RANGES=$(python3 - <<PY
n=int("$TOTAL"); w=int("$WORKERS")
base=n//w; rem=n%w
start=0
for i in range(w):
    size=base+(1 if i<rem else 0)
    print(f"{i} {start} {size}")
    start+=size
PY
)

PIDS=""
while read -r wi start limit; do
  [ -z "${wi:-}" ] && continue
  wout="/tmp/shadow_w${wi}"
  echo "=== WORKER $wi start=$start limit=$limit ===" | tee -a "$OUT/run.log"
  (
    set +e
    "$DOCKER" exec -e PYTHONUNBUFFERED=1 -e CASE_START="$start" -e CASE_LIMIT="$limit" \
      -e SUITE_PATH=/tmp/SUITE.json -e SHADOW_OUT="$wout" \
      -e EXPECTED_HASH="$HASH" \
      -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
      jaios-workspace-dev-api bash -lc "mkdir -p $wout && cd /app && PYTHONPATH=/app python -u /tmp/run_shadow_cert.py" \
      > "$OUT/worker_${wi}.log" 2>&1
    ec=$?
    "$DOCKER" cp "jaios-workspace-dev-api:${wout}/RESULTS.json" "$OUT/worker_${wi}.json" 2>>"$OUT/worker_${wi}.log"
    exit $ec
  ) &
  PIDS="$PIDS $!"
done <<EOF
$RANGES
EOF

fail=0
for pid in $PIDS; do
  if ! wait "$pid"; then
    fail=1
  fi
done

python3 - <<PY
import json
from pathlib import Path
out = Path("$OUT")
results=[]
for p in sorted(out.glob("worker_*.json"), key=lambda x: int(x.stem.split("_")[1])):
    results.extend(json.loads(p.read_text())["results"])
def sort_key(r):
    cid=str(r.get("case_id") or "")
    digits="".join(ch for ch in cid if ch.isdigit())
    return (int(digits) if digits else 0, cid)
results.sort(key=sort_key)
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
  "workers":int("$WORKERS"),
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
  and summary["n"]==int("$TOTAL")
)
(out/"RESULTS.json").write_text(json.dumps({"summary":summary,"results":results},indent=2,ensure_ascii=False)+"\n")
print(json.dumps(summary,indent=2,ensure_ascii=False))
fails=[r for r in results if r.get("hallucination") or r.get("studio_guard_passed") is False or r.get("error")]
print("FAILS", [(r.get("case_id"), (r.get("studio_guard_reason") or r.get("error") or "")[:120]) for r in fails[:30]])
PY

exit "$fail"
