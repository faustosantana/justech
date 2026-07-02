#!/usr/bin/env bash
# Fase 15 — Auditoría + corrección + validación completa en TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
AUDIT_EVIDENCE="$PROJECT_ROOT/evidence/phase15-menu-audit-test.json"
VALIDATE_EVIDENCE="$PROJECT_ROOT/evidence/phase15-validate-test.json"
REGRESSION_EVIDENCE="$PROJECT_ROOT/evidence/phase15-regression-test.json"
LOG="$PROJECT_ROOT/logs/deploy/phase15-test-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$AUDIT_EVIDENCE")" "$(dirname "$LOG")"

if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  git pull origin "$(git branch --show-current)" 2>/dev/null || true
  rsync -av "${REPO}/custom/" "${PROJECT_ROOT}/custom/"
  rsync -av "${REPO}/scripts/" "${PROJECT_ROOT}/scripts/"
  chmod +x "${PROJECT_ROOT}/scripts/"*.sh
fi

hellenia_load_env "$ENV_FILE"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"

hellenia_log "=== Fase 15 — TEST (auditoría + fix + validación) ===" | tee "$LOG"

cd "$COMPOSE_DIR"
for mod in hellenia_ui justech_l10n_do_base justech_l10n_do_ncf justech_l10n_do_reports; do
  hellenia_log "Upgrade $mod..." | tee -a "$LOG"
  docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
    -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
    -u "$mod" --stop-after-init --no-http 2>&1 | tail -5 | tee -a "$LOG"
done

docker compose --env-file "$ENV_FILE" up -d odoo
sleep 15

hellenia_log "Auditoría pre-fix..." | tee -a "$LOG"
"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase15-audit-menus.py PHASE15_AUDIT "$AUDIT_EVIDENCE" 2>&1 | tee -a "$LOG" || true

hellenia_log "Corrección + validación..." | tee -a "$LOG"
"$SCRIPT_DIR/run-odoo-shell-env.sh" test phase15-validate-test.py PHASE15_VALIDATE "$VALIDATE_EVIDENCE" 2>&1 | tee -a "$LOG"

python3 -c "import json; d=json.load(open('$VALIDATE_EVIDENCE')); exit(0 if d.get('ok') else 1)"

hellenia_log "Regresión PHASE6 MVP..." | tee -a "$LOG"
PHASE6_TMP=$(mktemp)
set +e
"$SCRIPT_DIR/run-odoo-shell-env.sh" test validate-phase6-mvp.py IGNORE /dev/null 2>&1 | tee "$PHASE6_TMP" | tee -a "$LOG"
PHASE6_RC=$?
set -e
python3 - <<PY
import json, re, pathlib
text = pathlib.Path("$PHASE6_TMP").read_text()
m = re.search(r'\{[\s\S]*\}\s*$', text)
ok = False
if m:
    d = json.loads(m.group())
    ok = d.get("ok", False)
    pathlib.Path("$PROJECT_ROOT/evidence/phase15-phase6-regression.json").write_text(json.dumps(d, indent=2, default=str))
print("phase6 ok:", ok)
exit(0 if ok else 1)
PY

hellenia_log "Regresión UAT funcional..." | tee -a "$LOG"
"$SCRIPT_DIR/run-odoo-shell-env.sh" test uat-execute-functional.py UAT_FUNCTIONAL \
  "$PROJECT_ROOT/evidence/phase15-uat-regression.json" 2>&1 | tee -a "$LOG"

hellenia_log "Healthcheck TEST..." | tee -a "$LOG"
"$SCRIPT_DIR/healthcheck-full.sh" test 2>&1 | tee -a "$LOG"

# Consolidar regresión
python3 - <<PY
import json, pathlib
root = pathlib.Path("$PROJECT_ROOT/evidence")
out = {"phase": "15", "regression": {}, "ok": True}
for name, path in [
    ("phase6", root / "phase15-phase6-regression.json"),
    ("uat", root / "phase15-uat-regression.json"),
    ("validate", root / "phase15-validate-test.json"),
]:
    if path.exists():
        d = json.loads(path.read_text())
        out["regression"][name] = {"ok": d.get("ok", False)}
        if not d.get("ok"):
            out["ok"] = False
root.joinpath("phase15-regression-test.json").write_text(json.dumps(out, indent=2))
print("Regression ok:", out["ok"])
PY

python3 -c "import json; d=json.load(open('$REGRESSION_EVIDENCE')); exit(0 if d.get('ok') else 1)"

hellenia_log "PASS Fase 15 TEST — $VALIDATE_EVIDENCE" | tee -a "$LOG"
