#!/usr/bin/env bash
# Fase 14 — Estabilización final TEST (sin tocar PROD)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
COMMIT="${1:-$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo hellenia-odoo-infra)}"
LOG="$PROJECT_ROOT/logs/deploy/phase14-$(date +%Y-%m-%d_%H%M).log"
EVIDENCE="$PROJECT_ROOT/evidence/phase14-final-acceptance.json"

mkdir -p "$(dirname "$LOG")" "$(dirname "$EVIDENCE")"

hellenia_log "=== Fase 14 — Estabilización TEST ===" | tee "$LOG"

if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  git fetch origin 2>/dev/null || true
  git checkout "$COMMIT" 2>/dev/null || git checkout "origin/$COMMIT"
  hellenia_sync_from_repo "$REPO" "$PROJECT_ROOT"
  hellenia_log "Commit: $(git rev-parse --short HEAD)" | tee -a "$LOG"
fi

"$SCRIPT_DIR/deploy-test.sh" "$COMMIT" 2>&1 | tee -a "$LOG"

# Instalar módulos UI si hace falta
ENV_FILE="$PROJECT_ROOT/config/test/.env"
hellenia_load_env "$ENV_FILE"
cd "$PROJECT_ROOT/docker/test"

for mod in hellenia_ui hellenia_reports hellenia_base; do
  docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -i "$mod" --stop-after-init 2>&1 | tail -5 | tee -a "$LOG" || true
done

docker compose --env-file "$ENV_FILE" up -d odoo

"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase14-finalize-test.py PHASE14 "$EVIDENCE" 2>&1 | tee -a "$LOG"

if ! python3 -c "import json; d=json.load(open('$EVIDENCE')); exit(0 if d.get('ok') else 1)"; then
  hellenia_log "FAIL validación Fase 14" | tee -a "$LOG"
  exit 1
fi

"$SCRIPT_DIR/healthcheck-full.sh" test 2>&1 | tee -a "$LOG"

hellenia_log "PASS Fase 14 TEST — evidencia: $EVIDENCE" | tee -a "$LOG"
