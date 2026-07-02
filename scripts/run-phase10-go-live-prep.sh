#!/usr/bin/env bash
# Fase 10 — Preparación Go-Live: backups triples + auditoría (sin activar PROD)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence"
mkdir -p "$EVIDENCE"

hellenia_log "========== FASE 10 — PREPARACIÓN GO-LIVE =========="

hellenia_log "=== 1/4 Backup DEV ==="
"${SCRIPT_DIR}/backup-dev.sh"
"${SCRIPT_DIR}/verify-backup-dev.sh" "$(ls -1dt "${PROJECT_ROOT}/backups/dev"/20* 2>/dev/null | head -1)"

hellenia_log "=== 2/4 Backup TEST ==="
"${SCRIPT_DIR}/backup-test.sh"

hellenia_log "=== 3/4 Backup producción actual (odoo-pecv) ==="
"${SCRIPT_DIR}/backup-production-current.sh"

hellenia_log "=== 4/4 Auditoría infraestructura ==="
"${SCRIPT_DIR}/audit-infrastructure-phase10.sh" "${EVIDENCE}/phase10-infra-audit.txt"

# Verificar integridad backups
verify_backup() {
  local dest="$1"
  local name="$2"
  if [[ -f "${dest}/postgres_all.sql.gz" ]] && [[ -s "${dest}/postgres_all.sql.gz" ]]; then
    hellenia_log "OK backup $name: $(basename "$dest")"
    return 0
  fi
  hellenia_log "WARN backup $name incompleto: $dest"
  return 1
}

DEV_B=$(ls -1dt "${PROJECT_ROOT}/backups/dev"/20* 2>/dev/null | head -1)
TEST_B=$(ls -1dt "${PROJECT_ROOT}/backups/test"/20* 2>/dev/null | head -1)
PROD_B=$(ls -1dt "${PROJECT_ROOT}/backups/production"/20* 2>/dev/null | head -1)

verify_backup "$DEV_B" DEV
verify_backup "$TEST_B" TEST
verify_backup "$PROD_B" PRODUCTION

cat > "${EVIDENCE}/phase10-backups-manifest.json" <<EOF
{
  "phase": 10,
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "backups": {
    "dev": "$(basename "$DEV_B")",
    "test": "$(basename "$TEST_B")",
    "production_odoo_pecv": "$(basename "$PROD_B")"
  },
  "verified": true
}
EOF

hellenia_log "========== FASE 10 backups + audit completados =========="
