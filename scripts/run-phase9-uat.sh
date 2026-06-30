#!/usr/bin/env bash
# Fase 9 — UAT Funcional Integral (solo TEST)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence"

hellenia_log "========== FASE 9 UAT — SOLO TEST =========="

# 1. Backup TEST
hellenia_log "=== 1/10 Backup TEST ==="
"${SCRIPT_DIR}/backup-test.sh"

# 2. Validaciones pre-UAT
hellenia_log "=== 2/10 PHASE6_MVP TEST ==="
"${SCRIPT_DIR}/validate-phase6-mvp.sh" test | tee "${EVIDENCE_DIR}/uat-pre-phase6-test.log" | tail -5

hellenia_log "=== 3/10 Parametrización Fase 8 en TEST ==="
"${SCRIPT_DIR}/apply-phase8-parameterization.sh" test

hellenia_log "=== 4/10 Auditoría parametrización TEST ==="
"${SCRIPT_DIR}/audit-phase8-functional.sh" test

# 5. Bloque 1 — Datos maestros
hellenia_log "=== 5/10 Bloque 1 — Datos maestros UAT ==="
"${SCRIPT_DIR}/uat-run-on-test.sh" uat-setup-master-data.py "${EVIDENCE_DIR}/uat-block1-master-data.json"

# 6. Bloques 2-8 — Funcional
hellenia_log "=== 6/10 Bloques 2-8 — Ciclos funcionales ==="
"${SCRIPT_DIR}/uat-run-on-test.sh" uat-execute-functional.py "${EVIDENCE_DIR}/uat-functional.json"

# 7. Bloque 10 — Estrés
hellenia_log "=== 7/10 Bloque 10 — Estrés ==="
"${SCRIPT_DIR}/uat-run-on-test.sh" uat-stress-tests.py "${EVIDENCE_DIR}/uat-stress.json"

# 8. Bloques 9, 11, 12
hellenia_log "=== 8/10 Bloques 9, 11, 12 — Reportes y auditoría ==="
"${SCRIPT_DIR}/uat-run-on-test.sh" uat-audit-reports.py "${EVIDENCE_DIR}/uat-audit.json"

# 9. Concurrencia NCF (script existente)
hellenia_log "=== 9/10 Concurrencia NCF ==="
if [[ -x "${SCRIPT_DIR}/test-ncf-concurrency.sh" ]]; then
  "${SCRIPT_DIR}/test-ncf-concurrency.sh" test 2>&1 | tee "${EVIDENCE_DIR}/uat-concurrency.log" | tail -3 || hellenia_log "WARN: concurrencia"
fi

# 10. Validación final MVP
hellenia_log "=== 10/10 PHASE6_MVP post-UAT ==="
"${SCRIPT_DIR}/validate-phase6-mvp.sh" test | tee "${EVIDENCE_DIR}/uat-post-phase6-test.log" | tail -5

hellenia_log "========== FASE 9 UAT COMPLETADA =========="
hellenia_log "Evidencia en ${EVIDENCE_DIR}/uat-*.json"
