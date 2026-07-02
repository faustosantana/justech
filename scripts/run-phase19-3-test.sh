#!/usr/bin/env bash
# Fase 19.3 — validación bandeja revisión fiscal DGII en TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"
LOG="${PROJECT_ROOT}/logs/phase19-3-test.log"
mkdir -p "$EVIDENCE_DIR" "$(dirname "$LOG")"
chmod 777 "$EVIDENCE_DIR"

ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"
hellenia_load_env "$ENV_FILE"

hellenia_log "Fase 19.3 — upgrade módulos"
bash "$SCRIPT_DIR/update-custom-modules.sh" test \
  justech_l10n_do_base justech_l10n_do_ncf hellenia_account justech_l10n_do_reports \
  2>&1 | tee -a "$LOG"

TMP=$(mktemp)
cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" run --rm -T \
  -v "${EVIDENCE_DIR}:/evidence" \
  -e HELLENIA_PHASE19_EVIDENCE=/evidence \
  odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/phase19-3-validate-review-test.py" > "$TMP" 2>&1 | tee -a "$LOG"

python3 -c "
import json, sys
raw = open('$TMP').read()
marker = 'PHASE19_3:'
i = raw.find(marker)
payload = raw[i + len(marker):].strip() if i >= 0 else ''
if not payload.startswith('{'):
    print(raw[-8000:], file=sys.stderr)
    sys.exit(1)
open('$EVIDENCE_DIR/phase19-3-review-test.json', 'w').write(json.dumps(json.loads(payload), indent=2, ensure_ascii=False))
d = json.loads(payload)
print('RESULTADO:', 'PASS' if d.get('pass') else 'FAIL', d['passed'], '/', d['total'])
sys.exit(0 if d.get('pass') else 1)
"
rm -f "$TMP"
