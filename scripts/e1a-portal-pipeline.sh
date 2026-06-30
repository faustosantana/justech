#!/usr/bin/env bash
# Pipeline E1a portal — solo validación por defecto
# Uso:
#   e1a-portal-pipeline.sh --validate-only [archivo]
#   e1a-portal-pipeline.sh --execute [archivo]   # REQUIERE aprobación explícita
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODE="${1:-}"
ARCHIVE="${2:-}"
DOWNLOAD_DIR="$PROJECT_ROOT/downloads/enterprise"

if [[ -z "$ARCHIVE" ]]; then
  ARCHIVE=$(find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' \) -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
fi

case "$MODE" in
  --validate-only)
    hellenia_log "=== E1a portal — solo validación ==="
    [[ -f "$ARCHIVE" ]] || { hellenia_log "ERROR: archivo no encontrado"; exit 1; }
    "${SCRIPT_DIR}/validate-enterprise-archive.sh" "$ARCHIVE" --report
    hellenia_log "Sin extract/install (E1a no aprobado)"
    ;;
  --execute)
    hellenia_log "=== E1a portal — ejecución completa ==="
    hellenia_log "Requiere aprobación explícita del usuario"
    [[ -f "$ARCHIVE" ]] || { hellenia_log "ERROR: archivo no encontrado"; exit 1; }
    "${SCRIPT_DIR}/validate-enterprise-archive.sh" "$ARCHIVE" --report
    "${SCRIPT_DIR}/backup-dev.sh"
    "${SCRIPT_DIR}/extract-enterprise-portal.sh" "$ARCHIVE"
    ENV_FILE="$PROJECT_ROOT/config/dev/.env"
    COMPOSE_DIR="$PROJECT_ROOT/docker/dev"
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    cd "$COMPOSE_DIR"
    docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo
    sleep 50
    docker compose --env-file "$ENV_FILE" stop odoo
    docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
      -d "${ODOO_DB_NAME:-hellenia_dev}" \
      --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
      -i web_enterprise --stop-after-init
    docker compose --env-file "$ENV_FILE" up -d odoo
    sleep 45
    "${SCRIPT_DIR}/validate-enterprise-dev.sh"
    ;;
  *)
    hellenia_log "Uso: $0 --validate-only [archivo]"
    hellenia_log "     $0 --execute [archivo]  # solo tras aprobación E1a"
    exit 1
    ;;
esac
