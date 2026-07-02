#!/usr/bin/env bash
# Restaura backup TEST desde directorio timestamp
# Uso: restore-test.sh /opt/odoo-projects/hellenia/backups/test/2026-06-30_1200
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

BACKUP_DIR="${1:?Uso: restore-test.sh <ruta-backup-timestamp>}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"

hellenia_require_file "${BACKUP_DIR}/postgres_all.sql.gz"
hellenia_load_env "${ENV_FILE}"

PROJECT="${COMPOSE_PROJECT_NAME:-hellenia-test}"
DB_CONTAINER="$(hellenia_container "$PROJECT" db)"
ODOO_VOLUME="$(hellenia_volume "$PROJECT" odoo-data)"

hellenia_log "Backup de seguridad antes de restaurar..."
"${SCRIPT_DIR}/backup-test.sh"

hellenia_log "Deteniendo Odoo TEST..."
cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" stop odoo

hellenia_log "Restaurando PostgreSQL..."
gunzip -c "${BACKUP_DIR}/postgres_all.sql.gz" | docker exec -i "$DB_CONTAINER" psql -U "${DB_USER}" -d postgres

if [[ -f "${BACKUP_DIR}/filestore.tar.gz" ]]; then
  hellenia_log "Restaurando filestore..."
  docker run --rm -v "${ODOO_VOLUME}:/data" -v "${BACKUP_DIR}":/backup alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/filestore.tar.gz -C /data"
fi

if [[ -f "${BACKUP_DIR}/custom.tar.gz" ]]; then
  hellenia_log "Restaurando custom addons..."
  tar xzf "${BACKUP_DIR}/custom.tar.gz" -C "$PROJECT_ROOT"
fi

docker compose --env-file "$ENV_FILE" start odoo
hellenia_log "Restauración TEST completada desde ${BACKUP_DIR}"
