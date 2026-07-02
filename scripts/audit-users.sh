#!/usr/bin/env bash
# Fase 7 — Inventario usuarios Odoo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: audit-users.sh dev|test}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"
OUT="${PROJECT_ROOT}/evidence/uat-user-audit-${ENV_NAME}-$(date +%Y%m%d).json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/audit-users.py" 2>/dev/null | sed -n '/USER_AUDIT:/s/USER_AUDIT://p' | tee "$OUT"

hellenia_log "Auditoría usuarios ${ENV_NAME} → ${OUT}"
