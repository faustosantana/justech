#!/usr/bin/env bash
# Fase 7.5 — Auditoría seguridad
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: audit-security-phase75.sh dev|test}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"
OUT="${PROJECT_ROOT}/evidence/security-audit-${ENV_NAME}.json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/audit-security-phase75.py" 2>/dev/null \
  | python3 -c "import sys; d=sys.stdin.read(); i=d.find('SECURITY_AUDIT:'); sys.stdout.write(d[i+15:] if i>=0 else d)" \
  > "$OUT"

hellenia_log "Auditoría seguridad ${ENV_NAME} → ${OUT} ($(wc -c < "$OUT") bytes)"
