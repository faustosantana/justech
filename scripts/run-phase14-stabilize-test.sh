#!/usr/bin/env bash
# Fase 14 — Estabilización final TEST (sin tocar PROD ni redeploy compose)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
COMMIT="${1:-c91a2b2}"
LOG="$PROJECT_ROOT/logs/deploy/phase14-$(date +%Y-%m-%d_%H%M).log"
EVIDENCE="$PROJECT_ROOT/evidence/phase14-final-acceptance.json"

mkdir -p "$(dirname "$LOG")" "$(dirname "$EVIDENCE")"

hellenia_log "=== Fase 14 — Estabilización TEST ===" | tee "$LOG"

if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  git fetch origin 2>/dev/null || true
  git checkout "$COMMIT" 2>/dev/null || git checkout "origin/$COMMIT"
  rsync -av "${REPO}/custom/" "${PROJECT_ROOT}/custom/"
  rsync -av "${REPO}/scripts/" "${PROJECT_ROOT}/scripts/"
  chmod +x "${PROJECT_ROOT}/scripts/"*.sh
  hellenia_log "Commit: $(git rev-parse --short HEAD)" | tee -a "$LOG"
fi

ENV_FILE="$PROJECT_ROOT/config/test/.env"
hellenia_load_env "$ENV_FILE"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"
cd "$COMPOSE_DIR"

install_mod() {
  local mod="$1"
  hellenia_log "Instalando/actualizando módulo $mod..." | tee -a "$LOG"
  docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -i "$mod" --stop-after-init --no-http 2>&1 | tail -8 | tee -a "$LOG" || true
}

for mod in hellenia_base hellenia_ui hellenia_reports; do
  install_mod "$mod"
done

docker compose --env-file "$ENV_FILE" up -d odoo
sleep 15

"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase14-finalize-test.py PHASE14 "$EVIDENCE" 2>&1 | tee -a "$LOG"

if ! python3 -c "import json; d=json.load(open('$EVIDENCE')); exit(0 if d.get('ok') else 1)"; then
  hellenia_log "FAIL validación Fase 14" | tee -a "$LOG"
  exit 1
fi

if [[ -x "$SCRIPT_DIR/healthcheck-full.sh" ]]; then
  "$SCRIPT_DIR/healthcheck-full.sh" test 2>&1 | tee -a "$LOG" || true
fi

hellenia_log "PASS Fase 14 TEST — evidencia: $EVIDENCE" | tee -a "$LOG"
