#!/usr/bin/env bash
# Runs INSIDE jaios-workspace-dev-api via `docker exec -d`.
# Owns precheck + worker lifecycle for one run-scoped directory.
set -euo pipefail
RUN_DIR="${RUN_DIR:?RUN_DIR required}"
JOB_KIND="${JOB_KIND:?JOB_KIND required}"
cd "$RUN_DIR"
echo $$ > "$RUN_DIR/wrapper.pid"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN_DIR/started_at"
echo "STARTING" > "$RUN_DIR/status.txt"

export PYTHONPATH="/app:${RUN_DIR}:/tmp${PYTHONPATH:+:$PYTHONPATH}"
export FORENSIC_BASE_URL="${FORENSIC_BASE_URL:-http://127.0.0.1:8000/api/v1}"
export PROMPT_FREEZE_PATH="${PROMPT_FREEZE_PATH:-$RUN_DIR/PROMPT_FREEZE.json}"
export PRECHECK_AUTH_JSON="${PRECHECK_AUTH_JSON:-$RUN_DIR/routing3_auth.json}"
export SHADOW_OUT="$RUN_DIR"
export SUITE_PATH="${SUITE_PATH:-$RUN_DIR/suite.json}"

_finish() {
  local ec=$?
  echo "$ec" > "$RUN_DIR/exit_code"
  if [ "$ec" -eq 0 ]; then
    echo "COMPLETED" > "$RUN_DIR/status.txt"
  elif [ -f "$RUN_DIR/PRECHECK_FAILED" ]; then
    echo "PRECHECK_FAILED" > "$RUN_DIR/status.txt"
  else
    echo "FAILED" > "$RUN_DIR/status.txt"
  fi
  exit "$ec"
}
trap _finish EXIT

if [ "${SKIP_PROMPT_PRECHECK:-0}" != "1" ]; then
  set +e
  PRE_OUT=$(python -u "$RUN_DIR/prompt_hash_precheck.py" 2>&1)
  PRE_RC=$?
  set -e
  if [ "$PRE_RC" -ne 0 ]; then
    echo "PRECHECK_FAILED" > "$RUN_DIR/PRECHECK_FAILED"
    echo "$PRE_OUT" | tee "$RUN_DIR/run.log" >/dev/null
    echo "$PRE_OUT" > "$RUN_DIR/precheck.err"
    echo "PROMPT_HASH_PRECHECK_FAILED" >> "$RUN_DIR/run.log"
    exit 2
  fi
  echo "$PRE_OUT" > "$RUN_DIR/PROMPT_HASH_PRECHECK.json"
  # Resolve EXPECTED_HASH for the worker from precheck JSON when unset.
  if [ -z "${EXPECTED_HASH:-}" ]; then
    EXPECTED_HASH=$(python -c "import json;print(json.load(open('$RUN_DIR/PROMPT_HASH_PRECHECK.json'))['expected_hash'])")
    export EXPECTED_HASH
  fi
fi

if [ "$JOB_KIND" = "JOB_SMOKE" ]; then
  python -u "$RUN_DIR/job_smoke_worker.py" >>"$RUN_DIR/run.log" 2>&1 &
else
  python -u "$RUN_DIR/run_shadow_eligible.py" >>"$RUN_DIR/run.log" 2>&1 &
fi
WPID=$!
echo "$WPID" > "$RUN_DIR/worker.pid"
echo "RUNNING" > "$RUN_DIR/status.txt"
wait "$WPID"
exit $?
