#!/usr/bin/env bash
# Cron root: backup diario hellenia-prod + healthcheck semanal
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MARKER="# hellenia-prod-monitoring"
BACKUP_LINE="15 2 * * * cd ${PROJECT_ROOT} && ${PROJECT_ROOT}/scripts/backup-hellenia-prod.sh >> ${PROJECT_ROOT}/logs/deploy/cron-backup-prod.log 2>&1"
HEALTH_LINE="30 6 * * 1 cd ${PROJECT_ROOT} && ${PROJECT_ROOT}/scripts/healthcheck.sh >> ${PROJECT_ROOT}/logs/deploy/cron-healthcheck.log 2>&1"

TMP=$(mktemp)
crontab -l 2>/dev/null | grep -v "$MARKER" | grep -v "backup-hellenia-prod.sh" | grep -v "healthcheck.sh" > "$TMP" || true
{
  cat "$TMP"
  echo "$MARKER backup"
  echo "$BACKUP_LINE"
  echo "$MARKER healthcheck"
  echo "$HEALTH_LINE"
} | crontab -
rm -f "$TMP"

hellenia_log "Cron configurado:"
crontab -l | grep -A1 hellenia-prod-monitoring || true
