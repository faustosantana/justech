#!/usr/bin/env bash
# Fase 17.1 — Pagos menú + retenciones + PDF — TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
EVIDENCE="$PROJECT_ROOT/evidence/phase17-1-full-validation.json"
LOG="$PROJECT_ROOT/logs/deploy/phase17-1-test-$(date +%Y-%m-%d_%H%M).log"

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

hellenia_log "=== Fase 17.1 Pagos/PDF — TEST ===" | tee "$LOG"

cd "$COMPOSE_DIR"
hellenia_log "Actualizar módulos hellenia_account, hellenia_reports, hellenia_ux..." | tee -a "$LOG"
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u hellenia_account,hellenia_reports,hellenia_ux,hellenia_ui --stop-after-init --no-http \
  2>&1 | tail -20 | tee -a "$LOG"

docker compose --env-file "$ENV_FILE" up -d odoo
docker compose --env-file "$ENV_FILE" restart odoo
sleep 20

"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase17-1-validate-payments-test.py PHASE17_1 "$EVIDENCE" 2>&1 | tee -a "$LOG"

# Regresión Fase 16
"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase16-validate-payments-test.py PHASE16_PAYMENTS \
  "$PROJECT_ROOT/evidence/phase17-1-payments-regression.json" 2>&1 | tee -a "$LOG" || true

python3 -c "import json; d=json.load(open('$EVIDENCE')); exit(0 if d.get('ok') else 1)"

hellenia_log "PASS Fase 17.1 TEST — $EVIDENCE" | tee -a "$LOG"
