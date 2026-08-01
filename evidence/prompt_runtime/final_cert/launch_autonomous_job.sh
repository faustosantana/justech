#!/usr/bin/env bash
# Launch a long cert job detached. Returns immediately with PID/log/checkpoint paths.
# Usage: launch_autonomous_job.sh SHADOW10|SHADOW25|SHADOW200|CERT200
set -euo pipefail
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
CERT="$ROOT/evidence/prompt_runtime/final_cert"
KIND="${1:?KIND required}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
case "$KIND" in
  SHADOW10) SUITE="$CERT/SHADOW10_ELIGIBLE.json"; LABEL=SHADOW10 ;;
  SHADOW25) SUITE="$CERT/SHADOW25_ELIGIBLE.json"; LABEL=SHADOW25 ;;
  SHADOW200) SUITE="$CERT/SHADOW200_ELIGIBLE_DATASET.json"; LABEL=SHADOW200 ;;
  CERT200) SUITE="$CERT/SHADOW200.json"; LABEL=CERT200 ;;
  *) echo "unknown kind"; exit 2 ;;
esac
OUT="$CERT/${LABEL}_${STAMP}"
mkdir -p "$OUT"

DATASET_HASH=$(shasum -a 256 "$SUITE" | awk '{print $1}')
HARNESS_HASH=$(shasum -a 256 "$CERT/run_shadow_eligible.py" | awk '{print $1}')
FREEZE="$CERT/PROMPT_FREEZE.json"
echo "prompt version: $(python3 -c "import json;print(json.load(open('$FREEZE'))['semantic_version'])")"
echo "version ID: $(python3 -c "import json;print(json.load(open('$FREEZE'))['version_id'])")"
echo "expected hash completo: $(python3 -c "import json;print(json.load(open('$FREEZE'))['compiled_prompt_hash'])")"
echo "hash source: runtime_status (validated against env/freeze)"
echo "dataset hash: $DATASET_HASH"
echo "harness hash: $HARNESS_HASH"

export SKIP_RESTART=1 SHADOW_CONCURRENCY=1
export SHADOW_OUT_DIR="$OUT"
export PROMPT_FREEZE_PATH="$FREEZE"
export EXPECTED_HASH="${EXPECTED_HASH:-}"

# Fully detach from the calling shell/tool session (nohup + stdin closed + disown).
nohup bash -c "
  set -euo pipefail
  \"$CERT/run_shadow_eligible.sh\" \"$SUITE\" \"$LABEL\" >\"$OUT/launch.out\" 2>&1
  echo \$? > \"$OUT/exit_code\"
" </dev/null >"$OUT/host.log" 2>&1 &
HPID=$!
echo "$HPID" > "$OUT/host.pid"
disown "$HPID" 2>/dev/null || true

cat > "$OUT/STATUS.md" <<EOM
kind: $KIND
started: $STAMP
host_pid: $HPID
suite: $SUITE
out: $OUT
prompt_freeze: $FREEZE
status_cmd: docker exec jaios-workspace-dev-api tail -20 /tmp/shadow_eligible_inner.log
checkpoint: docker exec jaios-workspace-dev-api ls -la /tmp/shadow_eligible_out
stop_cmd: docker exec jaios-workspace-dev-api pkill -f run_shadow_eligible.py; kill $HPID
EOM
echo "LAUNCHED kind=$KIND out=$OUT pid=$HPID"
