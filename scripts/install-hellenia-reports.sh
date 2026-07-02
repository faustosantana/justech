#!/usr/bin/env bash
# Fase 13.6 — Instalar hellenia_reports en TEST o PROD
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-test}"
ACTION="${2:-install}"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_DIR="$(hellenia_env_dir "$ENV_NAME")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_DIR}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_DIR}"

hellenia_load_env "$ENV_FILE"
hellenia_log "Fase 13.6 — ${ACTION} hellenia_reports en ${ENV_NAME} (${ODOO_DB_NAME})"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" stop odoo

for MOD in hellenia_base hellenia_reports; do
  hellenia_log "Procesando módulo ${MOD}..."
  if [[ "$ACTION" == "upgrade" ]]; then
    docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
      -d "${ODOO_DB_NAME}" \
      --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
      -u "${MOD}" --stop-after-init
  else
    STATE=$(docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
      -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
      <<< "mod=env['ir.module.module'].search([('name','=','${MOD}')],limit=1); print(mod.state if mod else 'missing')" 2>/dev/null | tail -1 || echo "missing")
    if [[ "$STATE" == "installed" ]]; then
      docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
        -d "${ODOO_DB_NAME}" \
        --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
        -u "${MOD}" --stop-after-init
    else
      docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
        -d "${ODOO_DB_NAME}" \
        --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
        -i "${MOD}" --stop-after-init
    fi
  fi
done

docker compose --env-file "$ENV_FILE" up -d odoo
hellenia_log "hellenia_reports listo en ${ENV_NAME}"
