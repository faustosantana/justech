#!/usr/bin/env bash
# Fase 8 — Flujo completo: backup → apply → audit → validate
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-dev}"
if [[ "$ENV_NAME" != "dev" ]]; then
  hellenia_log "ERROR: Fase 8 solo opera en DEV"
  exit 1
fi

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

hellenia_log "=== Fase 8: backup DEV ==="
"${SCRIPT_DIR}/backup-dev.sh"

hellenia_log "=== Fase 8: validar estado pre-apply ==="
"${SCRIPT_DIR}/validate-phase6-mvp.sh" dev || hellenia_log "WARN: validate-phase6-mvp"

hellenia_log "=== Fase 8: aplicar parametrización ==="
"${SCRIPT_DIR}/apply-phase8-parameterization.sh" dev

hellenia_log "=== Fase 8: auditoría post-apply ==="
"${SCRIPT_DIR}/audit-phase8-functional.sh" dev

hellenia_log "=== Fase 8: validaciones existentes ==="
"${SCRIPT_DIR}/validate-phase35-golden-config.sh" dev 2>/dev/null || true
"${SCRIPT_DIR}/validate-phase6-mvp.sh" dev

hellenia_log "=== Fase 8 flujo completado ==="
