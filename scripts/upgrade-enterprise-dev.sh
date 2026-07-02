#!/usr/bin/env bash
# Upgrade Enterprise DEV — validación RD + despliegue imagen + re-ejecución TC-001/TC-002
#
# NO toca TEST ni PRODUCCIÓN.
#
# Uso:
#   upgrade-enterprise-dev.sh --status
#   upgrade-enterprise-dev.sh --validate-only [archivo.tar.gz]
#   upgrade-enterprise-dev.sh --execute [archivo.tar.gz]     # requiere aprobación explícita
#   upgrade-enterprise-dev.sh --rerun-tc001-tc002            # tras upgrade exitoso
#
# Variables opcionales:
#   ENTERPRISE_ARCHIVE       ruta al tarball (default: más reciente en downloads/enterprise/)
#   TC_BASELINE_BACKUP       backup para restaurar antes de repetir TC-001/TC-002
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOWNLOAD_DIR="$PROJECT_ROOT/downloads/enterprise"
ENV_FILE="$PROJECT_ROOT/config/dev/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/dev"
MODE="${1:-}"
ARCHIVE="${2:-${ENTERPRISE_ARCHIVE:-}}"
LOG_DIR="$PROJECT_ROOT/logs/deploy"
STAMP=$(date +%Y-%m-%d_%H%M%S)
LOG_FILE="$LOG_DIR/upgrade-enterprise-dev-${STAMP}.log"

mkdir -p "$LOG_DIR"

resolve_archive() {
  if [[ -z "$ARCHIVE" ]]; then
    ARCHIVE=$(find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' \) -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
  fi
  [[ -n "$ARCHIVE" && -f "$ARCHIVE" ]] || {
    hellenia_log "ERROR: archivo Enterprise no encontrado en $DOWNLOAD_DIR"
    exit 1
  }
}

running_dev_version() {
  docker exec hellenia-dev-odoo-1 python3 -c "import odoo.release as r; print(r.version)" 2>/dev/null || echo "unknown"
}

archive_pkg_version() {
  local archive="$1"
  tar xzf "$archive" -O "$(tar tzf "$archive" | grep -m1 PKG-INFO)" 2>/dev/null \
    | awk -F': ' '/^Version:/ {print $2; exit}'
}

compare_archives_in_dir() {
  find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' \) -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | while read -r _ts path; do
        local sha size ver
        sha=$(sha256sum "$path" | awk '{print $1}')
        size=$(stat -c%s "$path" 2>/dev/null || stat -f%z "$path")
        ver=$(archive_pkg_version "$path" 2>/dev/null || echo "?")
        echo "  $(basename "$path") | $ver | ${size} bytes | sha256=${sha:0:16}..."
      done
}

status_report() {
  hellenia_log "=== Estado Enterprise DEV ===" | tee -a "$LOG_FILE"
  local running
  running=$(running_dev_version)
  hellenia_log "DEV en ejecución: Odoo $running" | tee -a "$LOG_FILE"
  hellenia_log "Imagen: $(docker inspect hellenia-dev-odoo-1 --format '{{.Config.Image}}' 2>/dev/null || echo '?')" | tee -a "$LOG_FILE"

  hellenia_log "--- Archivos en $DOWNLOAD_DIR ---" | tee -a "$LOG_FILE"
  if [[ -d "$DOWNLOAD_DIR" ]]; then
    compare_archives_in_dir | tee -a "$LOG_FILE"
  else
    hellenia_log "(directorio vacío o inexistente)" | tee -a "$LOG_FILE"
  fi

  resolve_archive 2>/dev/null || true
  if [[ -f "${ARCHIVE:-}" ]]; then
    local pkg running_date archive_date
    pkg=$(archive_pkg_version "$ARCHIVE" 2>/dev/null || echo "?")
    running_date=$(echo "$running" | grep -oE '[0-9]{8}$' || echo "")
    archive_date=$(echo "$pkg" | grep -oE '[0-9]{8}$' || echo "")
    hellenia_log "Tarball seleccionado: $(basename "$ARCHIVE") ($pkg)" | tee -a "$LOG_FILE"
    if [[ -n "$running_date" && -n "$archive_date" && "$archive_date" -gt "$running_date" ]]; then
      hellenia_log "HAY actualización disponible: $running → $pkg" | tee -a "$LOG_FILE"
    elif [[ "$running_date" == "$archive_date" ]]; then
      hellenia_log "Tarball coincide con build en ejecución ($running_date)" | tee -a "$LOG_FILE"
    else
      hellenia_log "Comparar manualmente: running=$running tarball=$pkg" | tee -a "$LOG_FILE"
    fi
  fi

  hellenia_log "--- TEST / PROD (solo lectura) ---" | tee -a "$LOG_FILE"
  docker inspect hellenia-test-odoo-1 --format 'TEST imagen: {{.Config.Image}}' 2>/dev/null | tee -a "$LOG_FILE" || true
  docker inspect odoo-pecv-odoo-1 --format 'PROD imagen: {{.Config.Image}}' 2>/dev/null | tee -a "$LOG_FILE" || true

  hellenia_log "TC-003 y pruebas funcionales: BLOQUEADAS hasta upgrade DEV" | tee -a "$LOG_FILE"
}

validate_archive_rd() {
  local archive="$1"
  hellenia_log "=== Validación Enterprise + RD Etapa 1 ===" | tee -a "$LOG_FILE"
  hellenia_log "Archivo: $archive" | tee -a "$LOG_FILE"
  hellenia_log "SHA256: $(sha256sum "$archive" | awk '{print $1}')" | tee -a "$LOG_FILE"

  "${SCRIPT_DIR}/report-enterprise-tarball.sh" "$archive" 2>&1 | tee -a "$LOG_FILE"
  "${SCRIPT_DIR}/validate-enterprise-archive.sh" "$archive" --rd-stage1 --report 2>&1 | tee -a "$LOG_FILE"
}

upgrade_modules_post_image() {
  hellenia_log "--- Actualizar módulos Enterprise / RD en BD ---" | tee -a "$LOG_FILE"
  hellenia_load_env "$ENV_FILE"
  cd "$COMPOSE_DIR"
  local db="${ODOO_DB_NAME:-hellenia_dev}"

  docker compose --env-file "$ENV_FILE" stop odoo 2>&1 | tee -a "$LOG_FILE"
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "$db" --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
    -u web_enterprise,account,account_accountant,account_reports \
    --stop-after-init 2>&1 | tee -a "$LOG_FILE"

  # Si l10n_do ya instalado (post TC-001), actualizar; si no, solo asegurar disponibilidad
  local l10n_state
  l10n_state=$(docker exec hellenia-dev-db-1 psql -U odoo -d "$db" -tAc \
    "SELECT COALESCE(state,'absent') FROM ir_module_module WHERE name='l10n_do';" 2>/dev/null || echo "absent")
  if [[ "$l10n_state" == "installed" ]]; then
    hellenia_log "l10n_do instalado — actualizando cadena RD" | tee -a "$LOG_FILE"
    docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
      -d "$db" --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
      -u l10n_do,l10n_do_reports,l10n_do_check_printing \
      --stop-after-init 2>&1 | tee -a "$LOG_FILE"
  else
    hellenia_log "l10n_do no instalado — omitiendo -u l10n_do (TC-001 pendiente)" | tee -a "$LOG_FILE"
  fi

  docker compose --env-file "$ENV_FILE" up -d odoo 2>&1 | tee -a "$LOG_FILE"
  sleep 45
}

rerun_tc001_tc002() {
  hellenia_log "=== Repetir TC-001 y TC-002 desde cero ===" | tee -a "$LOG_FILE"

  local backup="${TC_BASELINE_BACKUP:-}"
  if [[ -z "$backup" ]]; then
    backup=$(ls -1dt /opt/odoo-projects/hellenia/backups/dev/20* 2>/dev/null | grep -vE '_weekly$|_monthly$' | head -1)
  fi

  if [[ -n "$backup" && -d "$backup" ]]; then
    hellenia_log "Restaurando BD desde backup: $backup" | tee -a "$LOG_FILE"
    hellenia_log "NOTA: usar backup pre-TC-001 si se desea línea base limpia (ej. 2026-06-30_0353)" | tee -a "$LOG_FILE"
    "${SCRIPT_DIR}/restore-dev.sh" "$backup" 2>&1 | tee -a "$LOG_FILE"
    sleep 30
  else
    hellenia_log "WARN: sin backup para restaurar — TC-001/002 sobre estado actual" | tee -a "$LOG_FILE"
  fi

  hellenia_log "--- TC-001: instalar l10n_do ---" | tee -a "$LOG_FILE"
  hellenia_load_env "$ENV_FILE"
  cd "$COMPOSE_DIR"
  local db="${ODOO_DB_NAME:-hellenia_dev}"
  docker compose --env-file "$ENV_FILE" stop odoo
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "$db" --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
    -i l10n_do --stop-after-init 2>&1 | tee -a "$LOG_FILE"
  docker compose --env-file "$ENV_FILE" up -d odoo
  sleep 45

  if command -v python3 &>/dev/null && [[ -f "${SCRIPT_DIR}/run-l10n-do-functional-tests.py" ]]; then
    hellenia_log "--- Evidencia TC-001 (XML-RPC) ---" | tee -a "$LOG_FILE"
    python3 "${SCRIPT_DIR}/run-l10n-do-functional-tests.py" --tc 001 2>&1 | tee -a "$LOG_FILE" || true
    hellenia_log "--- Evidencia TC-002 (XML-RPC) ---" | tee -a "$LOG_FILE"
    python3 "${SCRIPT_DIR}/run-l10n-do-functional-tests.py" --tc 002 2>&1 | tee -a "$LOG_FILE" || true
  fi

  hellenia_log "TC-001/TC-002 ejecutados — revisar docs/TC-001-RESULT.md y docs/TC-002-RESULT.md" | tee -a "$LOG_FILE"
  hellenia_log "TC-003 permanece BLOQUEADO hasta revisión manual de resultados" | tee -a "$LOG_FILE"
}

execute_upgrade() {
  local archive="$1"

  if [[ "${HELLENIA_APPROVE_ENTERPRISE_EXECUTE:-}" != "yes" ]]; then
    hellenia_log "ERROR: --execute bloqueado — requiere verificación portal y aprobación explícita"
    hellenia_log "Definir: export HELLENIA_APPROVE_ENTERPRISE_EXECUTE=yes"
    hellenia_log "Ver docs/ENTERPRISE-UPGRADE-DEV.md (Paso 0 — verificación manual portal)"
    exit 1
  fi

  validate_archive_rd "$archive"

  hellenia_log "=== EJECUCIÓN UPGRADE DEV (aprobación explícita) ===" | tee -a "$LOG_FILE"
  hellenia_log "NO se modifica TEST ni PRODUCCIÓN" | tee -a "$LOG_FILE"

  "${SCRIPT_DIR}/e1a-enterprise-image.sh" "$archive" 2>&1 | tee -a "$LOG_FILE"

  upgrade_modules_post_image

  hellenia_log "--- Validación post-upgrade ---" | tee -a "$LOG_FILE"
  "${SCRIPT_DIR}/validate-enterprise-dev.sh" --no-license 2>&1 | tee -a "$LOG_FILE"
  "${SCRIPT_DIR}/healthcheck.sh" 2>&1 | tee -a "$LOG_FILE"

  local new_ver
  new_ver=$(running_dev_version)
  hellenia_log "DEV actualizado: Odoo $new_ver" | tee -a "$LOG_FILE"
  hellenia_log "Siguiente paso: $0 --rerun-tc001-tc002" | tee -a "$LOG_FILE"
  hellenia_log "Log completo: $LOG_FILE" | tee -a "$LOG_FILE"
}

case "$MODE" in
  --status)
    status_report
    ;;
  --validate-only)
    resolve_archive
    validate_archive_rd "$ARCHIVE"
    hellenia_log "Validación OK — sin cambios en DEV (use --execute tras aprobación)" | tee -a "$LOG_FILE"
    ;;
  --execute)
    resolve_archive
    execute_upgrade "$ARCHIVE"
    ;;
  --rerun-tc001-tc002)
    rerun_tc001_tc002
    ;;
  *)
    hellenia_log "Uso: $0 --status"
    hellenia_log "     $0 --validate-only [archivo.tar.gz]"
    hellenia_log "     $0 --execute [archivo.tar.gz]   # solo tras aprobación"
    hellenia_log "     $0 --rerun-tc001-tc002"
    exit 1
    ;;
esac
