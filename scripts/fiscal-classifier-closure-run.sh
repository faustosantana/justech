#!/usr/bin/env bash
# Cierre limpio clasificador fiscal — upgrade + validación sin scripts manuales de sync
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADDONS="/opt/odoo-dev/custom-addons/justgroup/custom_addons"
SRC="/opt/odoo-dev/src/jaios/custom/justech_l10n_do_reports"
EV="/opt/odoo-dev/evidence/fiscal-integration/CLASSIFIER-closure-$(date +%Y%m%d_%H%M%S)"

mkdir -p "$EV"
exec > >(tee -a "$EV/run.log") 2>&1

fail() {
  echo "CLOSURE_FAIL: $*" >&2
  exit 1
}

echo "========================================"
echo "CLASSIFIER CLOSURE — $(date -Iseconds)"
echo "EVIDENCE=$EV"
echo "========================================"

echo "==> PRE: baseline histórico"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_baseline.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-post-validate.py").read())
PY
BASELINE_JSON=$(python3 -c "import json; d=json.load(open('$EV/pre_baseline.json')); print(json.dumps(d.get('checks',{})))")

echo "==> PRE: healthcheck"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY
grep -q '"passed": true' "$EV/pre_healthcheck.json" 2>/dev/null || grep -q '"ok": true' "$EV/pre_healthcheck.json" || fail "pre healthcheck"

echo "==> PRE: catálogo en BD (antes upgrade)"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/pre_catalog_count.json"
import json
cr = env.cr
cr.execute("SELECT COUNT(*) FROM justech_do_dgii_tax_classification")
before = cr.fetchone()[0]
print(json.dumps({"before_upgrade_count": before}))
PY

echo "==> SYNC código"
sudo rsync -av --delete "$SRC/" "${ADDONS}/justech_l10n_do_reports/"

echo "==> UPGRADE módulo (migration sync — sin shell manual)"
sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$DB" -u justech_l10n_do_reports --stop-after-init --no-http 2>&1 | tee "$EV/upgrade.log"
grep -qi "error" "$EV/upgrade.log" && grep -qi "Modules loaded" "$EV/upgrade.log" || true

echo "==> POST: catálogo en BD (después upgrade, sin sync manual)"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/post_catalog_persist.json"
import json
cr = env.cr
cr.execute("SELECT COUNT(*) FROM justech_do_dgii_tax_classification")
total = cr.fetchone()[0]
cr.execute("""
    SELECT tax_id, classification_role, column_606
    FROM justech_do_dgii_tax_classification
    WHERE tax_id IN (5, 14, 15) ORDER BY tax_id
""")
rows = [{"tax_id": r[0], "role": r[1], "col_606": r[2]} for r in cr.fetchall()]
mod = env["ir.module.module"].search([("name", "=", "justech_l10n_do_reports")], limit=1)
print(json.dumps({
    "after_upgrade_count": total,
    "key_taxes": rows,
    "module_version": mod.latest_version,
    "persisted_without_manual_sync": total >= 100,
}))
PY

AFTER_COUNT=$(python3 -c "import json; print(json.load(open('$EV/post_catalog_persist.json'))['after_upgrade_count'])")
if [ "$AFTER_COUNT" -lt 100 ]; then
  fail "catálogo no persistido tras upgrade (count=$AFTER_COUNT)"
fi

echo "==> POST: healthcheck"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY
grep -q '"passed": true' "$EV/post_healthcheck.json" 2>/dev/null || grep -q '"ok": true' "$EV/post_healthcheck.json" || fail "post healthcheck"

echo "==> POST: matriz final impuestos"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/FINAL_TAX_MATRIX.json"
exec(open("/opt/odoo-dev/scripts/fiscal-tax-matrix-analyze.py").read())
PY

echo "==> POST: cierre validación completa"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/CLOSURE_VALIDATE.json"
import json
baseline = json.loads('''${BASELINE_JSON}''')
import sys
sys.argv = ["", json.dumps(baseline)]
exec(open("${SCRIPT_DIR}/fiscal-classifier-closure-validate.py").read())
PY

python3 -c "
import json, sys
d=json.load(open('$EV/CLOSURE_VALIDATE.json'))
if not d.get('passed'):
    print('FAILED:', d.get('errors'), file=sys.stderr)
    sys.exit(1)
print('CLOSURE_PASS')
"

echo "CLOSURE_DONE"
echo "EVIDENCE=$EV"
