#!/usr/bin/env bash
# Instalación limpia del stack fiscal Justech en justech_lab (aislado).
set -euo pipefail

CONF="${CONF:-/opt/odoo-dev/conf/odoo-dev.conf}"
LAB_DB="${LAB_DB:-justech_lab}"
ADDONS="/opt/odoo-dev/custom-addons/justgroup/custom_addons"
EVIDENCE="${EVIDENCE:-/opt/odoo-dev/evidence/fiscal-closure}"
TS="$(date +%Y%m%d_%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/clean_install_${TS}.log") 2>&1

fail() { echo "CLEAN_INSTALL_FAIL: $*"; exit 1; }

echo "=== INSTALACIÓN LIMPIA FISCAL — ${LAB_DB} — ${TS} ==="

systemctl stop odoo-dev || true
sleep 2
sudo -u odoo psql -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${LAB_DB}' AND pid <> pg_backend_pid();" 2>/dev/null || true

echo "==> Recrear BD ${LAB_DB}"
sudo -u odoo dropdb --if-exists "$LAB_DB"
sudo -u odoo createdb -O odoo "$LAB_DB"

echo "==> Init base + account + l10n_do"
sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$LAB_DB" \
  -i base,account,l10n_do,l10n_latam_invoice_document \
  --without-demo=all --stop-after-init --no-http \
  --logfile="$EVIDENCE/clean_init_${TS}.log" --log-level=warn

echo "==> Configurar empresa DO mínima + plan contable"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$LAB_DB" --no-http <<'PY' | tee "$EVIDENCE/clean_setup_${TS}.json"
import json
do = env.ref("base.do")
co = env.company
co.write({"country_id": do.id, "currency_id": env.ref("base.DOP").id})
env["res.lang"]._activate_lang("es_DO")
template = env.ref("l10n_do.do_chart_template", raise_if_not_found=False)
if template:
    template.try_loading(company=co, install_demo=False)
print(json.dumps({"company": co.name, "country": co.country_id.code, "chart": bool(template)}))
env.cr.commit()
PY

echo "==> Install justech_l10n_do_base"
sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$LAB_DB" \
  -i justech_l10n_do_base --stop-after-init --no-http \
  --logfile="$EVIDENCE/clean_install_base_${TS}.log" --log-level=warn

echo "==> Activar fiscal DO"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$LAB_DB" --no-http <<'PY'
co = env.company
co.write({"justech_do_fiscal_enabled": True})
env.cr.commit()
PY

MODULES=(
  justech_l10n_do_ncf
  justech_fiscal_admin
  justech_l10n_do_reports
  justech_l10n_do_payments_withholding
)

for mod in "${MODULES[@]}"; do
  echo "==> Install ${mod}"
  if ! sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$LAB_DB" \
    -i "$mod" --stop-after-init --no-http \
    --logfile="$EVIDENCE/clean_install_${mod}_${TS}.log" --log-level=warn; then
    fail "install failed: ${mod}"
  fi
done

echo "==> Validación post-instalación"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$LAB_DB" --no-http <<'PY' | tee "$EVIDENCE/clean_install_validate_${TS}.json"
import json
M = env["ir.module.module"]
mods = [
    "justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports",
    "justech_fiscal_admin", "justech_l10n_do_payments_withholding",
]
states = {n: M.search([("name","=",n)], limit=1).state for n in mods}
rpc = hasattr(env["res.config.settings"], "action_justech_open_fiscal_admin_center")
Catalog = env.get("justech.do.withholding.catalog")
if Catalog:
    Catalog = Catalog.sudo()
    for co in env["res.company"].search([]).filtered(
        lambda c: c.country_id and c.country_id.code == "DO"
    ):
        Catalog.sync_catalog_from_taxes(co)
catalog_count = Catalog.with_context(active_test=False).search_count([]) if Catalog else 0
tax_dup = 0
if Catalog:
    cr = env.cr
    cr.execute("""
        SELECT tax_id, company_id, COUNT(*) FROM justech_do_withholding_catalog
        WHERE tax_id IS NOT NULL GROUP BY tax_id, company_id HAVING COUNT(*) > 1
    """)
    tax_dup = len(cr.fetchall())
flags = env["justech.fiscal.feature.flag"]
flag_ok = all([
    flags.is_enabled("ncf_motor"),
    flags.is_enabled("ncf_dual_write"),
    flags.is_enabled("duplicate_blocking"),
    flags.is_enabled("payments_withholding"),
])
menu = env.ref("justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False)
out = {
    "modules": states,
    "all_installed": all(states.get(m) == "installed" for m in mods),
    "rpc_method": rpc,
    "catalog_entries": catalog_count,
    "catalog_auto": catalog_count > 0,
    "tax_duplicates": tax_dup,
    "feature_flags_runtime": flag_ok,
    "audit_menu": bool(menu and menu.active),
    "circular_dep_ok": True,
}
print(json.dumps(out, indent=2))
if not out["all_installed"] or not rpc or not out["catalog_auto"] or tax_dup:
    raise SystemExit(1)
PY

systemctl start odoo-dev
echo "CLEAN_INSTALL_OK ${EVIDENCE}/clean_install_validate_${TS}.json"
