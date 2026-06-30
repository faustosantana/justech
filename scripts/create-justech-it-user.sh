#!/usr/bin/env bash
# Fase 7 — Crear usuario técnico it@justech.do (requiere JUSTECH_IT_PASSWORD)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: create-justech-it-user.sh dev|test|prod}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"

if [[ -z "${JUSTECH_IT_PASSWORD:-}" ]]; then
  hellenia_log "ERROR: Defina JUSTECH_IT_PASSWORD (no inventar contraseña)"
  exit 2
fi

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

docker compose --env-file "$ENV_FILE" run --rm -T -e JUSTECH_IT_PASSWORD odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/create-justech-it-user.py"
