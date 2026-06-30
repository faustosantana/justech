#!/usr/bin/env bash
# Fase E1 — Activar Odoo Enterprise en DEV (sin wizard, sin usuarios extra)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/dev/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/dev"
LOG_FILE="$PROJECT_ROOT/logs/deploy/install-enterprise-dev-$(date +%Y-%m-%d_%H%M).log"
SUBSCRIPTION_REF="M260616306091776"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")"

if [[ ! -f "$ENV_FILE" ]]; then
  log "ERROR: Falta $ENV_FILE"
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

log "=== Fase E1 — Enterprise DEV ==="

log "--- E0.5 validate ---"
"$SCRIPT_DIR/validate-subscription-env.sh" || true

log "--- Clone enterprise ---"
"$SCRIPT_DIR/clone-enterprise.sh"

log "--- Backup DEV ---"
"$SCRIPT_DIR/backup-dev.sh" || log "WARN backup falló"

log "--- Recrear stack con volúmenes enterprise/custom ---"
cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" pull odoo
docker compose --env-file "$ENV_FILE" up -d

log "--- Esperando Odoo (45s) ---"
sleep 45

log "--- Instalar web_enterprise ---"
docker compose --env-file "$ENV_FILE" stop odoo
docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
  -d "${ODOO_DB_NAME:-hellenia_dev}" \
  --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
  -i web_enterprise --stop-after-init 2>&1 | tail -25

docker compose --env-file "$ENV_FILE" up -d odoo
sleep 40

log "--- Verificación ---"
VERSION=$(curl -sS --max-time 15 -X POST 'https://dev.hellenia.cloud/web/webclient/version_info' \
  -H 'Content-Type: application/json' -d '{}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',{}).get('server_version',''))" 2>/dev/null || echo "")
log "server_version: $VERSION"

if docker exec hellenia-dev-odoo-1 test -d /mnt/enterprise/web_enterprise 2>/dev/null; then
  log "OK  web_enterprise montado"
else
  log "FAIL web_enterprise no visible en contenedor"
  exit 1
fi

LOGIN=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 https://dev.hellenia.cloud/web/login)
log "HTTP /web/login: $LOGIN"

log "=== REGISTRO SUSCRIPCIÓN (manual en UI) ==="
log "1. Abrir https://dev.hellenia.cloud"
log "2. Login admin"
log "3. Ingresar código: $SUBSCRIPTION_REF"
log "4. Verificar banner verde"
log ""
log "Ejecutar después: scripts/validate-enterprise-dev.sh"
