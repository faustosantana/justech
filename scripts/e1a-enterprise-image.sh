#!/usr/bin/env bash
# E1a — Imagen hellenia-odoo:19-enterprise en DEV (con rollback automático)
# Uso: e1a-enterprise-image.sh /path/odoo_19.0+e.YYYYMMDD.tar.gz
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ARCHIVE="${1:-/opt/odoo-projects/hellenia/downloads/enterprise/odoo_19.0+e.20260629.tar.gz}"
ENV_FILE="$PROJECT_ROOT/config/dev/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/dev"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
ODOO_CONF="$PROJECT_ROOT/config/dev/odoo.conf"
STATE_DIR="$PROJECT_ROOT/logs/deploy/e1a-state-$(date +%Y-%m-%d_%H%M%S)"
LOG_FILE="$PROJECT_ROOT/logs/deploy/e1a-enterprise-image-$(date +%Y-%m-%d_%H%M).log"
BACKUP_DIR=""
ROLLBACK_DONE=false

mkdir -p "$(dirname "$LOG_FILE")" "$STATE_DIR"

rollback() {
  local rc=$?
  if $ROLLBACK_DONE; then
    hellenia_log "Rollback ya ejecutado" | tee -a "$LOG_FILE"
    exit "$rc"
  fi
  ROLLBACK_DONE=true
  hellenia_log "=== ROLLBACK automático (código $rc) ===" | tee -a "$LOG_FILE"

  if [[ -f "$STATE_DIR/docker-compose.yml.bak" ]]; then
    cp -f "$STATE_DIR/docker-compose.yml.bak" "$COMPOSE_FILE"
    hellenia_log "Restaurado docker-compose.yml" | tee -a "$LOG_FILE"
  fi
  if [[ -f "$STATE_DIR/odoo.conf.bak" ]]; then
    cp -f "$STATE_DIR/odoo.conf.bak" "$ODOO_CONF"
    hellenia_log "Restaurado odoo.conf" | tee -a "$LOG_FILE"
  fi

  hellenia_load_env "$ENV_FILE" 2>/dev/null || true
  cd "$COMPOSE_DIR"
  docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo 2>&1 | tee -a "$LOG_FILE" || true

  if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]]; then
    hellenia_log "Restaurando BD desde $BACKUP_DIR" | tee -a "$LOG_FILE"
    "${SCRIPT_DIR}/restore-dev.sh" "$BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE" || true
  fi

  hellenia_log "ROLLBACK completado" | tee -a "$LOG_FILE"
  exit "$rc"
}

trap rollback ERR

hellenia_log "=== E1a Enterprise Image — DEV ===" | tee -a "$LOG_FILE"
hellenia_require_file "$ARCHIVE"

# --- 1-3. Validar integridad, SHA256, versión 19 ---
hellenia_log "--- Validación archivo ---" | tee -a "$LOG_FILE"
SHA=$(sha256sum "$ARCHIVE" | awk '{print $1}')
hellenia_log "SHA256: $SHA" | tee -a "$LOG_FILE"
echo "$SHA" > "$STATE_DIR/archive.sha256"

if ! tar tzf "$ARCHIVE" >/dev/null 2>&1; then
  hellenia_log "ERROR: archivo corrupto (tar test falló)"
  exit 1
fi
hellenia_log "OK  integridad tar.gz" | tee -a "$LOG_FILE"

WEB_MANIFEST=$(tar tzf "$ARCHIVE" | grep -E 'odoo/addons/web_enterprise/__manifest__\.py$' | head -1)
[[ -n "$WEB_MANIFEST" ]] || { hellenia_log "ERROR: web_enterprise no encontrado en tarball"; exit 1; }
hellenia_log "OK  web_enterprise en tarball" | tee -a "$LOG_FILE"

echo "$ARCHIVE" | grep -qE '19\.0(\+e)?' || { hellenia_log "ERROR: nombre no indica 19.0"; exit 1; }
hellenia_log "OK  versión 19.x en nombre archivo" | tee -a "$LOG_FILE"

# --- Backup estado previo ---
cp -f "$COMPOSE_FILE" "$STATE_DIR/docker-compose.yml.bak"
cp -f "$ODOO_CONF" "$STATE_DIR/odoo.conf.bak"

hellenia_log "--- Backup DEV ---" | tee -a "$LOG_FILE"
BACKUP_OUT=$("${SCRIPT_DIR}/backup-dev.sh" 2>&1 | tee -a "$LOG_FILE")
BACKUP_DIR=$(echo "$BACKUP_OUT" | grep -oE '/opt/odoo-projects/hellenia/backups/dev/[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}' | tail -1)
hellenia_log "Backup: ${BACKUP_DIR:-desconocido}" | tee -a "$LOG_FILE"

# Sincronizar custom desde repo si existe
if [[ -d "$PROJECT_ROOT/repository/custom" ]]; then
  rsync -a "$PROJECT_ROOT/repository/custom/" "$PROJECT_ROOT/custom/"
fi

# --- 4. Extraer ---
hellenia_log "--- Extracción ---" | tee -a "$LOG_FILE"
EXTRACTED=$("${SCRIPT_DIR}/extract-enterprise-full.sh" "$ARCHIVE" 2>&1 | tee -a "$LOG_FILE" | tail -1)

# --- 5-6. Preparar addons + build imagen ---
hellenia_log "--- Preparar addons Enterprise ---" | tee -a "$LOG_FILE"
"${SCRIPT_DIR}/prepare-enterprise-addons.sh" "$EXTRACTED" 2>&1 | tee -a "$LOG_FILE"

hellenia_log "--- Build imagen hellenia-odoo:19-enterprise ---" | tee -a "$LOG_FILE"
"${SCRIPT_DIR}/build-hellenia-odoo-image.sh" 2>&1 | tee -a "$LOG_FILE"

# --- 7-8. Actualizar DEV compose (sin volúmenes enterprise/custom) ---
hellenia_log "--- Actualizar DEV compose + odoo.conf ---" | tee -a "$LOG_FILE"

# odoo.conf: addons baked in image (preservar admin_passwd del backup)
AP_LINE=$(grep '^admin_passwd' "$STATE_DIR/odoo.conf.bak" || echo 'admin_passwd = CHANGE_ME_ADMIN_PASSWORD')
cat > "$ODOO_CONF" << CONF
[options]
; Enterprise y custom horneados en imagen hellenia-odoo:19-enterprise
addons_path = /opt/odoo/enterprise/addons,/usr/lib/python3/dist-packages/odoo/addons,/opt/odoo/custom
data_dir = /var/lib/odoo
dbfilter = ^hellenia_dev$
list_db = False
log_level = debug
logfile = False
workers = 0
proxy_mode = True
${AP_LINE}
CONF

# Aplicar compose enterprise image (idempotente si ya actualizado en repo)
if ! grep -q 'hellenia-odoo:19-enterprise' "$COMPOSE_FILE"; then
  hellenia_log "WARN: docker-compose.yml no tiene imagen enterprise — usar versión del repositorio"
fi

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

docker compose --env-file "$ENV_FILE" build odoo 2>&1 | tee -a "$LOG_FILE"
docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo 2>&1 | tee -a "$LOG_FILE"

hellenia_log "Esperando arranque Odoo..." | tee -a "$LOG_FILE"
sleep 60

# --- 9. Instalar web_enterprise ---
hellenia_log "--- Instalar web_enterprise ---" | tee -a "$LOG_FILE"
docker compose --env-file "$ENV_FILE" stop odoo
docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
  -d "${ODOO_DB_NAME:-hellenia_dev}" \
  --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
  -i web_enterprise --stop-after-init 2>&1 | tee -a "$LOG_FILE"

docker compose --env-file "$ENV_FILE" up -d odoo
sleep 45

# --- 10. Validaciones ---
hellenia_log "--- Validación post-instalación ---" | tee -a "$LOG_FILE"
if ! "${SCRIPT_DIR}/validate-enterprise-dev.sh" --no-license 2>&1 | tee -a "$LOG_FILE"; then
  hellenia_log "ERROR: validación enterprise falló"
  exit 1
fi

if ! "${SCRIPT_DIR}/healthcheck.sh" 2>&1 | tee -a "$LOG_FILE"; then
  hellenia_log "ERROR: healthcheck falló"
  exit 1
fi

# Verificar TEST y PROD intactos
docker inspect hellenia-test-odoo-1 --format '{{.Config.Image}}' 2>/dev/null | grep -q 'odoo:19.0-20260619' && \
  hellenia_log "OK  TEST sin cambios (imagen Community)" | tee -a "$LOG_FILE" || \
  hellenia_log "WARN  TEST imagen inesperada" | tee -a "$LOG_FILE"

docker inspect odoo-pecv-odoo-1 --format '{{.Config.Image}}' 2>/dev/null | grep -q 'odoo:18' && \
  hellenia_log "OK  PROD intacta (Odoo 18)" | tee -a "$LOG_FILE" || \
  hellenia_log "WARN  PROD imagen inesperada" | tee -a "$LOG_FILE"

trap - ERR
ROLLBACK_DONE=true

hellenia_log "=== E1a COMPLETADO OK ===" | tee -a "$LOG_FILE"
hellenia_log "Imagen: hellenia-odoo:19-enterprise" | tee -a "$LOG_FILE"
hellenia_log "SHA256 archivo: $SHA" | tee -a "$LOG_FILE"
hellenia_log "Backup: $BACKUP_DIR" | tee -a "$LOG_FILE"
