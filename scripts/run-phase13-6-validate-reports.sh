#!/usr/bin/env bash
# Fase 13.6 — Validación formatos corporativos
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-test}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_DIR="$(hellenia_env_dir "$ENV_NAME")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_DIR}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_DIR}"
OUT="$PROJECT_ROOT/evidence/phase13-6-hellenia-reports-${ENV_NAME}.json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

hellenia_log "Fase 13.6 — Validación hellenia_reports en ${ENV_NAME}"

TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/phase13-6-validate-hellenia-reports.py" > "$TMP" 2>&1
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR shell exit $RC"
  tail -50 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

mkdir -p "$(dirname "$OUT")"
python3 -c "
import sys
d=open('$TMP').read()
m='PHASE13_6_REPORTS:'
i=d.find(m)
if i<0:
    print(d[-10000:], file=sys.stderr); sys.exit(1)
open('$OUT','w').write(d[i+len(m):].strip())
print('OK → $OUT')
"
tail -15 "$TMP"
rm -f "$TMP"
hellenia_log "Validación completada"
