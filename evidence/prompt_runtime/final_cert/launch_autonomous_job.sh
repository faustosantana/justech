#!/usr/bin/env bash
# Launch a long cert job detached. Returns immediately with PID/log/checkpoint paths.
# Usage: launch_autonomous_job.sh SHADOW10|SHADOW25|SHADOW200|CERT200
set -euo pipefail
DOCKER="${DOCKER:-/usr/local/bin/docker}"
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
KIND="${1:?KIND required}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
case "$KIND" in
  SHADOW10) SUITE="$ROOT/evidence/prompt_runtime/final_cert/SHADOW10_ELIGIBLE.json"; LABEL=SHADOW10 ;;
  SHADOW25) SUITE="$ROOT/evidence/prompt_runtime/final_cert/SHADOW25_ELIGIBLE.json"; LABEL=SHADOW25 ;;
  SHADOW200) SUITE="$ROOT/evidence/prompt_runtime/final_cert/SHADOW200_ELIGIBLE_DATASET.json"; LABEL=SHADOW200 ;;
  CERT200) SUITE="$ROOT/evidence/prompt_runtime/final_cert/SHADOW200.json"; LABEL=CERT200 ;;
  *) echo "unknown kind"; exit 2 ;;
esac
OUT="$ROOT/evidence/prompt_runtime/final_cert/${LABEL}_${STAMP}"
mkdir -p "$OUT"
export SKIP_RESTART=1 SHADOW_CONCURRENCY=1
# Host-side launcher that detaches inner runner and writes control files
nohup bash -lc "
  \"$ROOT/evidence/prompt_runtime/final_cert/run_shadow_eligible.sh\" \"$SUITE\" \"$LABEL\" | tee \"$OUT/launch.out\"
  echo \$? > \"$OUT/exit_code\"
" >"$OUT/host.log" 2>&1 &
echo $! > "$OUT/host.pid"
cat > "$OUT/STATUS.md" <<EOM
kind: $KIND
started: $STAMP
host_pid: $(cat "$OUT/host.pid")
suite: $SUITE
out: $OUT
status_cmd: docker exec jaios-workspace-dev-api tail -20 /tmp/shadow_eligible_inner.log
checkpoint: docker exec jaios-workspace-dev-api ls -la /tmp/shadow_eligible_out
stop_cmd: docker exec jaios-workspace-dev-api pkill -f run_shadow_eligible.py; kill \$(cat $OUT/host.pid)
EOM
echo "LAUNCHED kind=$KIND out=$OUT pid=$(cat "$OUT/host.pid")"
