#!/usr/bin/env bash
# Launch Routing200 inside DEV API (separate from Shadow200).
set -euo pipefail
DOCKER="${DOCKER:-/usr/local/bin/docker}"
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
SUITE_FILE="${1:-$ROOT/evidence/prompt_runtime/final_cert/ROUTING200.json}"
CONCURRENCY="${ROUTING_CONCURRENCY:-1}"
CASE_LIMIT="${CASE_LIMIT:-0}"
CASE_START="${CASE_START:-0}"
UID_CLEAR=$(python3 -c "import json;print(json.load(open('/tmp/routing3_auth.json'))['uid'])")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$ROOT/evidence/prompt_runtime/final_cert/ROUTING200_${STAMP}"
mkdir -p "$OUT"
echo "suite=$SUITE_FILE concurrency=$CONCURRENCY out=$OUT" | tee "$OUT/run.log"

"$DOCKER" exec -e UID_CLEAR="$UID_CLEAR" jaios-lottery-pg-dev bash -lc \
  'psql -U jaios -d jaios_lottery_dev -v ON_ERROR_STOP=1 -c "SET search_path TO jaios; DELETE FROM lottery_chat_messages WHERE session_id IN (SELECT id FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid); DELETE FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid;"' \
  >/dev/null

"$DOCKER" cp /tmp/routing3_auth.json jaios-workspace-dev-api:/tmp/routing3_auth.json
"$DOCKER" cp "$SUITE_FILE" jaios-workspace-dev-api:/tmp/ROUTING200.json
"$DOCKER" cp "$ROOT/evidence/prompt_runtime/final_cert/run_routing200.py" jaios-workspace-dev-api:/tmp/run_routing200.py

"$DOCKER" exec -d -e PYTHONUNBUFFERED=1 \
  -e ROUTING_CONCURRENCY="$CONCURRENCY" \
  -e CASE_LIMIT="$CASE_LIMIT" -e CASE_START="$CASE_START" \
  -e SUITE_PATH=/tmp/ROUTING200.json \
  -e ROUTING_OUT=/tmp/routing200_out \
  -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
  -e ROUTING_MESSAGE_TIMEOUT=180 \
  -e ROUTING_SESSION_TIMEOUT=90 \
  -e ROUTING_MAX_INFRA_RETRIES=1 \
  jaios-workspace-dev-api bash -lc \
  'rm -rf /tmp/routing200_out /tmp/routing200_inner.log && mkdir -p /tmp/routing200_out && cd /tmp && PYTHONPATH=/app:/tmp python -u /tmp/run_routing200.py > /tmp/routing200_inner.log 2>&1'

echo "detached_inner" | tee -a "$OUT/run.log"
echo "$OUT"
