#!/usr/bin/env bash
# Promover Fase 16 pagos a PROD tras PASS en TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_EVIDENCE="$PROJECT_ROOT/evidence/phase16-payments-test.json"

if [[ "${APPROVE_PROMOTION:-}" != "1" ]]; then
  hellenia_log "ABORT: requiere APPROVE_PROMOTION=1"
  exit 1
fi

python3 -c "import json; d=json.load(open('$TEST_EVIDENCE')); exit(0 if d.get('ok') else 1)" \
  || { hellenia_log "ABORT: TEST no PASS"; exit 1; }

hellenia_log "Backup PROD..."
"$SCRIPT_DIR/backup-hellenia-prod.sh"

REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  git pull origin "$(git branch --show-current)" 2>/dev/null || true
  rsync -av "${REPO}/custom/" "${PROJECT_ROOT}/custom/"
  rsync -av "${REPO}/scripts/" "${PROJECT_ROOT}/scripts/"
fi

ENV_FILE="$PROJECT_ROOT/config/production/.env"
hellenia_load_env "$ENV_FILE"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
PROD_EVIDENCE="$PROJECT_ROOT/evidence/phase16-payments-prod.json"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -i hellenia_account --stop-after-init --no-http 2>&1 | tail -5 || \
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u hellenia_account --stop-after-init --no-http 2>&1 | tail -5

docker compose --env-file "$ENV_FILE" up -d odoo
sleep 15

sed 's/hellenia_test/hellenia_prod/g; s/solo hellenia_test/solo hellenia_prod/' \
  "$SCRIPT_DIR/phase16-validate-payments-test.py" > "$SCRIPT_DIR/phase16-validate-payments-prod.py"

"$SCRIPT_DIR/run-odoo-shell-env.sh" prod phase16-validate-payments-prod.py PHASE16_PAYMENTS "$PROD_EVIDENCE"
python3 -c "import json; d=json.load(open('$PROD_EVIDENCE')); exit(0 if d.get('ok') else 1)"

"$SCRIPT_DIR/healthcheck-full.sh" prod
hellenia_log "PASS promoción Fase 16 Pagos PROD"
