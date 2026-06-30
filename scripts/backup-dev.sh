#!/usr/bin/env bash
# Backup dev — Hellenia Odoo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_DIR="$PROJECT_ROOT/docker/dev"
ENV_FILE="$PROJECT_ROOT/config/dev/.env"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/odoo-projects/hellenia/backups/dev}"
TS=$(date +%Y-%m-%d_%H%M)
DEST="${BACKUP_ROOT}/${TS}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/backup-dev-${TS}.log"

mkdir -p "${DEST}" "$(dirname "$LOG_FILE")"
hellenia_load_env "${ENV_FILE}"

PROJECT="${COMPOSE_PROJECT_NAME:-hellenia-dev}"
DB_CONTAINER="$(hellenia_container "$PROJECT" db)"
ODOO_VOLUME="$(hellenia_volume "$PROJECT" odoo-data)"

hellenia_log "Iniciando backup dev → ${DEST}" | tee -a "$LOG_FILE"

if hellenia_container_running "$DB_CONTAINER"; then
  docker exec "$DB_CONTAINER" pg_dumpall -U "${DB_USER:-odoo}" | gzip > "${DEST}/postgres_all.sql.gz"
  hellenia_log "OK  PostgreSQL dump" | tee -a "$LOG_FILE"
else
  hellenia_log "WARN: ${DB_CONTAINER} no está corriendo — sin dump PostgreSQL" | tee -a "$LOG_FILE"
fi

if docker volume inspect "$ODOO_VOLUME" &>/dev/null; then
  docker run --rm -v "${ODOO_VOLUME}:/data:ro" -v "${DEST}":/backup alpine \
    tar czf /backup/filestore.tar.gz -C /data .
  hellenia_log "OK  filestore" | tee -a "$LOG_FILE"
else
  hellenia_log "WARN: volumen ${ODOO_VOLUME} no encontrado" | tee -a "$LOG_FILE"
fi

tar czf "${DEST}/custom.tar.gz" -C "$PROJECT_ROOT" custom
cp "${COMPOSE_DIR}/docker-compose.yml" "${DEST}/"
cp "$PROJECT_ROOT/config/dev/odoo.conf" "${DEST}/"
cp "${ENV_FILE}" "${DEST}/.env"

# Manifest para auditoría
cat > "${DEST}/MANIFEST.txt" << EOF
timestamp=${TS}
environment=dev
project=${PROJECT}
db_container=${DB_CONTAINER}
odoo_volume=${ODOO_VOLUME}
EOF

hellenia_mark_backup_tier "${BACKUP_ROOT}" "${DEST}"
hellenia_apply_retention "${BACKUP_ROOT}" 7 4 6

# Verificación obligatoria antes de declarar éxito
if ! hellenia_container_running "$DB_CONTAINER"; then
  hellenia_log "WARN: backup parcial — BD no estaba corriendo"
elif [[ ! -f "${DEST}/postgres_all.sql.gz" ]]; then
  hellenia_log "ERROR: falta postgres_all.sql.gz"
  exit 1
fi

if docker volume inspect "$ODOO_VOLUME" &>/dev/null && [[ ! -f "${DEST}/filestore.tar.gz" ]]; then
  hellenia_log "ERROR: falta filestore.tar.gz"
  exit 1
fi

for req in custom.tar.gz docker-compose.yml odoo.conf .env; do
  [[ -f "${DEST}/${req}" ]] || { hellenia_log "ERROR: falta ${req}"; exit 1; }
done

"${SCRIPT_DIR}/verify-backup-dev.sh" "${DEST}"

hellenia_log "Backup dev completado: ${DEST}" | tee -a "$LOG_FILE"
