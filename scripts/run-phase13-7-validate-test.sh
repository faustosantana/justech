#!/usr/bin/env bash
# Fase 13.7 — Validación funcional TEST + redeploy Traefik labels
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"
OUT="$PROJECT_ROOT/evidence/phase13-7-test-functional-validation.json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

hellenia_log "Fase 13.7 — Redeploy TEST (Traefik labels + gevent)"
docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo

hellenia_log "Esperando healthcheck Odoo TEST..."
sleep 15

TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/phase13-7-validate-test.py" > "$TMP" 2>&1
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR shell exit $RC"
  tail -50 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

mkdir -p "$(dirname "$OUT")"
python3 -c "
import sys
d=open('$TMP').read()
m='PHASE13_7_TEST:'
i=d.find(m)
if i<0:
    print(d[-12000:], file=sys.stderr); sys.exit(1)
open('$OUT','w').write(d[i+len(m):].strip())
print('OK → $OUT')
"
tail -20 "$TMP"
rm -f "$TMP"

# Smoke HTTP TEST
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L "https://test.${TRAEFIK_HOST}/web/login" || echo "000")
hellenia_log "HTTP test.hellenia.cloud/login → $HTTP_CODE"
echo "{\"http_test_login\": $HTTP_CODE}" >> "${OUT%.json}-http.json" 2>/dev/null || true

hellenia_log "Validación Fase 13.7 TEST completada"
