#!/usr/bin/env bash
# Fase 13.5 — Certificación motor PDF (solo hellenia_prod)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
OUT="$PROJECT_ROOT/evidence/phase13-5-pdf-certification-prod.json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

hellenia_log "Fase 13.5 — Certificación PDF hellenia_prod"

TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/phase13-5-certify-pdf-engine.py" > "$TMP" 2>&1
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR shell exit $RC"
  tail -40 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

mkdir -p "$(dirname "$OUT")"
python3 -c "
import sys
d=open('$TMP').read()
m='PHASE13_5_PDF:'
i=d.find(m)
if i<0:
    print(d[-8000:], file=sys.stderr); sys.exit(1)
open('$OUT','w').write(d[i+len(m):].strip())
print('OK → $OUT')
"
tail -10 "$TMP"
rm -f "$TMP"
hellenia_log "Certificación PDF completada"
