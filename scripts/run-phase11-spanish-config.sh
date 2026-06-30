#!/usr/bin/env bash
# Fase 11 — Aplicar idioma es_DO + validar módulos oficiales (DEV o TEST)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: run-phase11-spanish-config.sh dev|test|prod}"
if [[ "$ENV_NAME" != "dev" && "$ENV_NAME" != "test" && "$ENV_NAME" != "prod" ]]; then
  hellenia_log "ERROR: solo dev|test|prod"
  exit 1
fi

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_DIR="$(hellenia_env_dir "$ENV_NAME")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_DIR}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_DIR}"
OUT="${PROJECT_ROOT}/evidence/phase11-spanish-${ENV_NAME}.json"
LOG="${PROJECT_ROOT}/evidence/phase11-spanish-${ENV_NAME}.log"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/apply-phase11-spanish-and-modules.py" > "$TMP" 2>&1
RC=$?
set -e

tee "$LOG" < "$TMP" >/dev/null

if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR: odoo shell exit $RC (${ENV_NAME})"
  tail -40 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

python3 -c "
import sys, json
d = open('$TMP').read()
i = d.find('PHASE11_CONFIG:')
if i < 0:
    print(d[-4000:], file=sys.stderr)
    sys.exit(1)
payload = d[i + len('PHASE11_CONFIG:'):].strip()
open('$OUT', 'w').write(payload)
obj = json.loads(payload)
print(json.dumps({'ok': obj.get('ok'), 'env': '$ENV_NAME', 'english_items': len(obj.get('english_remainders', []))}))
sys.exit(0 if obj.get('ok') else 2)
"
PY_RC=$?
rm -f "$TMP"

if [[ $PY_RC -ne 0 ]]; then
  hellenia_log "WARN: Fase 11 ${ENV_NAME} completada con observaciones (ver ${OUT})"
  exit 0
fi

hellenia_log "Fase 11 español+módulos ${ENV_NAME} → ${OUT}"
