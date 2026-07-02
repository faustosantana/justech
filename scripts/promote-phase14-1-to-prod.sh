#!/usr/bin/env bash
# Promover fix 14.1 a PROD tras PASS en TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_EVIDENCE="$PROJECT_ROOT/evidence/phase14-1-accounting-permissions-test.json"

if [[ "${APPROVE_PROMOTION:-}" != "1" ]]; then
  hellenia_log "ABORT: requiere APPROVE_PROMOTION=1"
  exit 1
fi

python3 -c "import json; d=json.load(open('$TEST_EVIDENCE')); exit(0 if d.get('ok') else 1)" \
  || { hellenia_log "ABORT: TEST no PASS"; exit 1; }

hellenia_log "Backup PROD..."
"$SCRIPT_DIR/backup-hellenia-prod.sh"

hellenia_log "Aplicar fix 14.1 en PROD..."
"$SCRIPT_DIR/run-phase14-1-fix.sh" prod

hellenia_log "Healthcheck PROD..."
"$SCRIPT_DIR/healthcheck-full.sh" prod

CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://odoo.hellenia.cloud/web/login 2>/dev/null || echo "000")
[[ "$CODE" == "200" ]] || { hellenia_log "ABORT: smoke test HTTP $CODE"; exit 1; }

hellenia_log "PASS promoción 14.1 PROD"
