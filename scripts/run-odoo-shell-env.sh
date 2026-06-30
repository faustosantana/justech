#!/usr/bin/env bash
# Ejecutar script Python en odoo shell — DEV o TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: run-odoo-shell-env.sh dev|test|prod <script.py> [marker] [out.json]}"
PY_SCRIPT="${2:?}"
MARKER="${3:-PHASE12}"
OUT="${4:-}"

if [[ "$ENV_NAME" != "dev" && "$ENV_NAME" != "test" && "$ENV_NAME" != "prod" ]]; then
  hellenia_log "ERROR: solo dev|test|prod"
  exit 1
fi

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"

if [[ -n "$OUT" && "$OUT" != /* ]]; then
  OUT="$PROJECT_ROOT/$OUT"
fi
if [[ -n "$OUT" ]]; then
  mkdir -p "$(dirname "$OUT")"
fi

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/${PY_SCRIPT}" > "$TMP" 2>&1
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR: odoo shell exit $RC"
  tail -40 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

if [[ -n "$OUT" ]]; then
  python3 -c "
import sys
d = open('$TMP').read()
marker = '${MARKER}:'
i = d.find(marker)
if i < 0:
    print(d[-5000:], file=sys.stderr)
    sys.exit(1)
open('$OUT', 'w').write(d[i+len(marker):].strip())
print('OK → $OUT')
"
fi

tail -5 "$TMP"
rm -f "$TMP"
