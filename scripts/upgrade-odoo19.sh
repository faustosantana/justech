#!/usr/bin/env bash
# Upgrade Odoo 18 → 19 para DEV o TEST (Hellenia)
# Uso: upgrade-odoo19.sh dev|test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET="${1:-}"
ODOO_IMAGE="odoo:19.0-20260619"
LOG_FILE="$PROJECT_ROOT/logs/deploy/upgrade-odoo19-${TARGET}-$(date +%Y-%m-%d_%H%M).log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

usage() {
  echo "Uso: $0 dev|test"
  exit 1
}

[[ "$TARGET" == "dev" || "$TARGET" == "test" ]] || usage

COMPOSE_DIR="$PROJECT_ROOT/docker/${TARGET}"
ENV_FILE="$PROJECT_ROOT/config/${TARGET}/.env"
CONTAINER="hellenia-${TARGET}-odoo-1"
DB_CONTAINER="hellenia-${TARGET}-db-1"

if [[ "$TARGET" == "dev" ]]; then
  DB_NAME="hellenia_dev"
  BACKUP_SCRIPT="$SCRIPT_DIR/backup-dev.sh"
else
  DB_NAME="hellenia_test"
  BACKUP_SCRIPT="$SCRIPT_DIR/backup-test.sh"
fi

mkdir -p "$(dirname "$LOG_FILE")"

if [[ ! -f "$ENV_FILE" ]]; then
  log "ERROR: Falta $ENV_FILE"
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

log "=== Upgrade Odoo 19 — $TARGET ==="
log "Imagen destino: $ODOO_IMAGE"
log "Base de datos: $DB_NAME"

log "--- Backup pre-migración ---"
if [[ "${SKIP_BACKUP:-0}" != "1" ]]; then
  "$BACKUP_SCRIPT" || log "WARN: backup falló — continuar bajo responsabilidad"
else
  log "SKIP_BACKUP=1 — omitiendo backup"
fi

log "--- Pull imagen Odoo 19 ---"
docker pull "$ODOO_IMAGE"

log "--- Recrear contenedor Odoo ---"
cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" up -d odoo

log "--- Esperando arranque y migración automática BD (90s) ---"
sleep 90

log "--- Logs recientes ---"
docker logs "$CONTAINER" --tail 30 2>&1 | tee -a "$LOG_FILE"

if docker logs "$CONTAINER" 2>&1 | grep -qi "traceback"; then
  log "WARN: Se detectaron tracebacks — revisar logs"
fi

log "--- Upgrade explícito módulo base ---"
if ! docker exec "$CONTAINER" odoo \
  -d "$DB_NAME" --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
  -u base --stop-after-init 2>&1 | tee -a "$LOG_FILE"; then
  log "WARN: upgrade base falló — recreando BD desde cero (Odoo 18→19)"
  SKIP_BACKUP=1 "$SCRIPT_DIR/recreate-db-odoo19.sh" "$TARGET"
fi

log "--- Reinicio Odoo ---"
docker compose --env-file "$ENV_FILE" restart odoo
sleep 30

log "--- Verificación contenedores ---"
docker ps --filter "name=hellenia-${TARGET}" --format '{{.Names}} {{.Status}} {{.Image}}' | tee -a "$LOG_FILE"

log "=== Upgrade $TARGET completado ==="
log "Ejecutar: $SCRIPT_DIR/validate-odoo19.sh $TARGET"
