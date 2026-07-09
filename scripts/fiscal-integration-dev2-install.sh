#!/usr/bin/env bash
# DEV-2 — Backup + instalar justech_l10n_do_reports en erp.justech.do
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
TS="$(date +%Y%m%d_%H%M%S)"

echo "==> Backup DEV-2"
bash /opt/odoo-dev/scripts/fiscal-integration-dev1-backup.sh "${TS}" dev2
BACKUP="/opt/odoo-dev/backups/fiscal-integration-dev2-${TS}"
test -d "${BACKUP}"

echo "==> Validate restore"
bash /opt/odoo-dev/scripts/fiscal-integration-dev1-validate-restore.sh "${BACKUP}"

echo "==> Instalar justech_l10n_do_reports"
sudo -u odoo /usr/bin/odoo -c "${CONF}" -d "${DB}" -i justech_l10n_do_reports \
  --stop-after-init --no-http 2>&1 | tail -20

echo "==> Reconfirm fiscal disabled"
sudo -u odoo psql -d "${DB}" -c "UPDATE res_company SET justech_do_fiscal_enabled = false;"
ENABLED=$(sudo -u odoo psql -d "${DB}" -t -A -c "SELECT COUNT(*) FROM res_company WHERE justech_do_fiscal_enabled = true;")
test "${ENABLED}" = "0"

echo "==> Post validate histórico"
sudo -u odoo /usr/bin/odoo shell -c "${CONF}" -d "${DB}" --no-http <<'PY' | tee "${BACKUP}/post_dev2_validate.json"
exec(open("/opt/odoo-dev/scripts/fiscal-integration-dev1-post-validate.py").read())
PY

echo "==> Reports 606/607 read-only smoke"
sudo -u odoo /usr/bin/odoo shell -c "${CONF}" -d "${DB}" --no-http <<'PY' | tee "${BACKUP}/reports_smoke.json"
import json
mod = env["ir.module.module"].search([("name", "=", "justech_l10n_do_reports")], limit=1)
out = {"reports_installed": mod.state == "installed", "version": mod.latest_version}
cr = env.cr
cr.execute("""
    SELECT COUNT(*) FROM account_move
    WHERE state='posted' AND move_type IN ('out_invoice','out_refund')
      AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
""")
out["moves_607_eligible"] = cr.fetchone()[0]
cr.execute("""
    SELECT COUNT(*) FROM account_move
    WHERE state='posted' AND move_type IN ('in_invoice','in_refund')
      AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
""")
out["moves_606_eligible"] = cr.fetchone()[0]
# readonly: instanciar wizard si existe
if "justech.do.fiscal.report.wizard" in env:
    w = env["justech.do.fiscal.report.wizard"].new({"report_type": "607"})
    out["wizard_607_ok"] = bool(w)
if "justech.do.dgii.report.review" in env:
    out["review_model_ok"] = True
print(json.dumps(out, indent=2, default=str))
PY

echo "${BACKUP}" > "${BACKUP}/BACKUP_PATH.txt"
echo "DEV2_INSTALL_OK backup=${BACKUP}"
