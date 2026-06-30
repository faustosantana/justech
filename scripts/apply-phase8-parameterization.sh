#!/usr/bin/env bash
# Fase 8 — Aplicar parametrización funcional (solo DEV)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-dev}"
if [[ "$ENV_NAME" != "dev" ]]; then
  hellenia_log "ERROR: Fase 8 solo opera en DEV"
  exit 1
fi

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"
OUT="${PROJECT_ROOT}/evidence/phase8-apply-${ENV_NAME}.json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/apply-phase8-parameterization.py" 2>/dev/null \
  | tee "${PROJECT_ROOT}/evidence/phase8-apply-${ENV_NAME}.log" \
  | python3 -c "import sys; d=sys.stdin.read(); i=d.find('PHASE8_APPLY:'); sys.stdout.write(d[i+13:] if i>=0 else d)" \
  > "$OUT"

hellenia_log "Parametrización Fase 8 ${ENV_NAME} → ${OUT}"
