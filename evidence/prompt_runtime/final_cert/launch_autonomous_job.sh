#!/usr/bin/env bash
# Launch a durable, run-scoped cert job via `docker exec -d` (no host nohup).
# Survives Cursor/tool shell exit. Returns in a few seconds after liveness check.
# Usage: launch_autonomous_job.sh SHADOW10|SHADOW25|SHADOW200|CERT200|JOB_SMOKE
set -euo pipefail
DOCKER="${DOCKER:-/usr/local/bin/docker}"
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
CERT="$ROOT/evidence/prompt_runtime/final_cert"
KIND="${1:?KIND required}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
case "$KIND" in
  SHADOW10) SUITE="$CERT/SHADOW10_ELIGIBLE.json"; LABEL=SHADOW10; CASE_LIMIT="${CASE_LIMIT:-0}"; SKIP_PRE=0 ;;
  SHADOW25) SUITE="$CERT/SHADOW25_ELIGIBLE.json"; LABEL=SHADOW25; CASE_LIMIT="${CASE_LIMIT:-0}"; SKIP_PRE=0 ;;
  SHADOW200) SUITE="$CERT/SHADOW200_ELIGIBLE_DATASET.json"; LABEL=SHADOW200; CASE_LIMIT="${CASE_LIMIT:-0}"; SKIP_PRE=0 ;;
  CERT200) SUITE="$CERT/SHADOW200.json"; LABEL=CERT200; CASE_LIMIT="${CASE_LIMIT:-0}"; SKIP_PRE=0 ;;
  JOB_SMOKE) SUITE="$CERT/SHADOW10_ELIGIBLE.json"; LABEL=JOB_SMOKE; CASE_LIMIT=0; SKIP_PRE=1 ;;
  *) echo "unknown kind"; exit 2 ;;
esac

RUN_ID="${LABEL}_${STAMP}"
HOST_OUT="$CERT/${RUN_ID}"
CTR_DIR="/tmp/prompt_cert/${RUN_ID}"
FREEZE="$CERT/PROMPT_FREEZE.json"
mkdir -p "$HOST_OUT"

DATASET_HASH=$(shasum -a 256 "$SUITE" | awk '{print $1}')
HARNESS_HASH=$(shasum -a 256 "$CERT/run_shadow_eligible.py" | awk '{print $1}')
echo "prompt version: $(python3 -c "import json;print(json.load(open('$FREEZE'))['semantic_version'])")"
echo "version ID: $(python3 -c "import json;print(json.load(open('$FREEZE'))['version_id'])")"
echo "expected hash completo: $(python3 -c "import json;print(json.load(open('$FREEZE'))['compiled_prompt_hash'])")"
echo "hash source: runtime_status (validated against env/freeze inside container)"
echo "dataset hash: $DATASET_HASH"
echo "harness hash: $HARNESS_HASH"
echo "run_id: $RUN_ID"
echo "container_dir: $CTR_DIR"

# Stage run-scoped assets into the container (foreground; no long worker yet).
"$DOCKER" exec jaios-workspace-dev-api bash -lc "rm -rf '$CTR_DIR' && mkdir -p '$CTR_DIR'"
"$DOCKER" cp /tmp/routing3_auth.json "jaios-workspace-dev-api:$CTR_DIR/routing3_auth.json"
"$DOCKER" cp "$SUITE" "jaios-workspace-dev-api:$CTR_DIR/suite.json"
"$DOCKER" cp "$FREEZE" "jaios-workspace-dev-api:$CTR_DIR/PROMPT_FREEZE.json"
"$DOCKER" cp "$CERT/prompt_hash_precheck.py" "jaios-workspace-dev-api:$CTR_DIR/prompt_hash_precheck.py"
"$DOCKER" cp "$CERT/run_paths.py" "jaios-workspace-dev-api:$CTR_DIR/run_paths.py"
"$DOCKER" cp "$CERT/run_shadow_eligible.py" "jaios-workspace-dev-api:$CTR_DIR/run_shadow_eligible.py"
"$DOCKER" cp "$CERT/job_smoke_worker.py" "jaios-workspace-dev-api:$CTR_DIR/job_smoke_worker.py"
"$DOCKER" cp "$CERT/container_cert_wrapper.sh" "jaios-workspace-dev-api:$CTR_DIR/container_cert_wrapper.sh"
"$DOCKER" exec jaios-workspace-dev-api bash -lc "chmod +x '$CTR_DIR/container_cert_wrapper.sh'"

# Optional chat cleanup (best-effort; does not block durable launch semantics).
if [ "${SKIP_CHAT_CLEANUP:-0}" != "1" ] && [ "$KIND" != "JOB_SMOKE" ]; then
  UID_CLEAR=$(python3 -c "import json;print(json.load(open('/tmp/routing3_auth.json'))['uid'])" 2>/dev/null || true)
  if [ -n "${UID_CLEAR:-}" ]; then
    "$DOCKER" exec -e UID_CLEAR="$UID_CLEAR" jaios-lottery-pg-dev bash -lc \
      'psql -U jaios -d jaios_lottery_dev -v ON_ERROR_STOP=1 -c "DELETE FROM lottery_chat_messages WHERE session_id IN (SELECT id FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid); DELETE FROM lottery_chat_sessions WHERE user_id = '\''$UID_CLEAR'\''::uuid;"' \
      >/dev/null 2>&1 || true
  fi
fi

# Detach ONLY via docker exec -d — independent of Cursor/host shell lifetime.
"$DOCKER" exec -d \
  -e RUN_DIR="$CTR_DIR" \
  -e JOB_KIND="$KIND" \
  -e SKIP_PROMPT_PRECHECK="$SKIP_PRE" \
  -e EXPECTED_HASH="${EXPECTED_HASH:-}" \
  -e PROMPT_FREEZE_PATH="$CTR_DIR/PROMPT_FREEZE.json" \
  -e PRECHECK_AUTH_JSON="$CTR_DIR/routing3_auth.json" \
  -e FORENSIC_BASE_URL=http://127.0.0.1:8000/api/v1 \
  -e SHADOW_OUT="$CTR_DIR" \
  -e SUITE_PATH="$CTR_DIR/suite.json" \
  -e SHADOW_CONCURRENCY="${SHADOW_CONCURRENCY:-1}" \
  -e CASE_LIMIT="$CASE_LIMIT" \
  -e CASE_START="${CASE_START:-0}" \
  -e SHADOW_MESSAGE_TIMEOUT="${SHADOW_MESSAGE_TIMEOUT:-600}" \
  -e SHADOW_SESSION_TIMEOUT="${SHADOW_SESSION_TIMEOUT:-90}" \
  -e SHADOW_MAX_INFRA_RETRIES="${SHADOW_MAX_INFRA_RETRIES:-1}" \
  -e SMOKE_DURATION_SEC="${SMOKE_DURATION_SEC:-75}" \
  -e PYTHONUNBUFFERED=1 \
  jaios-workspace-dev-api \
  "$CTR_DIR/container_cert_wrapper.sh"

# Liveness: worker.pid must appear and stay alive (3–5s).
ALIVE=0
WPID=""
for i in 1 2 3 4 5 6 7 8; do
  sleep 1
  if "$DOCKER" exec jaios-workspace-dev-api bash -lc "test -f '$CTR_DIR/PRECHECK_FAILED'"; then
    "$DOCKER" cp "jaios-workspace-dev-api:$CTR_DIR/." "$HOST_OUT/" >/dev/null 2>&1 || true
    echo "PRECHECK_FAILED" | tee "$HOST_OUT/PRECHECK_FAILED"
    echo 2 > "$HOST_OUT/exit_code"
    echo "LAUNCHED=no reason=PRECHECK_FAILED out=$HOST_OUT"
    exit 2
  fi
  if "$DOCKER" exec jaios-workspace-dev-api bash -lc "test -f '$CTR_DIR/worker.pid'"; then
    WPID=$("$DOCKER" exec jaios-workspace-dev-api bash -lc "cat '$CTR_DIR/worker.pid'")
    if "$DOCKER" exec jaios-workspace-dev-api bash -lc "kill -0 '$WPID' 2>/dev/null"; then
      ALIVE=1
      break
    fi
  fi
done

# Sync status artefacts to host
"$DOCKER" cp "jaios-workspace-dev-api:$CTR_DIR/." "$HOST_OUT/" >/dev/null 2>&1 || true

if [ "$ALIVE" -ne 1 ] || [ -z "$WPID" ]; then
  echo "LAUNCH_FAILED" | tee "$HOST_OUT/LAUNCH_FAILED"
  echo "worker not alive after detach; container_dir=$CTR_DIR" | tee -a "$HOST_OUT/LAUNCH_FAILED"
  echo 1 > "$HOST_OUT/exit_code"
  cat > "$HOST_OUT/STATUS.md" <<EOM
kind: $KIND
run_id: $RUN_ID
started: $STAMP
status: LAUNCH_FAILED
container_dir: $CTR_DIR
out: $HOST_OUT
EOM
  echo "LAUNCHED=no reason=LAUNCH_FAILED out=$HOST_OUT"
  exit 1
fi

echo "$WPID" > "$HOST_OUT/worker.pid"
# Prove survival past launcher return window
sleep 5
if ! "$DOCKER" exec jaios-workspace-dev-api bash -lc "kill -0 '$WPID' 2>/dev/null"; then
  echo "LAUNCH_FAILED" | tee "$HOST_OUT/LAUNCH_FAILED"
  echo "worker pid $WPID died within 5s post-check" | tee -a "$HOST_OUT/LAUNCH_FAILED"
  echo 1 > "$HOST_OUT/exit_code"
  exit 1
fi
echo "alive_after_5s=yes pid=$WPID" | tee "$HOST_OUT/ALIVE_AFTER_5S.txt"

cat > "$HOST_OUT/STATUS.md" <<EOM
kind: $KIND
run_id: $RUN_ID
started: $STAMP
worker_pid: $WPID
container_dir: $CTR_DIR
out: $HOST_OUT
suite: $SUITE
prompt_freeze: $FREEZE
status_cmd: bash $CERT/status_autonomous_job.sh $RUN_ID
stop_cmd: bash $CERT/stop_autonomous_job.sh $RUN_ID
checkpoint: $CTR_DIR/CHECKPOINT.json
heartbeat: $CTR_DIR/heartbeat.json
log: $CTR_DIR/run.log
EOM

echo "LAUNCHED kind=$KIND run_id=$RUN_ID out=$HOST_OUT worker_pid=$WPID container_dir=$CTR_DIR"
