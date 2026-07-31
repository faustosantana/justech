#!/usr/bin/env bash
# Launch eligible shadow runner inside DEV API container (single docker exec).
set -euo pipefail
DOCKER="${DOCKER:-/usr/local/bin/docker}"
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
SUITE_FILE="${1:-$ROOT/evidence/prompt_runtime/final_cert/SHADOW200_ELIGIBLE_DATASET.json}"
LABEL="${2:-SHADOW_ELIGIBLE}"
CONCURRENCY="${SHADOW_CONCURRENCY:-1}"
CASE_LIMIT="${CASE_LIMIT:-0}"
CASE_START="${CASE_START:-0}"
HASH="${EXPECTED_HASH:-41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9}"
UID_CLEAR=$(python3 -c "import json;print(json.load(open('/tmp/routing3_auth.json'))['uid'])")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$ROOT/evidence/prompt_runtime/final_cert/${LABEL}_${STAMP}"
mkdir -p "$OUT"
echo "$OUT" > /tmp/shadow_eligible_out_dir.txt
echo "suite=$SUITE_FILE label=$LABEL concurrency=$CONCURRENCY out=$OUT" | tee "$OUT/run.log"

"$DOCKER" exec -e UID_CLEAR="$UID_CLEAR" jaios-lottery-pg-dev bash -lc \
  'psql -U jaios -d jaios_lottery_dev -v ON_ERROR_STOP=1 -c "DELETE FROM lottery_chat_messages WHERE session_id IN (SELECT id FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid); DELETE FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid;"' \
  >/dev/null

"$DOCKER" cp /tmp/routing3_auth.json jaios-workspace-dev-api:/tmp/routing3_auth.json
"$DOCKER" cp "$SUITE_FILE" jaios-workspace-dev-api:/tmp/SHADOW_ELIGIBLE.json
"$DOCKER" cp "$ROOT/evidence/prompt_runtime/final_cert/run_shadow_eligible.py" jaios-workspace-dev-api:/tmp/run_shadow_eligible.py

if [ "${SKIP_RESTART:-0}" != "1" ]; then
  "$DOCKER" cp "$ROOT/backend/app/core/security.py" jaios-workspace-dev-api:/app/app/core/security.py
  "$DOCKER" cp "$ROOT/backend/app/core/auth_trace.py" jaios-workspace-dev-api:/app/app/core/auth_trace.py
  "$DOCKER" cp "$ROOT/backend/app/api/deps.py" jaios-workspace-dev-api:/app/app/api/deps.py
  "$DOCKER" cp "$ROOT/backend/app/lottery/ai/analyst_reasoning/factual_guard.py" \
    jaios-workspace-dev-api:/app/app/lottery/ai/analyst_reasoning/factual_guard.py
  "$DOCKER" restart jaios-workspace-dev-api >/dev/null
  for i in $(seq 1 40); do
    st=$("$DOCKER" inspect -f '{{.State.Health.Status}}' jaios-workspace-dev-api 2>/dev/null || echo starting)
    [ "$st" = "healthy" ] && break
    sleep 3
  done
  echo "api_healthy" | tee -a "$OUT/run.log"
else
  echo "skip_restart" | tee -a "$OUT/run.log"
fi

"$DOCKER" exec -d -e PYTHONUNBUFFERED=1 \
  -e SHADOW_CONCURRENCY="$CONCURRENCY" \
  -e CASE_LIMIT="$CASE_LIMIT" -e CASE_START="$CASE_START" \
  -e SUITE_PATH=/tmp/SHADOW_ELIGIBLE.json \
  -e SHADOW_OUT=/tmp/shadow_eligible_out \
  -e EXPECTED_HASH="$HASH" \
  -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
  -e SHADOW_MESSAGE_TIMEOUT=600 \
  -e SHADOW_SESSION_TIMEOUT=90 \
  -e SHADOW_MAX_INFRA_RETRIES=1 \
  jaios-workspace-dev-api bash -lc \
  'rm -rf /tmp/shadow_eligible_out /tmp/shadow_eligible_inner.log && mkdir -p /tmp/shadow_eligible_out && cd /tmp && PYTHONPATH=/app:/tmp python -u /tmp/run_shadow_eligible.py > /tmp/shadow_eligible_inner.log 2>&1'

echo "detached_inner" | tee -a "$OUT/run.log"
echo "$OUT"
