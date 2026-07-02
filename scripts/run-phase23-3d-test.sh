#!/usr/bin/env bash
# Fase 23.3D — Ajustes finales cotización Hellenia — TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase23-3d-quotation-final-adjustments"
EVIDENCE="$EVIDENCE_DIR/validation.json"
LOG="$PROJECT_ROOT/logs/deploy/phase23-3d-test-$(date +%Y-%m-%d_%H%M).log"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"

mkdir -p "$EVIDENCE_DIR" "$(dirname "$LOG")"
chmod 777 "$EVIDENCE_DIR" 2>/dev/null || true
hellenia_load_env "$ENV_FILE" 2>/dev/null || true

hellenia_log() { echo "[$(date -Iseconds)] $*"; }

hellenia_log "=== Fase 23.3D Ajustes finales cotización — TEST ===" | tee "$LOG"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u hellenia_reports --stop-after-init --no-http \
  2>&1 | tail -12 | tee -a "$LOG"

docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo
sleep 25

docker compose --env-file "$ENV_FILE" exec -T -u root odoo \
  bash -c "command -v pdftotext >/dev/null || (apt-get update -qq && apt-get install -y -qq poppler-utils)" \
  2>&1 | tee -a "$LOG" || true

TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" exec -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/phase23-3d-quotation-final-adjustments-test.py" > "$TMP" 2>&1
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR: odoo shell exit $RC"
  tail -60 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

python3 -c "
import sys
d = open('$TMP').read()
marker = 'PHASE23_3D:'
i = d.find(marker)
if i < 0:
    print(d[-8000:], file=sys.stderr)
    sys.exit(1)
open('$EVIDENCE', 'w').write(d[i+len(marker):].strip())
print('OK → $EVIDENCE')
"

tail -8 "$TMP"
rm -f "$TMP"

docker compose --env-file "$ENV_FILE" cp \
  "odoo:/tmp/phase23-3d-quotation-final-adjustments/." "${EVIDENCE_DIR}/" 2>/dev/null || true

python3 -c "
import json, sys
d = json.load(open('$EVIDENCE'))
print('PASS' if d.get('pass') else 'FAIL', '- failed:', len(d.get('failed_checks', [])))
sys.exit(0 if d.get('pass') else 1)
"

hellenia_log "PASS Fase 23.3D TEST — $EVIDENCE" | tee -a "$LOG"
