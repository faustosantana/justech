#!/usr/bin/env bash
# Aplicar hellenia_ui + sale_management — SOLO PRODUCCIÓN
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
LOG="$PROJECT_ROOT/logs/deploy/apply-hellenia-ui-prod-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$LOG")"
hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

log() { hellenia_log "$*" | tee -a "$LOG"; }

log "=== Hellenia UI — solo PROD ==="

STATE=$(docker exec hellenia-prod-db-1 psql -U odoo -d "${ODOO_DB_NAME}" -tAc \
  "SELECT state FROM ir_module_module WHERE name='sale_management'" | tr -d '[:space:]')
if [[ "$STATE" != "installed" ]]; then
  log "Instalando sale_management..."
  docker compose --env-file "$ENV_FILE" stop odoo
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -i sale_management --stop-after-init 2>&1 | tail -30 | tee -a "$LOG"
  docker compose --env-file "$ENV_FILE" up -d odoo
  sleep 15
else
  log "sale_management ya instalado"
fi

STATE=$(docker exec hellenia-prod-db-1 psql -U odoo -d "${ODOO_DB_NAME}" -tAc \
  "SELECT state FROM ir_module_module WHERE name='hellenia_ui'" | tr -d '[:space:]')
if [[ "$STATE" != "installed" ]]; then
  log "Instalando hellenia_ui..."
  docker compose --env-file "$ENV_FILE" stop odoo
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -i hellenia_ui --stop-after-init 2>&1 | tail -30 | tee -a "$LOG"
  docker compose --env-file "$ENV_FILE" up -d odoo
  sleep 15
else
  log "Actualizando hellenia_ui..."
  docker compose --env-file "$ENV_FILE" stop odoo
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -u hellenia_ui --stop-after-init 2>&1 | tail -30 | tee -a "$LOG"
  docker compose --env-file "$ENV_FILE" up -d odoo
  sleep 15
fi

log "Validando menú..."
"$SCRIPT_DIR/run-odoo-shell-env.sh" prod validate-hellenia-ui-menu.py HELLENIA_UI_MENU \
  "evidence/hellenia-ui-menu-prod.json" 2>&1 | tee -a "$LOG"

log "=== Completado — ver evidence/hellenia-ui-menu-prod.json ==="
