#!/usr/bin/env bash
# Backup dev — Hellenia Odoo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_DIR="docker/dev"
ENV_FILE="$PROJECT_ROOT/config/dev/.env"
BACKUP_ROOT="/opt/odoo-projects/hellenia/backups/dev"
TS=$(date +%Y-%m-%d_%H%M)
DEST="${BACKUP_ROOT}/${TS}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/backup-dev-${TS}.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

apply_retention() {
  local backup_root="$1"
  local daily_days="${2:-7}"
  local weekly_weeks="${3:-4}"
  local monthly_months="${4:-6}"

  # Daily: remove backups older than N days (except weekly/monthly markers)
  find "${backup_root}" -maxdepth 1 -type d -name '20*' ! -name '*_weekly' ! -name '*_monthly' -mtime +"${daily_days}" -exec rm -rf {} + 2>/dev/null || true

  # Weekly markers: keep last N weekly (dirs ending _weekly)
  ls -1dt "${backup_root}"/20*_weekly 2>/dev/null | tail -n +$((weekly_weeks + 1)) | xargs -r rm -rf

  # Monthly markers: keep last N monthly
  ls -1dt "${backup_root}"/20*_monthly 2>/dev/null | tail -n +$((monthly_months + 1)) | xargs -r rm -rf
}

mark_backup_tier() {
  local dest="$1"
  local dow
  local dom
  dow=$(date +%u)
  dom=$(date +%d)
  if [[ "${dom}" == "01" ]]; then
    ln -sfn "$(basename "${dest}")" "${dest}_monthly" 2>/dev/null || cp -al "${dest}" "${dest}_monthly" 2>/dev/null || true
  fi
  if [[ "${dow}" == "7" ]]; then
    ln -sfn "$(basename "${dest}")" "${dest}_weekly" 2>/dev/null || cp -al "${dest}" "${dest}_weekly" 2>/dev/null || true
  fi
}


mkdir -p "${DEST}" "$(dirname "$LOG_FILE")"

if [[ ! -f "${ENV_FILE}" ]]; then
  log "ERROR: Falta ${ENV_FILE} — copiar desde .env.example"
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

log "Iniciando backup dev → ${DEST}" | tee -a "$LOG_FILE"

if docker ps --format '{{.Names}}' | grep -q '^hellenia-dev-odoo-1$'; then
  docker exec hellenia-dev-db-1 pg_dumpall -U "${DB_USER:-odoo}" | gzip > "${DEST}/postgres_all.sql.gz"
  docker run --rm -v hellenia-dev_odoo-data:/data:ro -v "${DEST}":/backup alpine \
    tar czf /backup/filestore.tar.gz -C /data .
else
  log "WARN: Contenedor hellenia-dev-odoo-1 no está corriendo — backup parcial" | tee -a "$LOG_FILE"
fi

tar czf "${DEST}/addons.tar.gz" -C "$PROJECT_ROOT" addons
cp "${COMPOSE_DIR}/docker-compose.yml" "${DEST}/"
cp "$PROJECT_ROOT/config/dev/odoo.conf" "${DEST}/"
cp "${ENV_FILE}" "${DEST}/.env"

mark_backup_tier "${DEST}"
apply_retention "${BACKUP_ROOT}" 7 4 6

log "Backup dev completado: ${DEST}" | tee -a "$LOG_FILE"
