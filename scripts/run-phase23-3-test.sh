#!/usr/bin/env bash
# Fase 23.3 — Template premium cotización Hellenia — TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
EVIDENCE="$PROJECT_ROOT/evidence/phase23-3-quotation-template/validation.json"
LOG="$PROJECT_ROOT/logs/deploy/phase23-3-test-$(date +%Y-%m-%d_%H%M).log"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"

mkdir -p "$(dirname "$EVIDENCE")" "$(dirname "$LOG")"
hellenia_load_env "$ENV_FILE"

hellenia_log "=== Fase 23.3 Cotización premium — TEST ===" | tee "$LOG"

cd "$COMPOSE_DIR"
hellenia_log "Actualizar hellenia_reports..." | tee -a "$LOG"
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u hellenia_reports --stop-after-init --no-http \
  2>&1 | tail -15 | tee -a "$LOG"

docker compose --env-file "$ENV_FILE" up -d odoo
sleep 12

"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase23-3-quotation-template-test.py PHASE23_3 "$EVIDENCE" 2>&1 | tee -a "$LOG"

python3 -c "
import json
d = json.load(open('$EVIDENCE'))
print('PASS' if d.get('pass') else 'FAIL', '- checks failed:', len(d.get('failed_checks', [])))
exit(0 if d.get('pass') else 1)
"

hellenia_log "PASS Fase 23.3 TEST — $EVIDENCE" | tee -a "$LOG"
