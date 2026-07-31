#!/usr/bin/env bash
# Launch Shadow suite with in-container thread pool (avoids concurrent docker exec hangs).
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
echo "suite=$SUITE_NAME total=$TOTAL workers=$WORKERS out=$OUT" | tee -a "$OUT/run.log"

"$DOCKER" exec -e UID_CLEAR="$UID_CLEAR" jaios-lottery-pg-dev bash -lc \
  'psql -U jaios -d jaios_lottery_dev -v ON_ERROR_STOP=1 -c "DELETE FROM lottery_chat_messages WHERE session_id IN (SELECT id FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid); DELETE FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid;"' \
  >/dev/null

"$DOCKER" cp /tmp/routing3_auth.json jaios-workspace-dev-api:/tmp/routing3_auth.json
"$DOCKER" cp "$ROOT/evidence/prompt_runtime/final_cert/${SUITE_NAME}.json" jaios-workspace-dev-api:/tmp/SUITE.json
"$DOCKER" cp "$ROOT/evidence/prompt_runtime/final_cert/run_shadow_cert.py" jaios-workspace-dev-api:/tmp/run_shadow_cert.py
"$DOCKER" cp "$ROOT/evidence/prompt_runtime/final_cert/run_shadow_parallel_inner.py" jaios-workspace-dev-api:/tmp/run_shadow_parallel_inner.py

echo "starting_inner" | tee -a "$OUT/run.log"
"$DOCKER" exec -e PYTHONUNBUFFERED=1 -e WORKERS="$WORKERS" \
  -e SUITE_PATH=/tmp/SUITE.json -e SHADOW_OUT=/tmp/shadow_parallel_out \
  -e EXPECTED_HASH="$HASH" \
  -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
  jaios-workspace-dev-api bash -lc \
  'rm -rf /tmp/shadow_parallel_out && mkdir -p /tmp/shadow_parallel_out && cd /tmp && PYTHONPATH=/app:/tmp python -u /tmp/run_shadow_parallel_inner.py' \
  | tee -a "$OUT/run.log"

"$DOCKER" cp jaios-workspace-dev-api:/tmp/shadow_parallel_out/RESULTS.json "$OUT/RESULTS.json"
python3 - <<PY
import json
from pathlib import Path
p=Path("$OUT/RESULTS.json")
d=json.loads(p.read_text())
print(json.dumps(d["summary"], indent=2, ensure_ascii=False))
fails=[r for r in d["results"] if r.get("hallucination") or r.get("studio_guard_passed") is False or r.get("error")]
print("FAILS", [(r.get("case_id"), (r.get("studio_guard_reason") or r.get("error") or "")[:120]) for r in fails[:30]])
PY
