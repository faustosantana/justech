#!/usr/bin/env bash
# Actualiza módulos custom en BD (sin cambiar código fuente)
# Uso: update-custom-modules.sh dev hellenia_base [otro_modulo...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: update-custom-modules.sh dev|test <modulo> [modulo...]}"
shift
MODULES=("$@")

if [[ ${#MODULES[@]} -eq 0 ]]; then
  hellenia_log "ERROR: Indicar al menos un módulo"
  exit 1
fi

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"

hellenia_load_env "$ENV_FILE"
MODULE_LIST=$(IFS=,; echo "${MODULES[*]}")

hellenia_log "Actualizando módulos: ${MODULE_LIST} en ${ENV_NAME}"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" stop odoo
docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
  -d "${ODOO_DB_NAME}" \
  --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u "${MODULE_LIST}" --stop-after-init
docker compose --env-file "$ENV_FILE" up -d odoo

hellenia_log "Módulos actualizados"
