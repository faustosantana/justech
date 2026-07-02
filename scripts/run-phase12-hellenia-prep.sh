#!/usr/bin/env bash
# Fase 12 — Preparación final Hellenia para producción (sin Go-Live)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence"
PRE_UAT_TEST_BACKUP="${PHASE12_TEST_RESTORE_BACKUP:-2026-06-30_1415}"
mkdir -p "$EVIDENCE"

hellenia_log "========== FASE 12 — PREPARACIÓN HELLENIA PRODUCCIÓN =========="
hellenia_log "NO Go-Live | NO prod | NO DNS | NO licencia prod"

hellenia_log "=== 1/7 Backups triples ==="
"${SCRIPT_DIR}/backup-dev.sh"
"${SCRIPT_DIR}/verify-backup-dev.sh" "$(ls -1dt "${PROJECT_ROOT}/backups/dev"/20* 2>/dev/null | head -1)"
"${SCRIPT_DIR}/backup-test.sh"
"${SCRIPT_DIR}/backup-production-current.sh" || hellenia_log "WARN: backup odoo-pecv falló — revisar logs"

DEV_B=$(ls -1dt "${PROJECT_ROOT}/backups/dev"/20* 2>/dev/null | head -1)
TEST_B=$(ls -1dt "${PROJECT_ROOT}/backups/test"/20* 2>/dev/null | head -1)
PROD_B=$(ls -1dt "${PROJECT_ROOT}/backups/production"/20* 2>/dev/null | head -1)

cat > "${EVIDENCE}/phase12-backups-manifest.json" <<EOF
{
  "phase": 12,
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "paths": {
    "dev": "${DEV_B}",
    "test": "${TEST_B}",
    "production_odoo_pecv": "${PROD_B}"
  }
}
EOF
hellenia_log "Backups: DEV=$(basename "$DEV_B") TEST=$(basename "$TEST_B") PROD=$(basename "$PROD_B")"

hellenia_log "=== 2/7 Restaurar TEST pre-UAT (base limpia) ==="
if [[ -d "${PROJECT_ROOT}/backups/test/${PRE_UAT_TEST_BACKUP}" ]]; then
  hellenia_log "Restaurando TEST desde ${PROJECT_ROOT}/backups/test/${PRE_UAT_TEST_BACKUP}"
  "${SCRIPT_DIR}/restore-test.sh" "${PROJECT_ROOT}/backups/test/${PRE_UAT_TEST_BACKUP}" || hellenia_log "WARN: restore TEST falló — continuar con limpieza"
else
  hellenia_log "WARN: backup pre-UAT no encontrado — solo limpieza"
fi

hellenia_log "=== 3/7 Español + módulos (TEST) ==="
"${SCRIPT_DIR}/run-phase11-spanish-config.sh" test || true

hellenia_log "=== 4/7 Limpieza datos prueba TEST + DEV ==="
chmod +x "${SCRIPT_DIR}/run-odoo-shell-env.sh"
"${SCRIPT_DIR}/run-odoo-shell-env.sh" test phase12-cleanup-hellenia.py PHASE12_CLEANUP \
  "${EVIDENCE}/phase12-cleanup-test.json" || hellenia_log "WARN: cleanup TEST con observaciones"
"${SCRIPT_DIR}/run-odoo-shell-env.sh" dev phase12-cleanup-hellenia.py PHASE12_CLEANUP \
  "${EVIDENCE}/phase12-cleanup-dev.json" || hellenia_log "WARN: cleanup DEV con observaciones"

hellenia_log "=== 5/7 Validar configuración TEST + DEV ==="
"${SCRIPT_DIR}/run-odoo-shell-env.sh" test phase12-validate-configuration.py PHASE12_CONFIG \
  "${EVIDENCE}/phase12-config-test.json"
"${SCRIPT_DIR}/run-odoo-shell-env.sh" dev phase12-validate-configuration.py PHASE12_CONFIG \
  "${EVIDENCE}/phase12-config-dev.json"

hellenia_log "=== 6/7 Validar MVP Justech post-limpieza ==="
"${SCRIPT_DIR}/validate-phase6-mvp.sh" test || true

hellenia_log "=== 7/7 Completado — ver docs/PRODUCTION_STATUS.md ==="
hellenia_log "Go-Live NO ejecutado"
