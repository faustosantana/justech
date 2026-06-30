#!/usr/bin/env bash
# Fase 19 — validación campos P0 + exportador 606 en TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

EVIDENCE="${SCRIPT_DIR}/../evidence/phase19-606-test.json"
LOG="${SCRIPT_DIR}/../logs/phase19-test.log"
mkdir -p "$(dirname "$EVIDENCE")" "$(dirname "$LOG")"

hellenia_log "Fase 19 — validación 606 TEST"
"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase19-validate-606-test.py PHASE19 "$EVIDENCE" 2>&1 | tee -a "$LOG"
python3 -c "
import json, sys
d=json.load(open('$EVIDENCE'))
print('PASS', d['passed'], '/', d['total'])
sys.exit(0 if d.get('pass') else 1)
"
