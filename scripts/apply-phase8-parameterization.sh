#!/usr/bin/env bash
# Fase 8 — Aplicar parametrización funcional (solo DEV)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-dev}"
if [[ "$ENV_NAME" != "dev" && "$ENV_NAME" != "test" && "$ENV_NAME" != "prod" ]]; then
  hellenia_log "ERROR: Fase 8 solo opera en dev|test|prod"
  exit 1
fi

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"
OUT="${PROJECT_ROOT}/evidence/phase8-apply-${ENV_NAME}.json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

WEB_BASE_URL="https://dev.hellenia.cloud"
[[ "$ENV_NAME" == "test" ]] && WEB_BASE_URL="https://test.hellenia.cloud"
[[ "$ENV_NAME" == "prod" ]] && WEB_BASE_URL="https://odoo.hellenia.cloud"

SKIP_PILOT_ARGS=()
[[ "$ENV_NAME" == "prod" ]] && SKIP_PILOT_ARGS=(-e HELLENIA_SKIP_PILOT=1)

docker compose --env-file "$ENV_FILE" run --rm -T -e WEB_BASE_URL="$WEB_BASE_URL" "${SKIP_PILOT_ARGS[@]}" odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/apply-phase8-parameterization.py" 2>/dev/null \
  | tee "${PROJECT_ROOT}/evidence/phase8-apply-${ENV_NAME}.log" \
  | python3 -c "import sys; d=sys.stdin.read(); i=d.find('PHASE8_APPLY:'); sys.stdout.write(d[i+13:] if i>=0 else d)" \
  > "$OUT"

hellenia_log "Parametrización Fase 8 ${ENV_NAME} → ${OUT}"
