#!/usr/bin/env python3
"""UX-FLOW-FIX — Validación de los 10 hallazgos en TEST/PROD."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

DB = env.cr.dbname
OUT = os.environ.get("UX_FLOW_FIX_EVIDENCE", "/tmp/ux-flow-fix")
os.makedirs(OUT, exist_ok=True)

report = {
    "phase": "UX-FLOW-FIX",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "ok": True,
    "findings_fixed": {},
    "pending": [],
    "checks": {},
}


def check(key, cond, detail=""):
    report["checks"][key] = {"pass": bool(cond), "detail": str(detail)[:500]}
    if not cond:
        report["ok"] = False
        report["pending"].append(key)


def view_arch(model, view_type="form", domain=None):
    rec = env[model]
    if domain:
        rec = rec.search(domain, limit=1)
    else:
        rec = rec.search([], limit=1)
    if not rec:
        return ""
    return rec.get_view(view_type=view_type).get("arch", "")


# 1. Tipo ingreso 607
inv = view_arch("account.move", "form", [("move_type", "=", "out_invoice")])
check("fix_01_income_type_607", "justech_do_income_type_607" in inv and "Tipo de ingreso" in inv, "field in invoice form")

# 2. Alerta multimoneda
so = view_arch("sale.order", "form")
check("fix_02_fx_warning_so", "hellenia_fx_rate_missing" in so and "hellenia_fx_rate_warning" in so, "sale order banner")
check("fix_02_fx_warning_inv", "hellenia_fx_rate_missing" in inv, "invoice banner fields")

# 3. Traducciones
check("fix_03_invoice_lines_es", "Invoice Lines" not in inv or "Líneas de factura" in inv, inv[:200])
menu_en = env["ir.ui.menu"].search([("name", "in", ["Reporting", "Tax Groups", "Vendor"])], limit=5)
check("fix_03_menus_en", len(menu_en) == 0, [m.complete_name for m in menu_en])

# 4. Void NCF hidden/ES
check("fix_04_void_ncf", "Void NCF" not in inv, "no Void NCF in form")
void_btn = env["ir.ui.view"].search([("model", "=", "account.move"), ("arch_db", "ilike", "Anular comprobante")], limit=1)
check("fix_04_anular_ncf", bool(void_btn), void_btn.name if void_btn else "")

# 5. Vendor → Proveedor
bill = view_arch("account.move", "form", [("move_type", "=", "in_invoice")])
check("fix_05_proveedor", "Proveedor" in bill and 'string="Vendor"' not in bill, bill[:300])

# 6. RNC en contactos
partner_tree = view_arch("res.partner", "list")
check("fix_06_rnc_column", "RNC / Cédula" in partner_tree or ('name="vat"' in partner_tree and "optional" in partner_tree), partner_tree[:300])
partner_form = view_arch("res.partner", "form")
check("fix_06_hide_technical", "justech_do_partner_id_type" not in partner_form or 'invisible="1"' in partner_form, "")

# 7. NCF navigation
for xid, label in (
    ("justech_l10n_do_base.menu_justech_do_document_types", "1. Tipos"),
    ("justech_l10n_do_ncf.menu_justech_do_ncf_ranges", "2. Rangos"),
    ("justech_l10n_do_ncf.menu_justech_do_ncf_consumption", "3. Consumo"),
):
    m = env.ref(xid, raise_if_not_found=False)
    check(f"fix_07_{xid.split('.')[-1]}", m and label in (m.name or ""), m.name if m else "missing")

# 8. Licencias y Personalizaciones
m = env.ref("justech_admin.menu_justech_modules", raise_if_not_found=False)
check("fix_08_licencias", m and "Licencias y Personalizaciones" in m.name, m.name if m else "")

# 9. Auditorías diferenciadas
fiscal = env.ref("justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False)
changes = env.ref("justech_global_audit_log.menu_justech_global_audit_root", raise_if_not_found=False)
check("fix_09_audit_fiscal", fiscal and "Fiscal" in fiscal.name, fiscal.name if fiscal else "")
check("fix_09_audit_changes", changes and "Cambios" in changes.name, changes.name if changes else "")

# 10. Ayuda multimoneda producto
prod = view_arch("product.template", "form")
check("fix_10_product_help", "Precios comerciales vs contables" in prod or "precio comercial" in prod.lower(), prod[:400])

fixed = sum(1 for k, v in report["checks"].items() if v["pass"] and k.startswith("fix_"))
report["findings_fixed"] = {"count": fixed, "total_scope": 10}
report["summary"] = "PASS" if report["ok"] else "FAIL"

path = os.path.join(OUT, "UX_FLOW_FIX_VALIDATION.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(json.dumps(report, indent=2, ensure_ascii=False))
