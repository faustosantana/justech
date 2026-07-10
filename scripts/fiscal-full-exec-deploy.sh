#!/usr/bin/env bash
# Despliegue completo Estándar Fiscal + Pagos y Retenciones — erp.justech.do / justech_dev
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
FILESTORE="/opt/odoo-dev/data/filestore/${DB}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_CUSTOM="${REPO_CUSTOM:-/opt/odoo-dev/src/jaios/custom}"
ADDONS="/opt/odoo-dev/custom-addons/justgroup/custom_addons"
BASE_URL="${BASE_URL:-https://erp.justech.do}"
EV="/opt/odoo-dev/evidence/fiscal-full-exec-$(date +%Y%m%d_%H%M%S)"

MODULES=(
  justech_l10n_do_base
  justech_l10n_do_ncf
  justech_l10n_do_reports
  justech_fiscal_admin
  justech_l10n_do_payments_withholding
)

mkdir -p "$EV"
exec > >(tee -a "$EV/run.log") 2>&1

fail() { echo "FISCAL_EXEC_FAIL: $*" >&2; exit 1; }

rollback_now() {
  local backup="$1"
  echo "==> ROLLBACK desde $backup"
  systemctl stop odoo-dev
  sudo -u odoo dropdb --if-exists "$DB"
  sudo -u odoo createdb -O odoo "$DB"
  sudo -u odoo pg_restore -d "$DB" "$backup/${DB}.dump"
  rm -rf "$FILESTORE"
  mkdir -p "$(dirname "$FILESTORE")"
  tar -xzf "$backup/filestore_${DB}.tar.gz" -C "$(dirname "$FILESTORE")"
  chown -R odoo:odoo "$FILESTORE"
  systemctl start odoo-dev
  echo "ROLLBACK_DONE"
}

echo "========================================"
echo "FISCAL FULL EXEC — $(date -Iseconds)"
echo "EVIDENCE=$EV"
echo "========================================"

echo "==> PRE: baseline"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_baseline.json"
import json
cr = env.cr
cr.execute("SELECT COUNT(*) FROM account_move WHERE state='posted'")
posted = cr.fetchone()[0]
cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
reconciles = cr.fetchone()[0]
print(json.dumps({"posted": posted, "reconciles": reconciles}))
PY

echo "==> BACKUP"
BACKUP_OUT=$(bash "${SCRIPT_DIR}/fiscal-integration-dev1-backup.sh" "$(date +%Y%m%d_%H%M%S)" "fiscal-full-exec" 2>&1 | tee "$EV/backup.log" | tail -1)
BACKUP_PATH=$(echo "$BACKUP_OUT" | awk '{print $NF}')
[[ -d "$BACKUP_PATH" ]] || fail "backup failed: $BACKUP_OUT"
echo "$BACKUP_PATH" > "$EV/BACKUP_PATH.txt"

echo "==> Sync módulos"
for mod in "${MODULES[@]}"; do
  src="${REPO_CUSTOM}/${mod}"
  dst="${ADDONS}/${mod}"
  [[ -d "$src" ]] || fail "missing source $src"
  rsync -a --delete "${src}/" "${dst}/"
  chown -R odoo:odoo "${dst}"
done

for s in fiscal-integration-env-healthcheck.py fiscal-standard-validate.py fiscal-integration-dev1-post-validate.py fiscal-integration-606-period-validate.py; do
  src="${SCRIPT_DIR}/${s}"
  dst="/opt/odoo-dev/scripts/${s}"
  if [[ -f "$src" ]]; then
    install -m 0755 "$src" "$dst"
  fi
done

echo "==> UPGRADE módulos fiscales"
UPGRADE_LIST=$(IFS=,; echo "${MODULES[*]}")
if ! sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$DB" \
  -u "$UPGRADE_LIST" \
  --stop-after-init --no-http 2>&1 | tee "$EV/upgrade.log"; then
  rollback_now "$BACKUP_PATH"
  fail "upgrade failed"
fi
if grep -iE 'ParseError|Traceback|CRITICAL' "$EV/upgrade.log" | grep -v DeprecationWarning | grep -v '^$' | head -1 | grep -q .; then
  rollback_now "$BACKUP_PATH"
  fail "upgrade log errors"
fi

echo "==> INSTALL justech_l10n_do_payments_withholding (si pendiente)"
MOD=$(sudo -u odoo psql -d "$DB" -t -A -c "SELECT state FROM ir_module_module WHERE name='justech_l10n_do_payments_withholding' LIMIT 1" || echo uninstalled)
if [[ "$MOD" != "installed" ]]; then
  if ! sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$DB" \
    -i justech_l10n_do_payments_withholding \
    --stop-after-init --no-http 2>&1 | tee -a "$EV/install_payments.log"; then
    rollback_now "$BACKUP_PATH"
    fail "install payments failed"
  fi
fi

echo "==> Sync catálogo retenciones (4 empresas DO)"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/sync_catalog.json"
import json
Catalog = env["justech.do.withholding.catalog"]
out = []
for co in env["res.company"].search([("country_id.code", "=", "DO")]):
    rows = Catalog.sync_catalog_from_taxes(co)
    active = Catalog.search_count([("company_id", "=", co.id), ("active", "=", True)])
    out.append({"company": co.name, "synced": len(rows), "active": active})
print(json.dumps(out, indent=2))
PY

systemctl restart odoo-dev
sleep 8

echo "==> POST: login HTTP"
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}/web/login" || echo 000)
echo "login_http=$HTTP" | tee "$EV/login.txt"
[[ "$HTTP" == "200" ]] || fail "login not 200"

echo "==> POST: RPC method check"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EV/rpc_check.json"
import json
ok = hasattr(env["res.config.settings"], "action_justech_open_fiscal_admin_center")
print(json.dumps({"rpc_method": ok}))
PY
grep -q '"rpc_method": true' "$EV/rpc_check.json" || fail "RPC method missing"

echo "==> POST: healthcheck"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY
grep -q '"passed": true' "$EV/post_healthcheck.json" || fail "healthcheck failed"

echo "==> POST: baseline histórico intacto"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_baseline.json"
import json
cr = env.cr
cr.execute("SELECT COUNT(*) FROM account_move WHERE state='posted'")
posted = cr.fetchone()[0]
cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
reconciles = cr.fetchone()[0]
print(json.dumps({"posted": posted, "reconciles": reconciles}))
PY

echo "==> POST: validación estándar (4 empresas)"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_standard_validate.json"
exec(open("${SCRIPT_DIR}/fiscal-standard-validate.py").read())
PY

echo "FISCAL_EXEC_OK $EV"
