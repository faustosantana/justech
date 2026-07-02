#!/usr/bin/env bash
# Fase 18 — Motor retenciones por factura — TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
EVIDENCE="$PROJECT_ROOT/evidence/phase18-withholding-test.json"
LOG="$PROJECT_ROOT/logs/deploy/phase18-test-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$EVIDENCE")" "$(dirname "$LOG")"

if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  git pull origin "$(git branch --show-current)" 2>/dev/null || true
  rsync -av "${REPO}/custom/" "${PROJECT_ROOT}/custom/"
  rsync -av "${REPO}/scripts/" "${PROJECT_ROOT}/scripts/"
  chmod +x "${PROJECT_ROOT}/scripts/"*.sh
fi

hellenia_load_env "$ENV_FILE"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"

hellenia_log "=== Fase 18 Retenciones por factura — TEST ===" | tee "$LOG"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u hellenia_account --stop-after-init --no-http 2>&1 | tail -15 | tee -a "$LOG"

docker compose --env-file "$ENV_FILE" restart odoo
sleep 20

"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase18-validate-withholding-test.py PHASE18 "$EVIDENCE" 2>&1 | tee -a "$LOG"

"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase17-4-validate-payment-wizard-test.py PHASE17_4 \
  "$PROJECT_ROOT/evidence/phase18-wizard-regression.json" 2>&1 | tee -a "$LOG" || true

"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase16-validate-payments-test.py PHASE16_PAYMENTS \
  "$PROJECT_ROOT/evidence/phase18-payments-regression.json" 2>&1 | tee -a "$LOG" || true

python3 -c "import json; d=json.load(open('$EVIDENCE')); exit(0 if d.get('ok') else 1)"

hellenia_log "PASS Fase 18 TEST — $EVIDENCE" | tee -a "$LOG"
