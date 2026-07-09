#!/usr/bin/env bash
# Fase 3A Sprint 1 — despliegue y validación SOLO en lab aislado (justech_ncf_lab).
# NO toca justech_dev operativo ni Producción.
set -euo pipefail

CONF="${CONF:-/opt/odoo-dev/conf/odoo-ncf-lab.conf}"
DB="${DB:-justech_ncf_lab}"
LAB_ADDONS="${LAB_ADDONS:-/opt/odoo-dev/custom-addons/ncf-lab}"
EVIDENCE="${EVIDENCE:-/opt/odoo-dev/evidence/fiscal-phase3}"
REPO_LOCAL="${REPO_LOCAL:-}"

log() { echo "[$(date -Iseconds)] $*"; }

if [[ "$(id -un)" != "odoo" && "$(id -un)" != "root" ]]; then
  echo "Ejecutar como root u odoo en jaios-vps" >&2
  exit 1
fi

run_odoo() {
  if [[ "$(id -un)" == "root" ]]; then
    sudo -u odoo /usr/bin/odoo -c "$CONF" "$@"
  else
    /usr/bin/odoo -c "$CONF" "$@"
  fi
}

run_shell() {
  run_odoo -d "$DB" --no-http "$@"
}

mkdir -p "$EVIDENCE"
TS="$(date +%Y%m%d_%H%M%S)"
LOG="$EVIDENCE/run-${TS}.log"

exec > >(tee -a "$LOG") 2>&1

log "=== Fase 3A Sprint 1 Lab Validation ==="
log "BD=$DB CONF=$CONF"
log "justech_dev operativo: NO TOCAR"

log "--- Baseline integridad (pre-upgrade) ---"
run_shell <<'PY' | tee "$EVIDENCE/baseline-${TS}.json"
import json, sys
sys.argv = ["baseline"]
exec(open("/opt/odoo-dev/evidence/fiscal-phase3/fiscal-phase3-sprint1-validate-lab.py").read())
PY

log "--- Upgrade base + ncf ---"
run_odoo -d "$DB" -u justech_l10n_do_base,justech_l10n_do_ncf --stop-after-init --no-http

log "--- Install dashboard (estructura) ---"
run_odoo -d "$DB" -i justech_l10n_do_dashboard --stop-after-init --no-http

log "--- Post-upgrade integridad ---"
run_shell <<'PY' | tee "$EVIDENCE/post_upgrade-${TS}.json"
import json, sys
sys.argv = ["post_upgrade"]
exec(open("/opt/odoo-dev/evidence/fiscal-phase3/fiscal-phase3-sprint1-validate-lab.py").read())
PY

log "--- Comparación integridad ---"
python3 <<PY
import json, glob, os, sys
ev = "$EVIDENCE"
baselines = sorted(glob.glob(ev + "/baseline-*.json"))
posts = sorted(glob.glob(ev + "/post_upgrade-*.json"))
if not baselines or not posts:
    sys.exit("Missing snapshot files")
b = json.load(open(baselines[-1]))
a = json.load(open(posts[-1]))
issues = []
for k, label in [
    ("posted_moves", "posted_moves"),
    ("gl_debit", "gl_debit"),
    ("gl_credit", "gl_credit"),
    ("partial_reconciles", "partial_reconciles"),
]:
    if b.get(k) != a.get(k):
        issues.append(f"{label}: {b.get(k)} -> {a.get(k)}")
if not a.get("gl_balanced"):
    issues.append("GL desbalanceado")
result = {"ok": len(issues)==0, "issues": issues, "baseline": b, "after": a}
out = ev + "/validation-${TS}.json"
json.dump(result, open(out, "w"), indent=2)
print(json.dumps(result, indent=2))
sys.exit(0 if result["ok"] else 2)
PY

log "=== FIN — log: $LOG ==="
