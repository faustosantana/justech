#!/usr/bin/env bash
# Fase 19.1 — validación real exportador 606 en TEST (VPS)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"
EVIDENCE="${EVIDENCE_DIR}/phase19-606-test.json"
EXCEL="${EVIDENCE_DIR}/phase19-606-export.xlsx"
LOG="${PROJECT_ROOT}/logs/phase19-1-test.log"
RAW="/tmp/phase19-606-test-raw.json"
mkdir -p "$EVIDENCE_DIR" "$(dirname "$LOG")"
chmod 777 "$EVIDENCE_DIR"

ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"
hellenia_load_env "$ENV_FILE"

hellenia_log "Fase 19.1 — validación completa 606 TEST"
TMP=$(mktemp)
set +e
cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" run --rm -T \
  -v "${EVIDENCE_DIR}:/evidence" \
  -e HELLENIA_PHASE19_EVIDENCE=/evidence \
  -e HELLENIA_PHASE19_EVIDENCE_HOST="${EVIDENCE}" \
  odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/phase19-1-validate-606-full-test.py" > "$TMP" 2>&1 | tee -a "$LOG"
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR: odoo shell exit $RC"
  tail -40 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

python3 -c "
import json, sys, re, base64, os
raw = open('$TMP').read()
marker = 'PHASE19_1:'
i = raw.find(marker)
payload = raw[i + len(marker):].strip() if i >= 0 else raw.strip()
if not payload.startswith('{'):
    print(raw[-5000:], file=sys.stderr)
    sys.exit(1)
open('$RAW', 'w').write(payload)
data = json.loads(payload)
open('$EVIDENCE', 'w').write(json.dumps(data, ensure_ascii=False, indent=2))
b64 = data.get('excel_base64')
if b64 and not os.path.isfile('$EXCEL'):
    open('$EXCEL', 'wb').write(base64.b64decode(b64))
print('OK → $EVIDENCE')
"
rm -f "$TMP"

python3 -c "
import json, sys
d=json.load(open('$EVIDENCE'))
print('RESULTADO:', 'PASS' if d.get('pass') else 'FAIL', d['passed'], '/', d['total'])
print('Excel:', '$EXCEL' if __import__('os').path.isfile('$EXCEL') else d.get('excel_path_host', ''))
if not d.get('pass'):
    fails=[k for k,v in d.get('checks',{}).items() if not v.get('ok')]
    print('Fallos:', ', '.join(fails[:15]))
sys.exit(0 if d.get('pass') else 1)
"
