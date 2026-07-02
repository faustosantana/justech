#!/usr/bin/env bash
# Validación de rollback en TEST (no toca PROD)
#
# Modos:
#   ./validate-rollback-test.sh           # dry-run: verifica artefactos y scripts
#   FULL_SIMULATION=1 ./validate-rollback-test.sh  # simulación completa en TEST
#
# Documenta tiempos de recuperación en evidence/rollback-certification-*.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
if [[ ! -f "$ENV_FILE" && -f "$PROJECT_ROOT/config/test/.env.example" ]]; then
  ENV_FILE="$PROJECT_ROOT/config/test/.env.example"
  log_early() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
  log_early "WARN: config/test/.env ausente — usando .env.example (dry-run local)"
fi
TS=$(date +%Y-%m-%d_%H%M)
REPORT="$PROJECT_ROOT/evidence/rollback-certification-test-${TS}.json"
LOG_FILE="$PROJECT_ROOT/logs/deploy/rollback-validation-test-${TS}.log"
FULL="${FULL_SIMULATION:-0}"

mkdir -p "$(dirname "$REPORT")" "$(dirname "$LOG_FILE")"
hellenia_load_env "$ENV_FILE"

PROJECT="${COMPOSE_PROJECT_NAME:-hellenia-test}"
ODOO_CONTAINER="$(hellenia_container "$PROJECT" odoo)"
DB_CONTAINER="$(hellenia_container "$PROJECT" db)"

log() { hellenia_log "$*" | tee -a "$LOG_FILE"; }

START_TOTAL=$(date +%s)
TIMINGS=()

time_step() {
  local label="$1"
  local start="$2"
  local end
  end=$(date +%s)
  local elapsed=$((end - start))
  TIMINGS+=("\"${label}\": ${elapsed}")
  log "TIMING ${label}: ${elapsed}s"
}

log "=== Validación rollback TEST (FULL_SIMULATION=${FULL}) ==="

# --- 1. Verificar scripts existen ---
for script in backup-test.sh restore-test.sh healthcheck-full.sh; do
  [[ -x "${SCRIPT_DIR}/${script}" ]] || chmod +x "${SCRIPT_DIR}/${script}"
  [[ -f "${SCRIPT_DIR}/${script}" ]] || { log "FAIL: falta $script"; exit 1; }
  log "OK  script: $script"
done

# --- 2. Backup TEST (si ambiente desplegado) ---
T0=$(date +%s)
if hellenia_container_running "$DB_CONTAINER"; then
  log "Creando backup TEST..."
  "$SCRIPT_DIR/backup-test.sh" 2>&1 | tee -a "$LOG_FILE"
  BACKUP_DIR=$(ls -1dt "${BACKUP_ROOT:-/opt/odoo-projects/hellenia/backups/test}"/20* 2>/dev/null | grep -vE '_weekly$|_monthly$' | head -1)
  [[ -d "$BACKUP_DIR" ]] || { log "FAIL: sin backup"; exit 1; }
  time_step "backup_test" "$T0"

  # --- 3. Verificar integridad artefactos ---
  T0=$(date +%s)
  for artifact in postgres_all.sql.gz filestore.tar.gz custom.tar.gz docker-compose.yml odoo.conf .env; do
    [[ -f "${BACKUP_DIR}/${artifact}" ]] || { log "FAIL: falta ${artifact}"; exit 1; }
    log "OK  artifact: $artifact"
  done
  gunzip -t "${BACKUP_DIR}/postgres_all.sql.gz"
  tar tzf "${BACKUP_DIR}/filestore.tar.gz" >/dev/null
  tar tzf "${BACKUP_DIR}/custom.tar.gz" >/dev/null
  time_step "verify_artifacts" "$T0"

  # --- 4. Simulación docker rollback ---
  T0=$(date +%s)
  if [[ -f "${BACKUP_DIR}/docker-compose.yml" ]]; then
    log "OK  docker-compose en backup disponible para rollback"
    diff -q "${BACKUP_DIR}/docker-compose.yml" "$PROJECT_ROOT/docker/test/docker-compose.yml" \
      && log "INFO: compose actual = backup (sin diff)" \
      || log "INFO: compose difiere — rollback docker posible desde backup"
  fi
  time_step "docker_rollback_check" "$T0"
else
  log "SKIP backup/artifacts: TEST no desplegado en este host (validación de scripts únicamente)"
  bash -n "${SCRIPT_DIR}/backup-test.sh"
  bash -n "${SCRIPT_DIR}/restore-test.sh"
  BACKUP_DIR=""
  time_step "backup_test" "$T0"
fi

if [[ "$FULL" != "1" ]]; then
  log "DRY-RUN completado (sin restore destructivo)"
  RESULT="PASS_DRY_RUN"
else
  # --- 5. Simulación restore completa ---
  if ! hellenia_container_running "$DB_CONTAINER"; then
    log "SKIP FULL_SIMULATION: TEST no desplegado en este host"
    RESULT="PASS_DRY_RUN"
  else
    T0=$(date +%s)
    log "FULL_SIMULATION: restore desde $BACKUP_DIR"
    "$SCRIPT_DIR/restore-test.sh" "$BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE"
    time_step "restore_test" "$T0"

    T0=$(date +%s)
    if "$SCRIPT_DIR/healthcheck-full.sh" test 2>&1 | tee -a "$LOG_FILE"; then
      log "OK  healthcheck post-rollback"
      RESULT="PASS"
    else
      log "FAIL healthcheck post-rollback"
      RESULT="FAIL"
    fi
    time_step "healthcheck_post_rollback" "$T0"
  fi
fi

END_TOTAL=$(date +%s)
TOTAL_ELAPSED=$((END_TOTAL - START_TOTAL))
TIMINGS+=("\"total\": ${TOTAL_ELAPSED}")

cat > "$REPORT" << EOF
{
  "phase": "13.8",
  "environment": "test",
  "mode": "$([ "$FULL" = "1" ] && echo full_simulation || echo dry_run)",
  "result": "${RESULT:-PASS_DRY_RUN}",
  "backup_dir": "${BACKUP_DIR}",
  "timings_seconds": {$(IFS=,; echo "${TIMINGS[*]}")},
  "rto_estimate_minutes": $(echo "scale=1; $TOTAL_ELAPSED / 60" | bc 2>/dev/null || echo "n/a")
}
EOF

log "=== RESULTADO: ${RESULT:-PASS_DRY_RUN} ==="
log "Reporte: $REPORT"
log "RTO estimado (esta corrida): ${TOTAL_ELAPSED}s"

[[ "${RESULT:-PASS_DRY_RUN}" != "FAIL" ]]
