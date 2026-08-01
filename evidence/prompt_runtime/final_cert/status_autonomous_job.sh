#!/usr/bin/env bash
# Status for an exact run_id (never reads another run's artefacts).
set -euo pipefail
DOCKER="${DOCKER:-/usr/local/bin/docker}"
ROOT=/Users/faustosantana/Projects/justech-forensic-audit
CERT="$ROOT/evidence/prompt_runtime/final_cert"
RUN_ID="${1:?run_id required}"
CTR_DIR="/tmp/prompt_cert/${RUN_ID}"
HOST_OUT="$CERT/${RUN_ID}"

if ! "$DOCKER" exec jaios-workspace-dev-api bash -lc "test -d '$CTR_DIR'"; then
  echo "RUN_NOT_FOUND container_dir=$CTR_DIR"
  exit 3
fi

"$DOCKER" exec jaios-workspace-dev-api bash -lc "
set -e
D='$CTR_DIR'
echo run_id=$RUN_ID
echo container_dir=\$D
echo status=\$(cat \$D/status.txt 2>/dev/null || echo unknown)
echo started_at=\$(cat \$D/started_at 2>/dev/null || echo n/a)
echo worker_pid=\$(cat \$D/worker.pid 2>/dev/null || echo n/a)
echo exit_code=\$(cat \$D/exit_code 2>/dev/null || echo running)
WP=\$(cat \$D/worker.pid 2>/dev/null || true)
if [ -n \"\$WP\" ] && kill -0 \"\$WP\" 2>/dev/null; then echo alive=yes; else echo alive=no; fi
if [ -f \$D/heartbeat.json ]; then echo '---heartbeat---'; cat \$D/heartbeat.json; fi
if [ -f \$D/SUMMARY.json ]; then echo '---summary---'; cat \$D/SUMMARY.json; fi
if [ -f \$D/PRECHECK_FAILED ]; then echo '---PRECHECK_FAILED---'; cat \$D/precheck.err 2>/dev/null || true; fi
echo '---log_tail---'
tail -20 \$D/run.log 2>/dev/null || true
"

# Refresh host mirror for this run only
mkdir -p "$HOST_OUT"
"$DOCKER" cp "jaios-workspace-dev-api:$CTR_DIR/." "$HOST_OUT/" >/dev/null 2>&1 || true
