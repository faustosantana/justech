#!/usr/bin/env bash
# Stop only the worker/wrapper PIDs for one run_id (never pkill global runners).
set -euo pipefail
DOCKER="${DOCKER:-/usr/local/bin/docker}"
RUN_ID="${1:?run_id required}"
CTR_DIR="/tmp/prompt_cert/${RUN_ID}"

"$DOCKER" exec jaios-workspace-dev-api bash -lc "
set +e
D='$CTR_DIR'
if [ ! -d \"\$D\" ]; then echo RUN_NOT_FOUND; exit 3; fi
for f in worker.pid wrapper.pid; do
  if [ -f \"\$D/\$f\" ]; then
    pid=\$(cat \"\$D/\$f\")
    if [ -n \"\$pid\" ] && kill -0 \"\$pid\" 2>/dev/null; then
      kill \"\$pid\" 2>/dev/null || true
      echo stopped_\$f=\$pid
    else
      echo already_dead_\$f=\$pid
    fi
  fi
done
echo STOPPED > \"\$D/status.txt\"
"
