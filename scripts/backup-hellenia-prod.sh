#!/usr/bin/env bash
# Backup hellenia-prod (post Go-Live) — plantilla Fase 12
# NO ejecutar hasta que hellenia-prod esté activo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
BACKUP_ROOT="$PROJECT_ROOT/backups/hellenia-prod"
TS=$(date +%Y-%m-%d_%H%M)
DEST="${BACKUP_ROOT}/${TS}"

if [[ ! -f "$ENV_FILE" ]]; then
  hellenia_log "ERROR: config/production/.env no existe — desplegar prod primero"
  exit 1
fi

hellenia_load_env "$ENV_FILE"
PROJECT="${COMPOSE_PROJECT_NAME:-hellenia-prod}"
DB_CONTAINER="$(hellenia_container "$PROJECT" db)"
ODOO_VOLUME="$(hellenia_volume "$PROJECT" odoo-data)"

mkdir -p "$DEST"
hellenia_log "Backup hellenia-prod → $DEST"

docker exec "$DB_CONTAINER" pg_dumpall -U "${DB_USER}" | gzip > "${DEST}/postgres_all.sql.gz"
docker run --rm -v "${ODOO_VOLUME}:/data:ro" -v "${DEST}":/backup alpine \
  tar czf /backup/filestore.tar.gz -C /data .
tar czf "${DEST}/custom.tar.gz" -C "$PROJECT_ROOT" custom
cp "$PROJECT_ROOT/docker/production/docker-compose.yml" "${DEST}/"
[[ -f "$ENV_FILE" ]] && cp "$ENV_FILE" "${DEST}/.env.example.redacted"

hellenia_log "Backup hellenia-prod completado: $DEST"
