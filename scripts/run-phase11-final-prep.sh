#!/usr/bin/env bash
# Fase 11 — Preparación operativa final pre Go-Live (sin ejecutar corte)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

hellenia_log "========== FASE 11 — PREPARACIÓN OPERATIVA FINAL =========="
hellenia_log "Reglas: NO Go-Live, NO PROD, NO DNS, NO datos reales"

hellenia_log "=== 1/2 Auditoría integral repositorio ==="
"${SCRIPT_DIR}/audit-phase11-final-review.sh"

hellenia_log "=== 2/2 Validación documentación Fase 11 ==="
REQUIRED_DOCS=(
  FINAL_PROJECT_AUDIT.md
  FINAL_CODE_REVIEW.md
  FINAL_FUNCTIONAL_REVIEW.md
  FINAL_ACCOUNTING_REVIEW.md
  FINAL_FISCAL_REVIEW.md
  FINAL_SECURITY_REVIEW.md
  FINAL_PRODUCT_REVIEW.md
  FINAL_TECHNICAL_DEBT.md
  PRODUCT_ROADMAP.md
  GO_LIVE_FINAL_CERTIFICATION.md
)
MISSING=0
for doc in "${REQUIRED_DOCS[@]}"; do
  if [[ -f "${PROJECT_ROOT}/docs/${doc}" ]]; then
    hellenia_log "OK docs/${doc}"
  else
    hellenia_log "MISSING docs/${doc}"
    MISSING=$((MISSING + 1))
  fi
done

if [[ "$MISSING" -gt 0 ]]; then
  hellenia_log "WARN: ${MISSING} documentos Fase 11 pendientes"
  exit 1
fi

hellenia_log "Fase 11 preparación documental: COMPLETA"
hellenia_log "Go-Live: NO EJECUTADO — esperar aprobación explícita"
