#!/usr/bin/env bash
# Despliegue motor clasificación fiscal DGII — erp.justech.do / justech_dev
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADDONS="/opt/odoo-dev/custom-addons/justgroup/custom_addons"
PERIOD="${PERIOD:-202606}"
EV="/opt/odoo-dev/evidence/fiscal-integration/CLASSIFIER-deploy-$(date +%Y%m%d_%H%M%S)"

mkdir -p "$EV"
exec > >(tee -a "$EV/run.log") 2>&1

fail() {
  echo "CLASSIFIER_DEPLOY_FAIL: $*" >&2
  exit 1
}

echo "========================================"
echo "DGII CLASSIFIER DEPLOY — $(date -Iseconds)"
echo "EVIDENCE=$EV"
echo "PERIOD=$PERIOD"
echo "========================================"

echo "==> PRE: backup"
BACKUP="/opt/odoo-dev/backups/classifier-pre-$(date +%Y%m%d_%H%M%S)"
sudo mkdir -p "$BACKUP"
sudo chown odoo:odoo "$BACKUP"
sudo -u odoo pg_dump -Fc -f "$BACKUP/${DB}.dump" "$DB"
sudo tar -czf "$BACKUP/filestore_${DB}.tar.gz" -C /opt/odoo-dev/data/filestore "${DB}"
echo "$BACKUP" > "$EV/BACKUP_PATH.txt"

echo "==> PRE: healthcheck"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY
grep -q '"passed": true' "$EV/pre_healthcheck.json" || fail "pre healthcheck failed"

echo "==> PRE: baseline histórico"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_baseline.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-post-validate.py").read())
PY

echo "==> PRE: 606 período ${PERIOD}"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_606_${PERIOD}.json"
import sys
sys.argv = ["", "${PERIOD}"]
exec(open("${SCRIPT_DIR}/fiscal-integration-606-period-validate.py").read())
PY

echo "==> PRE: matriz impuestos"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/pre_tax_matrix.json"
exec(open("/opt/odoo-dev/scripts/fiscal-tax-matrix-analyze.py").read())
PY

echo "==> SYNC código"
sudo rsync -av --delete \
  /opt/odoo-dev/src/jaios/custom/justech_l10n_do_reports/ \
  "${ADDONS}/justech_l10n_do_reports/"

echo "==> UPGRADE módulo"
sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$DB" -u justech_l10n_do_reports --stop-after-init --no-http

echo "==> POST: sync clasificaciones"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/post_sync_classifications.json"
import json
Classification = env["justech.do.dgii.tax.classification"].sudo()
created = Classification.sync_from_taxes()
env.cr.commit()
all_rows = Classification.search([])
print(json.dumps({
    "created": len(created),
    "total": len(all_rows),
    "sample": [{
        "tax_id": r.tax_id.id,
        "tax": r.tax_id.name,
        "role": r.classification_role,
        "606": r.column_606,
        "607": r.column_607,
    } for r in all_rows[:20]],
}, indent=2, default=str))
PY

echo "==> POST: healthcheck"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY
grep -q '"passed": true' "$EV/post_healthcheck.json" || fail "post healthcheck failed"

echo "==> POST: baseline histórico"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_baseline.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-post-validate.py").read())
PY

echo "==> POST: validar reportes 606-609-623"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/post_all_reports_validate.json"
import json
from datetime import date
from calendar import monthrange

period = "${PERIOD}"
year, month = int(period[:4]), int(period[4:6])
date_from = date(year, month, 1)
date_to = date(year, month, monthrange(year, month)[1])
company = env.company
out = {}
for code, model in [
    ("606", "justech.do.dgii.606.exporter"),
    ("607", "justech.do.dgii.607.exporter"),
    ("608", "justech.do.dgii.608.exporter"),
    ("609", "justech.do.dgii.609.exporter"),
    ("623", "justech.do.dgii.623.exporter"),
]:
    exp = env[model]
    try:
        res = exp.validate_period(company, date_from, date_to, refresh_states=False)
        out[code] = {
            "counts": res.get("counts"),
            "error_lines": len(res.get("errors_flat") or []),
            "uses_classifier": "justech.do.dgii.tax.classifier" in env,
            "uses_fdp": "justech.do.fiscal.data.provider" in env,
        }
    except Exception as e:
        out[code] = {"error": str(e)}
print(json.dumps(out, indent=2, default=str))
PY

echo "==> POST: 606 período ${PERIOD} detallado"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_606_${PERIOD}.json"
import sys
sys.argv = ["", "${PERIOD}"]
exec(open("${SCRIPT_DIR}/fiscal-integration-606-period-validate.py").read())
PY

echo "==> POST: columnas N/W/X muestra telecom"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/post_606_columns_sample.json"
import json
from datetime import date
from calendar import monthrange

period = "${PERIOD}"
year, month = int(period[:4]), int(period[4:6])
date_from = date(year, month, 1)
date_to = date(year, month, monthrange(year, month)[1])
exporter = env["justech.do.dgii.606.exporter"]
company = env.company
buckets = exporter.classify_moves(company, date_from, date_to, refresh_states=False)
classifier = env["justech.do.dgii.tax.classifier"]
rows = []
for move in buckets["valid"]:
    cols = classifier.move_column_amounts(move, "606")
    if cols.get("X") or cols.get("W") or cols.get("N"):
        rows.append({
            "move": move.name,
            "ncf": env["justech.do.fiscal.data.provider"].get_ncf(move),
            "N": cols.get("N", 0),
            "W": cols.get("W", 0),
            "X": cols.get("X", 0),
            "Y": cols.get("Y", 0),
        })
print(json.dumps({"sample_count": len(rows), "rows": rows[:30]}, indent=2, default=str))
PY

echo "CLASSIFIER_DEPLOY_PASS"
echo "EVIDENCE=$EV"
