#!/usr/bin/env bash
# Verifica que un backup DEV contiene todos los artefactos requeridos
# Uso: verify-backup-dev.sh [ruta-backup-timestamp]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

BACKUP_DIR="${1:-}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/odoo-projects/hellenia/backups/dev}"
FAIL=0

if [[ -z "$BACKUP_DIR" ]]; then
  BACKUP_DIR=$(ls -1dt "${BACKUP_ROOT}"/20* 2>/dev/null | grep -vE '_weekly$|_monthly$' | head -1)
fi

[[ -d "$BACKUP_DIR" ]] || { hellenia_log "ERROR: backup no encontrado: $BACKUP_DIR"; exit 1; }

check_file() {
  local label="$1" path="$2" min_bytes="${3:-1}"
  if [[ ! -f "$path" ]]; then
    hellenia_log "FAIL $label — archivo ausente: $path"
    FAIL=1
    return
  fi
  local size
  size=$(stat -c%s "$path" 2>/dev/null || stat -f%z "$path")
  if [[ "$size" -lt "$min_bytes" ]]; then
    hellenia_log "FAIL $label — muy pequeño (${size} bytes): $path"
    FAIL=1
    return
  fi
  hellenia_log "OK  $label — $(basename "$path") (${size} bytes)"
}

hellenia_log "=== Verificación backup DEV ==="
hellenia_log "Directorio: $BACKUP_DIR"

check_file "PostgreSQL dump" "${BACKUP_DIR}/postgres_all.sql.gz" 1000
check_file "Filestore" "${BACKUP_DIR}/filestore.tar.gz" 100
check_file "docker-compose" "${BACKUP_DIR}/docker-compose.yml" 100
check_file "odoo.conf" "${BACKUP_DIR}/odoo.conf" 50
check_file ".env config" "${BACKUP_DIR}/.env" 20
check_file "custom" "${BACKUP_DIR}/custom.tar.gz" 50

if [[ -f "${BACKUP_DIR}/postgres_all.sql.gz" ]]; then
  if gunzip -t "${BACKUP_DIR}/postgres_all.sql.gz" 2>/dev/null; then
    hellenia_log "OK  postgres_all.sql.gz — integridad gzip"
  else
    hellenia_log "FAIL postgres_all.sql.gz — corrupto"
    FAIL=1
  fi
fi

if [[ -f "${BACKUP_DIR}/filestore.tar.gz" ]]; then
  if tar tzf "${BACKUP_DIR}/filestore.tar.gz" >/dev/null 2>&1; then
    hellenia_log "OK  filestore.tar.gz — integridad tar"
  else
    hellenia_log "FAIL filestore.tar.gz — corrupto"
    FAIL=1
  fi
fi

if [[ -f "${BACKUP_DIR}/custom.tar.gz" ]]; then
  if tar tzf "${BACKUP_DIR}/custom.tar.gz" >/dev/null 2>&1; then
    hellenia_log "OK  custom.tar.gz — integridad tar"
  else
    hellenia_log "FAIL custom.tar.gz — corrupto"
    FAIL=1
  fi
fi

if [[ "$FAIL" -eq 0 ]]; then
  hellenia_log "RESULTADO: backup completo y válido"
  exit 0
fi

hellenia_log "RESULTADO: backup incompleto o inválido"
exit 1
