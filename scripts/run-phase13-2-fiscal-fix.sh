#!/usr/bin/env bash
# Fase 13.2 — Diagnóstico, corrección fiscal RD y validación (TEST → PROD)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-test}"
ACTION="${2:-diagnose}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_DIR="$(hellenia_env_dir "$ENV_NAME")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_DIR}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_DIR}"
EVIDENCE_DIR="$PROJECT_ROOT/evidence"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

extract_marker() {
  local tmp="$1" marker="$2" out="$3"
  python3 -c "
import sys
d = open('$tmp').read()
marker = '${marker}:'
i = d.find(marker)
if i < 0:
    print(d[-8000:], file=sys.stderr)
    sys.exit(1)
open('$out', 'w').write(d[i+len(marker):].strip())
print('OK → $out')
"
}

run_shell() {
  local script="$1"
  local tmp
  tmp=$(mktemp)
  set +e
  docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
    < "${SCRIPT_DIR}/${script}" > "$tmp" 2>&1
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    hellenia_log "ERROR: odoo shell exit $rc"
    tail -50 "$tmp"
    rm -f "$tmp"
    exit $rc
  fi
  echo "$tmp"
}

upgrade_modules() {
  hellenia_log "Actualizando módulos Justech en ${ENV_NAME}..."
  docker compose --env-file "$ENV_FILE" stop odoo
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -u justech_l10n_do_base,justech_l10n_do_ncf,justech_l10n_do_reports \
    --stop-after-init --no-http 2>&1 | tail -25
  docker compose --env-file "$ENV_FILE" up -d odoo
}

case "$ACTION" in
  diagnose)
    hellenia_log "Diagnóstico fiscal — ${ENV_NAME}"
    TMP=$(run_shell diagnose-fiscal-taxes.py)
    mkdir -p "$EVIDENCE_DIR"
    OUT="$EVIDENCE_DIR/phase13-2-diagnose-${ENV_NAME}.json"
    extract_marker "$TMP" "FISCAL_DIAGNOSIS" "$OUT"
    tail -8 "$TMP"
    rm -f "$TMP"
    ;;
  fix)
    hellenia_log "Corrección fiscal RD — ${ENV_NAME}"
    TMP=$(run_shell fix-fiscal-rd-configuration.py)
    OUT="$EVIDENCE_DIR/phase13-2-fix-${ENV_NAME}.json"
    extract_marker "$TMP" "FISCAL_FIX" "$OUT"
    tail -8 "$TMP"
    rm -f "$TMP"
    ;;
  validate)
    hellenia_log "Validación P13.2 — ${ENV_NAME}"
    upgrade_modules
    TMP=$(run_shell phase13-2-validate-fiscal.py)
    OUT="$EVIDENCE_DIR/phase13-2-validate-${ENV_NAME}.json"
    extract_marker "$TMP" "PHASE13_2_VALIDATION" "$OUT"
    tail -8 "$TMP"
    rm -f "$TMP"
    ;;
  upgrade)
    upgrade_modules
    ;;
  full-test)
    hellenia_log "Flujo completo TEST: diagnose → validate"
    "$0" test diagnose
    "$0" test validate
    ;;
  full-prod)
    hellenia_log "Flujo PROD: backup → fix → upgrade → validate"
    "$SCRIPT_DIR/backup-hellenia-prod.sh"
    "$0" prod fix
    "$0" prod upgrade
    "$0" prod validate
    "$0" prod diagnose
    ;;
  *)
    echo "Uso: $0 {test|prod} {diagnose|fix|validate|upgrade|full-test|full-prod}"
    exit 1
    ;;
esac

hellenia_log "Completado: ${ACTION} en ${ENV_NAME}"
