#!/usr/bin/env bash
# Actualiza imagen Community (tag pinneado en docker-compose)
# Uso: upgrade-community.sh dev|test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: upgrade-community.sh dev|test}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"

hellenia_load_env "$ENV_FILE"

hellenia_log "=== Upgrade Community ${ENV_NAME} ==="
"${SCRIPT_DIR}/backup-${ENV_NAME}.sh"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" pull odoo
docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo

hellenia_log "Community actualizado. Verificar con validate-odoo19.sh ${ENV_NAME}"
