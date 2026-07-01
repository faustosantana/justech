#!/usr/bin/env bash
# Fase 23.3C — Rediseño cotización wkhtmltopdf-safe — TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase23-3c-quotation-redesign"
EVIDENCE="$EVIDENCE_DIR/validation.json"
LOG="$PROJECT_ROOT/logs/deploy/phase23-3c-test-$(date +%Y-%m-%d_%H%M).log"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"

mkdir -p "$EVIDENCE_DIR" "$(dirname "$LOG")"
chmod 777 "$EVIDENCE_DIR"
hellenia_load_env "$ENV_FILE"

hellenia_log "=== Fase 23.3C Rediseño cotización — TEST ===" | tee "$LOG"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u hellenia_reports --stop-after-init --no-http \
  2>&1 | tail -12 | tee -a "$LOG"

docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo
sleep 25

# pdftotext required for PDF mojibake checks (ephemeral run containers lack it)
docker compose --env-file "$ENV_FILE" exec -T -u root odoo \
  bash -c "command -v pdftotext >/dev/null || (apt-get update -qq && apt-get install -y -qq poppler-utils)" \
  2>&1 | tee -a "$LOG" || true

TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" exec -T \
  -e EVIDENCE_HOST="${EVIDENCE_DIR}" \
  odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/phase23-3c-quotation-redesign-test.py" > "$TMP" 2>&1
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
marker = 'PHASE23_3C:'
i = d.find(marker)
if i < 0:
    print(d[-8000:], file=sys.stderr)
    sys.exit(1)
open('$EVIDENCE', 'w').write(d[i+len(marker):].strip())
print('OK → $EVIDENCE')
"

tail -8 "$TMP"
rm -f "$TMP"

hellenia_log "PASS/FAIL → $EVIDENCE" | tee -a "$LOG"

# Collect PDFs/screenshots written under container /tmp when no bind mount
docker compose --env-file "$ENV_FILE" cp \
  "odoo:/tmp/phase23-3c-quotation-redesign/." "${EVIDENCE_DIR}/" 2>/dev/null || true

RESULT=$(python3 -c "import json; d=json.load(open('$EVIDENCE')); print('PASS' if d.get('pass') else 'FAIL')")
if [[ "$RESULT" != "PASS" ]]; then
  hellenia_log "FAIL Fase 23.3C TEST — $EVIDENCE" | tee -a "$LOG"
  exit 1
fi

hellenia_log "PASS Fase 23.3C TEST — $EVIDENCE" | tee -a "$LOG"
