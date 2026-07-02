#!/usr/bin/env bash
# Backup producción ACTUAL (/docker/odoo-pecv) — sin modificar el stack
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_ROOT="$PROJECT_ROOT/backups/production"
TS=$(date +%Y-%m-%d_%H%M)
DEST="${BACKUP_ROOT}/${TS}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/backup-production-${TS}.log"
PROD_ENV="/docker/odoo-pecv/.env"

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

if ! docker ps --format '{{.Names}}' | grep -q '^odoo-pecv-odoo-1$'; then
  log "ERROR: odoo-pecv-odoo-1 no está corriendo" | tee -a "$LOG_FILE"
  exit 1
fi

log "Backup producción actual (odoo-pecv) → ${DEST}" | tee -a "$LOG_FILE"

docker exec odoo-pecv-db-1 pg_dumpall -U odoo | gzip > "${DEST}/postgres_all.sql.gz"
docker run --rm -v odoo-pecv_odoo-data:/data:ro -v "${DEST}":/backup alpine \
  tar czf /backup/filestore.tar.gz -C /data .
docker run --rm -v odoo-pecv_odoo-addons:/data:ro -v "${DEST}":/backup alpine \
  tar czf /backup/addons_volume.tar.gz -C /data .

cp /docker/odoo-pecv/docker-compose.yml "${DEST}/"
[[ -f "${PROD_ENV}" ]] && cp "${PROD_ENV}" "${DEST}/.env"
[[ -f "$PROJECT_ROOT/config/production/README.md" ]] && cp "$PROJECT_ROOT/config/production/README.md" "${DEST}/PRODUCTION-REFERENCE.md" || true

mark_backup_tier "${DEST}"
apply_retention "${BACKUP_ROOT}" 7 4 6

log "Backup producción completado: ${DEST}" | tee -a "$LOG_FILE"
