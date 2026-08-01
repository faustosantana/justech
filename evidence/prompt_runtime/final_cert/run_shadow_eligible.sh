#!/usr/bin/env bash
# Launch eligible shadow runner inside DEV API container (single docker exec).
# Resolves EXPECTED_HASH via runtime status / env / freeze — never a silent rc3.4 default.
set -euo pipefail
DOCKER="${DOCKER:-/usr/local/bin/docker}"
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
CERT="$ROOT/evidence/prompt_runtime/final_cert"
SUITE_FILE="${1:-$CERT/SHADOW200_ELIGIBLE_DATASET.json}"
LABEL="${2:-SHADOW_ELIGIBLE}"
CONCURRENCY="${SHADOW_CONCURRENCY:-1}"
CASE_LIMIT="${CASE_LIMIT:-0}"
CASE_START="${CASE_START:-0}"
FREEZE_FILE="${PROMPT_FREEZE_PATH:-$CERT/PROMPT_FREEZE.json}"
# Optional explicit hash; empty means resolve from runtime status API.
HASH_IN="${EXPECTED_HASH:-}"

if [ -n "${SHADOW_OUT_DIR:-}" ]; then
  OUT="$SHADOW_OUT_DIR"
else
  STAMP=$(date -u +%Y%m%dT%H%M%SZ)
  OUT="$CERT/${LABEL}_${STAMP}"
fi
mkdir -p "$OUT"
echo "$OUT" > /tmp/shadow_eligible_out_dir.txt
echo "suite=$SUITE_FILE label=$LABEL concurrency=$CONCURRENCY out=$OUT" | tee "$OUT/run.log"

UID_CLEAR=$(python3 -c "import json;print(json.load(open('/tmp/routing3_auth.json'))['uid'])")
"$DOCKER" exec -e UID_CLEAR="$UID_CLEAR" jaios-lottery-pg-dev bash -lc \
  'psql -U jaios -d jaios_lottery_dev -v ON_ERROR_STOP=1 -c "DELETE FROM lottery_chat_messages WHERE session_id IN (SELECT id FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid); DELETE FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid;"' \
  >/dev/null

"$DOCKER" cp /tmp/routing3_auth.json jaios-workspace-dev-api:/tmp/routing3_auth.json
"$DOCKER" cp "$SUITE_FILE" jaios-workspace-dev-api:/tmp/SHADOW_ELIGIBLE.json
"$DOCKER" cp "$CERT/prompt_hash_precheck.py" jaios-workspace-dev-api:/tmp/prompt_hash_precheck.py
"$DOCKER" cp "$CERT/run_shadow_eligible.py" jaios-workspace-dev-api:/tmp/run_shadow_eligible.py
"$DOCKER" cp "$FREEZE_FILE" jaios-workspace-dev-api:/tmp/PROMPT_FREEZE.json

# Precheck before detach — abort with nonzero exit; do not create product_fail rows.
set +e
PRECHECK_JSON=$("$DOCKER" exec \
  -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
  -e EXPECTED_HASH="$HASH_IN" \
  -e PROMPT_FREEZE_PATH=/tmp/PROMPT_FREEZE.json \
  -e PYTHONPATH=/app:/tmp \
  jaios-workspace-dev-api \
  python -u /tmp/prompt_hash_precheck.py 2>&1)
PRECHECK_RC=$?
set -e
if [ "$PRECHECK_RC" -ne 0 ]; then
  echo "PROMPT_HASH_PRECHECK_FAILED" | tee -a "$OUT/run.log"
  echo "$PRECHECK_JSON" | tee -a "$OUT/run.log"
  exit 2
fi

echo "$PRECHECK_JSON" | tee "$OUT/PROMPT_HASH_PRECHECK.json" | tee -a "$OUT/run.log"
RESOLVED_HASH=$(python3 -c "import json,sys; print(json.load(sys.stdin)['expected_hash'])" <<<"$PRECHECK_JSON")
HASH_SOURCE=$(python3 -c "import json,sys; print(json.load(sys.stdin)['hash_source'])" <<<"$PRECHECK_JSON")
PROMPT_VERSION=$(python3 -c "import json,sys; print(json.load(sys.stdin)['active_semantic_version'])" <<<"$PRECHECK_JSON")
VERSION_ID=$(python3 -c "import json,sys; print(json.load(sys.stdin)['active_version_id'])" <<<"$PRECHECK_JSON")
DATASET_HASH=$(shasum -a 256 "$SUITE_FILE" | awk '{print $1}')
HARNESS_HASH=$(shasum -a 256 "$CERT/run_shadow_eligible.py" | awk '{print $1}')

cat >> "$OUT/run.log" <<EOM
prompt_version: $PROMPT_VERSION
version_id: $VERSION_ID
expected_hash: $RESOLVED_HASH
hash_source: $HASH_SOURCE
dataset_hash: $DATASET_HASH
harness_hash: $HARNESS_HASH
EOM

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

# Wipe prior checkpoint so this suite starts clean.
"$DOCKER" exec jaios-workspace-dev-api bash -lc 'rm -rf /tmp/shadow_eligible_out /tmp/shadow_eligible_inner.log && mkdir -p /tmp/shadow_eligible_out'

"$DOCKER" exec -d -e PYTHONUNBUFFERED=1 \
  -e SHADOW_CONCURRENCY="$CONCURRENCY" \
  -e CASE_LIMIT="$CASE_LIMIT" -e CASE_START="$CASE_START" \
  -e SUITE_PATH=/tmp/SHADOW_ELIGIBLE.json \
  -e SHADOW_OUT=/tmp/shadow_eligible_out \
  -e EXPECTED_HASH="$RESOLVED_HASH" \
  -e PROMPT_FREEZE_PATH=/tmp/PROMPT_FREEZE.json \
  -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
  -e SHADOW_MESSAGE_TIMEOUT=600 \
  -e SHADOW_SESSION_TIMEOUT=90 \
  -e SHADOW_MAX_INFRA_RETRIES=1 \
  jaios-workspace-dev-api bash -lc \
  'cd /tmp && PYTHONPATH=/app:/tmp python -u /tmp/run_shadow_eligible.py > /tmp/shadow_eligible_inner.log 2>&1'

echo "detached_inner" | tee -a "$OUT/run.log"
echo "$OUT"
