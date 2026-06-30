#!/usr/bin/env bash
# Restaura backup de producción actual hacia ambiente TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${1:?Uso: restore-production-to-test.sh /opt/odoo-projects/hellenia/backups/production/YYYY-MM-DD_HHMM}"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

[[ -f "${BACKUP_DIR}/postgres_all.sql.gz" ]] || { log "ERROR: backup inválido"; exit 1; }

# shellcheck disable=SC1090
source "$ENV_FILE"

log "Backup de TEST antes de restaurar..."
"$SCRIPT_DIR/backup-test.sh"

log "Deteniendo Odoo TEST..."
cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" stop odoo

log "Restaurando PostgreSQL en TEST..."
gunzip -c "${BACKUP_DIR}/postgres_all.sql.gz" | docker exec -i hellenia-test-db-1 psql -U "${DB_USER}" -d postgres

if [[ -f "${BACKUP_DIR}/filestore.tar.gz" ]]; then
  log "Restaurando filestore en TEST..."
  docker run --rm -v hellenia-test_odoo-data:/data -v "${BACKUP_DIR}":/backup alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/filestore.tar.gz -C /data"
fi

if [[ -f "${BACKUP_DIR}/addons_volume.tar.gz" ]]; then
  log "Restaurando addons desde volumen producción..."
  tar xzf "${BACKUP_DIR}/addons_volume.tar.gz" -C "$PROJECT_ROOT/addons"
fi

docker compose --env-file "$ENV_FILE" start odoo
log "Restauración producción → TEST completada desde ${BACKUP_DIR}"
