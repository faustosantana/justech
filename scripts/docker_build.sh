#!/usr/bin/env bash
# Workaround: docker-credential-desktop missing breaks `docker compose build`.
set -euo pipefail
CONFIG="${HOME}/.docker/config.json"
BACKUP="/tmp/jaios-docker-config-backup.json"
RESTORE=0
if [[ -f "$CONFIG" ]] && grep -qE 'credsStore|credHelpers' "$CONFIG"; then
  cp "$CONFIG" "$BACKUP"
  RESTORE=1
  python3 - <<'PY'
import json, os
p = os.path.expanduser("~/.docker/config.json")
with open(p) as f:
    c = json.load(f)
c.pop("credsStore", None)
c.pop("credHelpers", None)
with open(p, "w") as f:
    json.dump(c, f)
PY
fi
docker compose build "$@"
if [[ "$RESTORE" -eq 1 ]]; then
  mv "$BACKUP" "$CONFIG"
fi
