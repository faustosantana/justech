#!/usr/bin/env bash
# Backup hellenia-prod — producción Odoo 19 Hellenia
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
BACKUP_ROOT="${BACKUP_ROOT:-$PROJECT_ROOT/backups/hellenia-prod}"
TS=$(date +%Y-%m-%d_%H%M)
DEST="${BACKUP_ROOT}/${TS}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/backup-prod-${TS}.log"

if [[ ! -f "$ENV_FILE" ]]; then
  hellenia_log "ERROR: config/production/.env no existe — desplegar prod primero"
  exit 1
fi

mkdir -p "${DEST}" "$(dirname "$LOG_FILE")"
hellenia_load_env "${ENV_FILE}"

PROJECT="${COMPOSE_PROJECT_NAME:-hellenia-prod}"
DB_CONTAINER="$(hellenia_container "$PROJECT" db)"
ODOO_VOLUME="$(hellenia_volume "$PROJECT" odoo-data)"

hellenia_log "Iniciando backup hellenia-prod → ${DEST}" | tee -a "$LOG_FILE"

if hellenia_container_running "$DB_CONTAINER"; then
  docker exec "$DB_CONTAINER" pg_dumpall -U "${DB_USER}" | gzip > "${DEST}/postgres_all.sql.gz"
  hellenia_log "OK  PostgreSQL dump" | tee -a "$LOG_FILE"
else
  hellenia_log "ERROR: ${DB_CONTAINER} no está corriendo" | tee -a "$LOG_FILE"
  exit 1
fi

if docker volume inspect "$ODOO_VOLUME" &>/dev/null; then
  docker run --rm -v "${ODOO_VOLUME}:/data:ro" -v "${DEST}":/backup alpine \
    tar czf /backup/filestore.tar.gz -C /data .
  hellenia_log "OK  filestore" | tee -a "$LOG_FILE"
fi

tar czf "${DEST}/custom.tar.gz" -C "$PROJECT_ROOT" custom
cp "$PROJECT_ROOT/docker/production/docker-compose.yml" "${DEST}/"
cp "$PROJECT_ROOT/config/production/odoo.conf" "${DEST}/" 2>/dev/null || true
cp "${ENV_FILE}" "${DEST}/.env"

cat > "${DEST}/MANIFEST.txt" << EOF
timestamp=${TS}
environment=production
project=${PROJECT}
db_container=${DB_CONTAINER}
odoo_volume=${ODOO_VOLUME}
EOF

hellenia_mark_backup_tier "${BACKUP_ROOT}" "${DEST}"
hellenia_apply_retention "${BACKUP_ROOT}" 7 4 12

hellenia_log "Backup hellenia-prod completado: ${DEST}" | tee -a "$LOG_FILE"
