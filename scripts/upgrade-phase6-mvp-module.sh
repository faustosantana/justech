#!/usr/bin/env bash
# Sprint 0 — Upgrade MVP Justech l10n DO en DEV (con tests)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-dev}"
MODULES="${2:-justech_l10n_do_base,justech_l10n_do_ncf,justech_l10n_do_reports}"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"

hellenia_load_env "$ENV_FILE"
hellenia_log "Upgrade módulos ${MODULES} en ${ENV_NAME} (con tests)"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" stop odoo
docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
  -d "${ODOO_DB_NAME}" \
  --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u "${MODULES}" --test-enable --stop-after-init
docker compose --env-file "$ENV_FILE" up -d odoo

hellenia_log "Upgrade completado: ${MODULES}"
