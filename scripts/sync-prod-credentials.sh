#!/usr/bin/env bash
# Copiar hashes de contraseña admin + it@justech.do desde hellenia_dev → hellenia_prod
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
DEV_DB="hellenia-dev-db-1"

hellenia_load_env "$ENV_FILE"

if ! hellenia_container_running "$DEV_DB"; then
  hellenia_log "ERROR: $DEV_DB no está activo"
  exit 1
fi

fetch_hash() {
  local login="$1"
  docker exec "$DEV_DB" psql -U odoo -d hellenia_dev -tAc \
    "SELECT password FROM res_users WHERE login='${login}' AND active=true LIMIT 1" | tr -d '[:space:]'
}

fetch_user_field() {
  local field="$1"
  docker exec "$DEV_DB" psql -U odoo -d hellenia_dev -tAc \
    "SELECT ${field} FROM res_users WHERE login='it@justech.do' AND active=true LIMIT 1" | tr -d '\r'
}

ADMIN_HASH="$(fetch_hash admin)"
IT_HASH="$(fetch_hash 'it@justech.do')"

if [[ -z "$ADMIN_HASH" || -z "$IT_HASH" ]]; then
  hellenia_log "ERROR: No se pudieron leer hashes desde hellenia_dev"
  exit 1
fi

SYNC_IT_NAME="$(fetch_user_field name)"
SYNC_IT_EMAIL="$(fetch_user_field email)"
SYNC_IT_LANG="$(fetch_user_field lang)"
SYNC_IT_TZ="$(fetch_user_field tz)"

hellenia_log "Sincronizando credenciales DEV → PROD (solo hashes, sin contraseñas en claro)"

cd "$COMPOSE_DIR"
TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T \
  -e SYNC_ADMIN_HASH="$ADMIN_HASH" \
  -e SYNC_IT_HASH="$IT_HASH" \
  -e SYNC_IT_NAME="$SYNC_IT_NAME" \
  -e SYNC_IT_EMAIL="$SYNC_IT_EMAIL" \
  -e SYNC_IT_LANG="$SYNC_IT_LANG" \
  -e SYNC_IT_TZ="$SYNC_IT_TZ" \
  odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/sync-prod-credentials.py" > "$TMP" 2>&1
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR: sync credentials exit $RC"
  tail -40 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

OUT="${PROJECT_ROOT}/evidence/prod-credentials-sync.json"
python3 -c "
import sys, json
d = open('$TMP').read()
i = d.find('SYNC_PROD_CREDENTIALS:')
if i < 0:
    print(d[-4000:], file=sys.stderr)
    sys.exit(1)
open('$OUT', 'w').write(d[i+len('SYNC_PROD_CREDENTIALS:'):].strip())
print('OK → $OUT')
"

rm -f "$TMP"
hellenia_log "Credenciales sincronizadas → ${OUT}"
