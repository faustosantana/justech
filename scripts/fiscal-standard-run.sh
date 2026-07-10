#!/usr/bin/env bash
# Validación estándar fiscal Justech — empresa por empresa (erp.justech.do).
# Uso: bash fiscal-standard-run.sh [plugsafe|omni|justoffice|justech|all]
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
SCRIPT_DIR="${SCRIPT_DIR:-/opt/odoo-dev/scripts}"
EVIDENCE="${EVIDENCE:-/opt/odoo-dev/evidence/fiscal-standard}"
BASE_URL="${BASE_URL:-https://erp.justech.do}"
TARGET="${1:-plugsafe}"

declare -A COMPANY_MAP=(
  [plugsafe]=2
  [omni]=4
  [justoffice]=3
  [justech]=1
)

ORDER=(plugsafe omni justoffice justech)
TS="$(date +%Y%m%d_%H%M%S)"

log() { echo "[$(date -Iseconds)] $*"; }
fail() { log "ABORT $*"; exit 1; }

run_shell() {
  local script="$1" out="$2"
  shift 2
  sudo -u odoo env "$@" /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$out"
exec(open("${script}").read())
PY
}

run_company() {
  local SLUG="$1"
  local CID="${COMPANY_MAP[$SLUG]}"
  [[ -n "$CID" ]] || fail "unknown company $SLUG"

  log "========== VALIDACIÓN ESTÁNDAR: $SLUG (id=$CID) =========="

  log "--- Backup ---"
  bash "$SCRIPT_DIR/fiscal-integration-dev1-backup.sh" "${TS}_${SLUG}" "fiscal-standard-${SLUG}" \
    | tee "$EVIDENCE/backup_${SLUG}_${TS}.log"
  local BACKUP
  BACKUP=$(grep -o '/opt/odoo-dev/backups/fiscal-integration-fiscal-standard-[^ ]*' "$EVIDENCE/backup_${SLUG}_${TS}.log" | tail -1)
  [[ -n "$BACKUP" ]] || fail "backup path not found for $SLUG"

  log "--- Pre-snapshot ---"
  run_shell "$SCRIPT_DIR/fiscal-standard-snapshot.py" "$EVIDENCE/pre_${SLUG}_${TS}.json" \
    FISCAL_STD_COMPANY_ID="$CID" FISCAL_STD_SNAPSHOT_LABEL="pre_${SLUG}"

  log "--- Healthcheck login/assets ---"
  local CODE ASSET ACODE
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/web/login")
  [[ "$CODE" == "200" ]] || fail "login not 200: $CODE"
  ASSET=$(sudo -u odoo psql -d "$DB" -t -A -c "SELECT url FROM ir_attachment WHERE url LIKE '/web/assets/%' ORDER BY write_date DESC LIMIT 1;")
  ACODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL${ASSET}")
  [[ "$ACODE" == "200" ]] || fail "asset not 200: $ASSET"
  log "Health OK login=$CODE asset=$ACODE"

  log "--- Activate/ensure ranges ---"
  if ! run_shell "$SCRIPT_DIR/fiscal-standard-activate.py" "$EVIDENCE/activate_${SLUG}_${TS}.json" \
      FISCAL_STD_COMPANY_ID="$CID"; then
    log "ACTIVATE FAILED — RESTORE $BACKUP"
    bash "$SCRIPT_DIR/ncf-pilot-rollback.sh" "$BACKUP"
    fail "activate failed $SLUG"
  fi

  log "--- Validate full standard ---"
  if ! run_shell "$SCRIPT_DIR/fiscal-standard-validate.py" "$EVIDENCE/validate_${SLUG}_${TS}.json" \
      FISCAL_STD_COMPANY_ID="$CID" FISCAL_STD_PRE_SNAPSHOT="$EVIDENCE/pre_${SLUG}_${TS}.json"; then
    log "VALIDATE FAILED — RESTORE $BACKUP"
    bash "$SCRIPT_DIR/ncf-pilot-rollback.sh" "$BACKUP"
    fail "validate failed $SLUG"
  fi

  log "--- Post-snapshot ---"
  run_shell "$SCRIPT_DIR/fiscal-standard-snapshot.py" "$EVIDENCE/post_${SLUG}_${TS}.json" \
    FISCAL_STD_COMPANY_ID="$CID" FISCAL_STD_SNAPSHOT_LABEL="post_${SLUG}"

  python3 "$SCRIPT_DIR/fiscal-standard-report.py" \
    "$EVIDENCE/pre_${SLUG}_${TS}.json" \
    "$EVIDENCE/validate_${SLUG}_${TS}.json" \
    "$EVIDENCE/post_${SLUG}_${TS}.json" \
    > "$EVIDENCE/REPORT_${SLUG}_${TS}.md"

  log "=== APROBADO: $SLUG ==="
  log "Report: $EVIDENCE/REPORT_${SLUG}_${TS}.md"
}

mkdir -p "$EVIDENCE"
log "=== VALIDACIÓN ESTÁNDAR FISCAL JUSTECH — erp.justech.do ==="

if [[ "$TARGET" == "all" ]]; then
  for SLUG in "${ORDER[@]}"; do
    run_company "$SLUG"
  done
  log "=== VALIDACIÓN COMPLETA 4/4 ==="
else
  run_company "$TARGET"
fi
