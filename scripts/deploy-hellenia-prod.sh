#!/usr/bin/env bash
# Despliegue inicial hellenia-prod (Odoo 19 EE) — bootstrap pre-Go-Live
#
# ⚠️  ACTUALIZACIONES POST-GO-LIVE: usar promote-to-production.sh
#     Flujo obligatorio: TEST certificado → APPROVE_PROMOTION=1 → backup → promoción
#
# Este script NO debe usarse para cambios incrementales en producción.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
CONF_FILE="$PROJECT_ROOT/config/production/odoo.conf"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
COMMIT="${1:-feature/justech-l10n-do-mvp}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/deploy-prod-$(date +%Y-%m-%d_%H%M).log"
SUBSCRIPTION_CODE="${SUBSCRIPTION_CODE:-M260616306091776}"

mkdir -p "$(dirname "$LOG_FILE")" "$PROJECT_ROOT/evidence" "$PROJECT_ROOT/logs/deploy"

log() { hellenia_log "$*" | tee -a "$LOG_FILE"; }

require_dns() {
  local ip
  ip=$(dig +short prod.hellenia.cloud A 2>/dev/null | head -1 || true)
  if [[ "$ip" != "2.25.69.179" ]]; then
    log "WARN: prod.hellenia.cloud no apunta a 2.25.69.179 (actual: ${ip:-vacío})"
    log "WARN: Let's Encrypt requiere registro A prod.hellenia.cloud → 2.25.69.179 (no cambia odoo.hellenia.cloud)"
  else
    log "OK  DNS prod.hellenia.cloud → $ip"
  fi
}

ensure_config() {
  if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$PROJECT_ROOT/config/test/.env" ]]; then
      log "Creando config/production/.env desde test (misma política DB)..."
      cp "$PROJECT_ROOT/config/test/.env" "$ENV_FILE"
      sed -i 's/hellenia-test/hellenia-prod/g; s/hellenia_test/hellenia_prod/g; s/config\/test/config\/production/g' "$ENV_FILE"
    else
      cp "$PROJECT_ROOT/config/production/.env.example" "$ENV_FILE"
      log "ERROR: Editar $ENV_FILE con DB_PASSWORD real antes de continuar"
      exit 1
    fi
  fi
  if [[ ! -f "$CONF_FILE" ]]; then
    cp "$PROJECT_ROOT/config/production/odoo.conf.example" "$CONF_FILE"
    if [[ -f "$PROJECT_ROOT/config/test/odoo.conf" ]]; then
      grep '^admin_passwd' "$PROJECT_ROOT/config/test/odoo.conf" >> "$CONF_FILE.tmp" 2>/dev/null || true
      if [[ -f "$CONF_FILE.tmp" ]]; then
        admin_line=$(grep '^admin_passwd' "$PROJECT_ROOT/config/test/odoo.conf")
        sed -i "s|^admin_passwd.*|$admin_line|" "$CONF_FILE"
        rm -f "$CONF_FILE.tmp"
      fi
    fi
  fi
}

sync_repo() {
  if [[ -d "$REPO/.git" ]]; then
    cd "$REPO"
    git fetch origin 2>/dev/null || true
    git checkout "$COMMIT" 2>/dev/null || git checkout "origin/$COMMIT"
    git pull origin "$COMMIT" 2>/dev/null || true
    hellenia_sync_from_repo "$REPO" "$PROJECT_ROOT"
    log "Repo sincronizado: $(git -C "$REPO" rev-parse --short HEAD)"
  else
    log "WARN: Sin repo Git en $REPO — usando scripts locales"
  fi
}

wait_healthy() {
  local container="$1" max="${2:-60}" i=0
  while (( i < max )); do
    if docker inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null | grep -q healthy; then
      return 0
    fi
    sleep 5
    ((i++)) || true
  done
  return 1
}

log "=== Despliegue hellenia-prod (pre-Go-Live) ==="
require_dns
sync_repo
ensure_config
hellenia_load_env "$ENV_FILE"

if hellenia_container_running "hellenia-prod-odoo-1"; then
  log "Stack hellenia-prod ya existe — modo actualización"
else
  log "Stack hellenia-prod nuevo — instalación completa"
fi

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" pull odoo db 2>/dev/null || true
docker compose --env-file "$ENV_FILE" up -d db
wait_healthy "hellenia-prod-db-1" 24 || { log "ERROR: DB no healthy"; exit 1; }

DB_EXISTS=$(docker exec hellenia-prod-db-1 psql -U "${DB_USER}" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='${ODOO_DB_NAME}'" 2>/dev/null | tr -d '[:space:]' || true)

if [[ "$DB_EXISTS" != "1" ]]; then
  log "Creando BD ${ODOO_DB_NAME}..."
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -i base --stop-after-init --without-demo=all 2>&1 | tail -20 | tee -a "$LOG_FILE"

  log "Instalando web_enterprise..."
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -i web_enterprise --stop-after-init 2>&1 | tail -25 | tee -a "$LOG_FILE"
else
  log "BD ${ODOO_DB_NAME} ya existe — omitiendo init base"
fi

docker compose --env-file "$ENV_FILE" up -d odoo
wait_healthy "hellenia-prod-odoo-1" 36 || log "WARN: Odoo aún iniciando"

log "Fase 11 — es_DO + módulos oficiales + Justech..."
"$SCRIPT_DIR/run-phase11-spanish-config.sh" prod 2>&1 | tee -a "$LOG_FILE"

log "Fase 8 — Golden Configuration (sin datos piloto)..."
"$SCRIPT_DIR/apply-phase8-parameterization.sh" prod 2>&1 | tee -a "$LOG_FILE"

for mod in justech_l10n_do_base justech_l10n_do_ncf justech_l10n_do_reports; do
  state=$(docker exec hellenia-prod-db-1 psql -U odoo -d "${ODOO_DB_NAME}" -tAc \
    "SELECT state FROM ir_module_module WHERE name='${mod}'" 2>/dev/null | tr -d '[:space:]' || true)
  if [[ "$state" != "installed" ]]; then
    log "Instalando ${mod}..."
    "$SCRIPT_DIR/install-phase6-mvp-module.sh" prod "$mod" 2>&1 | tee -a "$LOG_FILE"
  fi
done

log "Sincronizando credenciales desde DEV..."
"$SCRIPT_DIR/sync-prod-credentials.sh" 2>&1 | tee -a "$LOG_FILE"

log "Registrando licencia Enterprise (${SUBSCRIPTION_CODE})..."
SUBSCRIPTION_CODE="$SUBSCRIPTION_CODE" "$SCRIPT_DIR/register-enterprise-prod.sh" 2>&1 | tee -a "$LOG_FILE" || true

log "Validación Golden Configuration..."
"$SCRIPT_DIR/validate-phase35-golden-config.sh" prod 2>&1 | tee -a "$LOG_FILE" || true

log "Validación MVP Justech..."
"$SCRIPT_DIR/validate-phase6-mvp.sh" prod 2>&1 | tee -a "$LOG_FILE" || true

log "Validación configuración Fase 12..."
"$SCRIPT_DIR/run-odoo-shell-env.sh" prod phase12-validate-configuration.py PHASE12 \
  "evidence/phase12-config-prod.json" 2>&1 | tee -a "$LOG_FILE" || true

log "Backup inicial producción..."
"$SCRIPT_DIR/backup-hellenia-prod.sh" 2>&1 | tee -a "$LOG_FILE" || true

log "Configurando cron backups + healthcheck..."
"$SCRIPT_DIR/setup-prod-monitoring-cron.sh" 2>&1 | tee -a "$LOG_FILE" || true

docker compose --env-file "$ENV_FILE" up -d
sleep 10

CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://prod.hellenia.cloud/web/login 2>/dev/null || echo "000")
log "HTTPS prod.hellenia.cloud /web/login → HTTP $CODE"

log "=== Despliegue hellenia-prod completado ==="
log "URL validación: https://prod.hellenia.cloud"
log "web.base.url:   https://odoo.hellenia.cloud (activo en BD, DNS sin corte)"
log "Log: $LOG_FILE"
