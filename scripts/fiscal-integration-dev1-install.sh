#!/usr/bin/env bash
# DEV-1 — Instalar justech_l10n_do_base + ncf en erp.justech.do (coexistencia Adel segura).
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
BACKUP_DIR="${1:?Usage: $0 /path/to/validated/backup}"

echo "==> Pre-check: backup exists"
test -f "${BACKUP_DIR}/justech_dev.dump"

echo "==> Instalar justech_l10n_do_base"
sudo -u odoo /usr/bin/odoo -c "${CONF}" -d "${DB}" -i justech_l10n_do_base \
  --stop-after-init --no-http 2>&1 | tail -8

echo "==> Desactivar fiscal Justech en todas las empresas (coexistencia Adel)"
sudo -u odoo psql -d "${DB}" -c "UPDATE res_company SET justech_do_fiscal_enabled = false;"
sudo -u odoo psql -d "${DB}" -t -c "SELECT COUNT(*) FROM res_company WHERE justech_do_fiscal_enabled = true;" | grep -q '^[[:space:]]*0$'

echo "==> Instalar justech_l10n_do_ncf"
sudo -u odoo /usr/bin/odoo -c "${CONF}" -d "${DB}" -i justech_l10n_do_ncf \
  --stop-after-init --no-http 2>&1 | tail -8

echo "==> Reconfirmar fiscal desactivado"
sudo -u odoo psql -d "${DB}" -c "UPDATE res_company SET justech_do_fiscal_enabled = false;"
ENABLED=$(sudo -u odoo psql -d "${DB}" -t -A -c "SELECT COUNT(*) FROM res_company WHERE justech_do_fiscal_enabled = true;")
test "${ENABLED}" = "0"

echo "==> Post-validación"
sudo -u odoo /usr/bin/odoo shell -c "${CONF}" -d "${DB}" --no-http <<'PY' | tee /tmp/dev1_post_validate.json
exec(open("/opt/odoo-dev/scripts/fiscal-integration-dev1-post-validate.py").read())
PY

echo "INSTALL_DEV1_OK"
