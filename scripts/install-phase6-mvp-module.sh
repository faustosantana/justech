#!/usr/bin/env bash
# Fase 6 — Instalación incremental MVP Justech l10n DO en DEV
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-dev}"
MODULE="${2:?Uso: install-phase6-mvp-module.sh dev <modulo>}"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_DIR="$(hellenia_env_dir "$ENV_NAME")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_DIR}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_DIR}"

hellenia_load_env "$ENV_FILE"
hellenia_log "Instalando módulo ${MODULE} en ${ENV_NAME} (con tests)"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" stop odoo
docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
  -d "${ODOO_DB_NAME}" \
  --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -i "${MODULE}" --test-enable --stop-after-init
docker compose --env-file "$ENV_FILE" up -d odoo

hellenia_log "Módulo ${MODULE} instalado"
