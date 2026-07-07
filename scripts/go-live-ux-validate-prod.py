#!/usr/bin/env python3
"""GO-LIVE-UX — Validación final hellenia_prod."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from lxml import etree

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("GOLIVE_UX_EVIDENCE", "/var/lib/odoo/go-live-ux")
os.makedirs(OUT, exist_ok=True)

TEST_RE = re.compile(r"COA|TEST|SMOKE|QA|CERT|P13|FISCALRD|DEMO|DEBUG|DEV|SAMPLE|FAKE|MOCK", re.I)
JUSTECH_RE = re.compile(r"justech", re.I)

report = {"phase": "GO-LIVE-UX", "timestamp_utc": datetime.now(timezone.utc).isoformat(), "database": DB, "ok": True, "checks": {}, "blockers": []}


def fail(key):
    report["ok"] = False
    report["blockers"].append(key)
    report["checks"][key] = False


def menu_xid(menu):
    data = env["ir.model.data"].search([("model", "=", "ir.ui.menu"), ("res_id", "=", menu.id)], limit=1)
    return f"{data.module}.{data.name}" if data else None


def visible_roots(user):
    Menu = env["ir.ui.menu"].with_user(user)
    visible = set(Menu._visible_menu_ids())
    return Menu.search([("parent_id", "=", False), ("active", "=", True)]).filtered(lambda m: m.id in visible).sorted("sequence")


# Product form
prod = env["product.template"].search([], limit=1)
arch = prod.get_view(view_type="form")["arch"] if prod else ""
general = arch.split('page name="general_information"')[1][:6000] if 'page name="general_information"' in arch else arch

checks = {
    "product_no_justech": "Justech" not in general,
    "product_has_venta_compra": 'string="Venta"' in general and 'string="Compra"' in general,
    "sale_taxes_labeled": "Impuestos de venta" in general,
    "purchase_taxes_labeled": "Impuestos de compra" in general,
    "taxes_order_ok": general.find("Impuestos de venta") < general.find("Impuestos de compra")
    if "Impuestos de venta" in general and "Impuestos de compra" in general
    else False,
    "no_comercial_tab": "justech_commercial_tab" not in arch,
}

# Menus
config = env.ref("account.menu_finance_configuration", raise_if_not_found=False)
acct_sub = env.ref("account.account_account_menu", raise_if_not_found=False)
rates = env.ref("justech_multicurrency.menu_justech_multicurrency_rates", raise_if_not_found=False)
curr = env.ref("account.menu_action_currency_form", raise_if_not_found=False)
fiscal = env.ref("justech_l10n_do_base.menu_justech_do_fiscal_root", raise_if_not_found=False)
audit = env.ref("justech_global_audit_log.menu_justech_global_audit_root", raise_if_not_found=False)
settings = env.ref("justech_admin.menu_justech_settings_root", raise_if_not_found=False)

checks.update(
    {
        "accounting_submenu_active": bool(acct_sub and acct_sub.active),
        "plan_cuentas_visible": bool(env.ref("account.menu_action_account_form", raise_if_not_found=False)),
        "monedas_visible": bool(curr and curr.active),
        "tasas_visible": bool(rates and rates.active and rates.parent_id == config),
        "fiscal_separate": bool(fiscal and fiscal.parent_id == config),
        "audit_not_root_app": not (audit and not audit.parent_id),
        "audit_under_settings": bool(audit and settings and audit.parent_id == settings),
        "platform_justech_hidden": not env.ref("justech_multicurrency.menu_justech_platform_root", raise_if_not_found=False).active,
    }
)

admin = env.ref("base.user_admin")
normal = env["res.users"].search([("login", "=", "usuario.normal.demo14")], limit=1)
checks["admin_root_no_auditoria"] = "Auditoría" not in visible_roots(admin).mapped("name")
checks["client_no_auditoria_app"] = "Auditoría" not in visible_roots(normal).mapped("name") if normal else True
checks["client_no_justech_app"] = "Justech" not in visible_roots(normal).mapped("name") if normal else True

# NCF clean names
ncf_bad = []
for rng in env["justech.do.ncf.range"].search([]):
    if TEST_RE.search(rng.name or ""):
        ncf_bad.append(rng.name)
checks["ncf_names_clean"] = not ncf_bad
checks["ncf_bad_names"] = ncf_bad

# Purchase tax
pt = env["account.tax"].search([("type_tax_use", "=", "purchase"), ("amount", "=", 18)], limit=1)
checks["purchase_tax_name"] = pt.name if pt else None
checks["purchase_tax_ok"] = bool(pt and "Cost Good" not in (pt.name or "") and "ITBIS" in (pt.name or ""))

for k, v in checks.items():
    if isinstance(v, bool) and not v and k not in ("ncf_bad_names",):
        fail(k)
    report["checks"][k] = v

report["menu_audit"] = {
    "config_children": env["ir.ui.menu"].search([("parent_id", "=", config.id), ("active", "=", True)]).sorted("sequence").mapped("name") if config else [],
    "admin_roots": visible_roots(admin).mapped("name"),
    "audit_parent": audit.parent_id.name if audit and audit.parent_id else None,
    "audit_xid_parent": menu_xid(audit.parent_id) if audit and audit.parent_id else None,
}

with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\nVALIDATION_OK={'true' if report['ok'] else 'false'}")
env.cr.commit()
if not report["ok"]:
    raise SystemExit(1)
