#!/usr/bin/env bash
# Fase 19.1 — validación real exportador 606 en TEST (VPS)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="${PROJECT_ROOT}/evidence/phase19-606-test.json"
EXCEL="${PROJECT_ROOT}/evidence/phase19-606-export.xlsx"
LOG="${PROJECT_ROOT}/logs/phase19-1-test.log"
mkdir -p "$(dirname "$EVIDENCE")" "$(dirname "$LOG")"

hellenia_log "Fase 19.1 — validación completa 606 TEST"
"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase19-1-validate-606-full-test.py PHASE19_1 "$EVIDENCE" 2>&1 | tee -a "$LOG"

python3 -c "
import json, sys
d=json.load(open('$EVIDENCE'))
print('RESULTADO:', 'PASS' if d.get('pass') else 'FAIL', d['passed'], '/', d['total'])
print('Excel:', d.get('excel_path', '$EXCEL'))
if not d.get('pass'):
    fails=[k for k,v in d.get('checks',{}).items() if not v.get('ok')]
    print('Fallos:', ', '.join(fails[:15]))
sys.exit(0 if d.get('pass') else 1)
"
