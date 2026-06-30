#!/usr/bin/env python3
"""Fase 17 — Validación UX, localización RD y regresión completa en TEST."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

company = env.company
report = {
    "phase": "17-ux-hardening",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "modules": {},
    "ux": {},
    "regression": {},
    "tests": {},
    "ok": True,
    "errors": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def pass_(name, detail=""):
    report["tests"][name] = {"status": "PASS", "detail": detail}


def fail(name, msg):
    report["tests"][name] = {"status": "FAIL", "message": msg}
    err(f"{name}: {msg}")


# --- Módulo hellenia_ux ---
mod = env["ir.module.module"].search([("name", "=", "hellenia_ux")], limit=1)
if not mod or mod.state != "installed":
    if mod:
        mod.button_immediate_install()
        env.cr.commit()
    else:
        fail("module_hellenia_ux", "módulo no encontrado")
        print("PHASE17:" + json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(1)
else:
    mod.button_immediate_upgrade()
    env.cr.commit()

report["modules"]["hellenia_ux"] = mod.state
env["hellenia.ui.menu.customizer"].apply_all()
env.cr.commit()

# --- UX: métodos de pago español ---
journals = env["account.journal"].search([("type", "in", ["bank", "cash"]), ("active", "=", True)])
generic = {"Manual Payment", "Checks", "Check"}
all_methods = journals.mapped("inbound_payment_method_line_ids.name") + journals.mapped(
    "outbound_payment_method_line_ids.name"
)
bad_methods = [m for m in all_methods if m in generic]
if not bad_methods:
    pass_("payment_methods_spanish", list(set(all_methods)))
else:
    fail("payment_methods_spanish", f"genéricos: {bad_methods}")

bnkd = env["account.journal"].search([("code", "=", "BNKD")], limit=1)
if bnkd and bnkd.bank_account_id:
    pass_("bank_account_linked", bnkd.bank_account_id.acc_number)
else:
    fail("bank_account_linked", "BNKD sin cuenta")

# --- UX: campos modelo español ---
ncf_field = env["account.move"]._fields["justech_do_ncf"]
if "Comprobante Fiscal" in (ncf_field.string or ""):
    pass_("ncf_label_spanish", ncf_field.string)
else:
    fail("ncf_label_spanish", ncf_field.string)

void_wiz = env["ir.model"].search([("model", "=", "justech.do.ncf.void.wizard")], limit=1)
if void_wiz:
    pass_("void_wizard_exists", void_wiz.name)
else:
    fail("void_wizard_exists", "wizard no encontrado")

# --- QR desactivado ---
if not company.hellenia_show_qr_on_invoice:
    pass_("qr_disabled", "hellenia_show_qr_on_invoice=False")
else:
    fail("qr_disabled", "QR aún activo en compañía")

# --- Menús Justech integrados ---
menu_checks = [
    ("justech_l10n_do_base.menu_justech_do_fiscal_root", "Localización Dominicana"),
    ("justech_l10n_do_reports.menu_justech_do_reports_root", "Reportes DGII"),
    ("justech_l10n_do_reports.menu_justech_do_audit_root", "Auditoría"),
]
for xid, label in menu_checks:
    menu = env.ref(xid, raise_if_not_found=False)
    if menu and menu.active and label in (menu.name or ""):
        pass_(f"menu_{xid.split('.')[-1]}", menu.name)
    else:
        fail(f"menu_{xid.split('.')[-1]}", f"menu inactivo o etiqueta incorrecta: {menu.name if menu else 'missing'}")

# --- Retenciones activas ---
for key, (name, use) in {
    "ret_gov": ("-5% ISR Gov.", "sale"),
    "ret_30": ("-30% ITBIS Leg. (N02-05)", "purchase"),
    "ret_10": ("-10% ISR Fee", "purchase"),
    "ret_75": ("-75% ITBIS (N08-10)", "purchase"),
}.items():
    tax = env["account.tax"].search([("name", "=", name), ("type_tax_use", "=", use)], limit=1)
    if tax and tax.active:
        pass_(key, name)
    else:
        fail(key, f"{name} no activo")

# --- Regresión pagos (smoke) ---
tax_18 = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
csh = env["account.journal"].search([("code", "=", "CSH1")], limit=1)

try:
    with env.cr.savepoint():
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({
                "product_id": product.id, "quantity": 1, "price_unit": 100,
                "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
            })],
        })
        inv.action_post()
        wiz = env["account.payment.register"].with_context(
            active_model="account.move", active_ids=inv.ids
        ).create({"journal_id": csh.id if csh else False})
        has_lines = bool(wiz.line_ids)
        has_ncf_col = "justech_do_ncf" in env["account.move.line"]._fields
        if has_lines and has_ncf_col:
            pass_("payment_wizard_documents", f"lines={len(wiz.line_ids)}")
        else:
            fail("payment_wizard_documents", "sin líneas o sin NCF")
except Exception as exc:  # noqa: BLE001
    fail("payment_wizard_documents", str(exc))

# --- Regresión 606/607/608 ---
try:
    with env.cr.savepoint():
        for rtype in ("606", "607", "608"):
            wiz = env["justech.do.fiscal.report.wizard"].create({
                "report_type": rtype,
                "date_from": date.today().replace(month=1, day=1),
                "date_to": date.today(),
            })
            wiz.action_generate()
        pass_("reports_606_607_608", "generados")
except Exception as exc:  # noqa: BLE001
    fail("reports_606_607_608", str(exc))

# --- Escaneo vistas custom inglés obvio ---
english_patterns = re.compile(
    r"\b(Void NCF|Void Reason|Manual Payment|Customer Code|Untaxed Amount|Company Bank Account)\b"
)
views = env["ir.ui.view"].search([
    ("arch_db", "ilike", "justech"),
    "|", ("arch_db", "ilike", "hellenia"), ("name", "ilike", "hellenia"),
])
english_hits = []
for view in views:
    arch = view.arch_db or ""
    if english_patterns.search(arch):
        english_hits.append(view.name)
if not english_hits:
    pass_("no_english_in_custom_views", "sin coincidencias críticas")
else:
    fail("no_english_in_custom_views", ", ".join(english_hits[:5]))

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t.get("status") == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t.get("status") == "FAIL"),
    "total": len(report["tests"]),
}

print("PHASE17:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
