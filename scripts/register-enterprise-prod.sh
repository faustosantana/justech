#!/usr/bin/env bash
# Registrar licencia Enterprise en hellenia_prod
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
SUBSCRIPTION_CODE="${SUBSCRIPTION_CODE:-M260616306091776}"
OUT="${PROJECT_ROOT}/evidence/prod-enterprise-registration.json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T -e SUBSCRIPTION_CODE="$SUBSCRIPTION_CODE" odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/register-enterprise-prod.py" > "$TMP" 2>&1
RC=$?
set -e

tee "${PROJECT_ROOT}/evidence/prod-enterprise-registration.log" < "$TMP" >/dev/null

python3 -c "
import sys, json
d = open('$TMP').read()
i = d.find('REGISTER_ENTERPRISE:')
if i < 0:
    print(d[-5000:], file=sys.stderr)
    sys.exit(1)
payload = d[i+len('REGISTER_ENTERPRISE:'):].strip()
open('$OUT', 'w').write(payload)
obj = json.loads(payload)
print(json.dumps({'ok': obj.get('ok'), 'already_linked': obj.get('already_linked')}))
sys.exit(0 if obj.get('ok') else 2)
"
PY_RC=$?
rm -f "$TMP"

if [[ $PY_RC -ne 0 ]]; then
  hellenia_log "WARN: Registro Enterprise requiere revisión (ver ${OUT})"
  exit 0
fi

hellenia_log "Licencia Enterprise registrada → ${OUT}"
