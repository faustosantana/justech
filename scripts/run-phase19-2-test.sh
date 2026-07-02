#!/usr/bin/env bash
# Fase 19.2 — limpieza UAT/demo + certificación 606 período completo TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"
LOG="${PROJECT_ROOT}/logs/phase19-2-test.log"
mkdir -p "$EVIDENCE_DIR" "$(dirname "$LOG")"
chmod 777 "$EVIDENCE_DIR"

ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"
hellenia_load_env "$ENV_FILE"

hellenia_log "Fase 19.2 — upgrade módulos"
bash "$SCRIPT_DIR/update-custom-modules.sh" test \
  justech_l10n_do_base justech_l10n_do_ncf hellenia_account justech_l10n_do_reports \
  2>&1 | tee -a "$LOG"

run_shell() {
  local py_script="$1"
  local marker="$2"
  local out_json="$3"
  local tmp
  tmp=$(mktemp)
  cd "$COMPOSE_DIR"
  docker compose --env-file "$ENV_FILE" run --rm -T \
    -v "${EVIDENCE_DIR}:/evidence" \
    -e HELLENIA_PHASE19_EVIDENCE=/evidence \
    odoo odoo shell \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
    < "${SCRIPT_DIR}/${py_script}" > "$tmp" 2>&1 | tee -a "$LOG"
  python3 -c "
import json, sys
raw = open('$tmp').read()
marker = '${marker}:'
i = raw.find(marker)
payload = raw[i + len(marker):].strip() if i >= 0 else ''
if not payload.startswith('{'):
    print(raw[-8000:], file=sys.stderr)
    sys.exit(1)
open('$out_json', 'w').write(json.dumps(json.loads(payload), ensure_ascii=False, indent=2))
print('OK → $out_json')
"
  rm -f "$tmp"
}

hellenia_log "Fase 19.2 — exclusión fiscal UAT/demo"
run_shell phase19-2-exclude-uat-demo-test.py PHASE19_2_CLEANUP \
  "$EVIDENCE_DIR/phase19-2-cleanup.json"

hellenia_log "Fase 19.2 — certificación período completo"
run_shell phase19-2-validate-606-certification.py PHASE19_2 \
  "$EVIDENCE_DIR/phase19-2-certification.json"

python3 -c "
import json, sys
cleanup = json.load(open('$EVIDENCE_DIR/phase19-2-cleanup.json'))
cert = json.load(open('$EVIDENCE_DIR/phase19-2-certification.json'))
print('CLEANUP excluidas:', cleanup.get('excluded_count'))
print('CERTIFICACIÓN:', 'PASS' if cert.get('pass') else 'FAIL', cert['passed'], '/', cert['total'])
print('Válidas 606:', cert.get('counts', {}).get('valid'))
print('Excluidas:', cert.get('counts', {}).get('excluded'))
if not cert.get('pass'):
    fails = [k for k, v in cert.get('checks', {}).items() if not v.get('ok')]
    print('Fallos:', ', '.join(fails))
sys.exit(0 if cert.get('pass') else 1)
"
