#!/usr/bin/env bash
# Fase 9 — Ejecutar script UAT en TEST (odoo shell)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PY_SCRIPT="${1:?Uso: uat-run-on-test.sh <script.py> [evidence.json]}"
EVIDENCE="${2:-}"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"
MARKER="${PY_SCRIPT%.py}"
MARKER="${MARKER##*/}"
MARKER=$(echo "$MARKER" | tr '[:lower:]' '[:upper:]' | tr '-' '_')

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

OUT_FILE="${EVIDENCE:-}"
if [[ -n "$OUT_FILE" && "$OUT_FILE" != /* ]]; then
  OUT_FILE="$PROJECT_ROOT/$OUT_FILE"
fi
TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/${PY_SCRIPT}" > "$TMP" 2>&1
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR: odoo shell exit $RC"
  tail -30 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

EVIDENCE_PATH="$OUT_FILE" TMPFILE="$TMP" python3 <<'PY'
import os, sys
d = open(os.environ["TMPFILE"]).read()
out = os.environ.get("EVIDENCE_PATH") or ""
for prefix in ("UAT_BLOCK1:", "UAT_FUNCTIONAL:", "UAT_STRESS:", "UAT_AUDIT:"):
    i = d.find(prefix)
    if i >= 0:
        payload = d[i + len(prefix):].strip()
        print(payload)
        if out:
            open(out, "w").write(payload)
        sys.exit(0)
print(d[-3000:], file=sys.stderr)
sys.exit(1)
PY

if [[ -n "$OUT_FILE" && -f "$OUT_FILE" ]]; then
  hellenia_log "Evidencia → $OUT_FILE ($(wc -c < "$OUT_FILE") bytes)"
fi
rm -f "$TMP"
