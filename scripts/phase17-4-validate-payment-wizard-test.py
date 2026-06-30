#!/usr/bin/env python3
"""Fase 17.4 — Validación RPC wizard pagos y regresión TEST."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report = {
    "phase": "17.4-payment-wizard-rpc-fix",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "El upgrade de hellenia_account se ejecutó en contenedor efímero (docker compose run) "
        "mientras el contenedor odoo en ejecución no reinició su registry Python. "
        "Las acciones/vistas en BD apuntaban a hellenia.payment.partner.wizard pero el worker "
        "HTTP tenía módulos en estado inconsistente (to upgrade) sin el modelo cargado → KeyError 404."
    ),
    "fix_applied": [
        "Wizard movido a custom/hellenia_account/wizards/ con imports explícitos",
        "hellenia_account 19.0.1.0.4 — reinicio obligatorio del contenedor odoo tras -u",
        "Botón Nuevo en listas Clientes/Proveedores → Pagos abre el wizard",
    ],
    "tests": {},
    "ok": True,
    "errors": [],
}


def err(msg):
    report["ok"] = False
    report["errors"].append(msg)


def pass_(name, detail=""):
    report["tests"][name] = {"status": "PASS", "detail": detail}


def fail(name, msg):
    report["tests"][name] = {"status": "FAIL", "message": msg}
    err(f"{name}: {msg}")


# --- Módulo instalado y consistente ---
mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if not mod:
    fail("module_exists", "hellenia_account no encontrado")
else:
    if mod.state == "to upgrade":
        mod.button_immediate_upgrade()
        env.cr.commit()
    elif mod.state != "installed":
        mod.button_immediate_install()
        env.cr.commit()
    if mod.state == "installed":
        pass_("module_installed", mod.latest_version or mod.installed_version)
    else:
        fail("module_installed", f"state={mod.state}")

# --- Modelo en registry ---
if "hellenia.payment.partner.wizard" in env.registry:
    pass_("model_in_registry", "hellenia.payment.partner.wizard")
else:
    fail("model_in_registry", "KeyError esperado en worker sin reinicio")

ir_model = env["ir.model"].search([("model", "=", "hellenia.payment.partner.wizard")], limit=1)
if ir_model:
    pass_("ir_model_record", ir_model.name)
else:
    fail("ir_model_record", "sin registro ir.model")

# --- Acciones ---
for xid, key in (
    ("hellenia_account.action_hellenia_register_customer_payment", "action_customer"),
    ("hellenia_account.action_hellenia_register_vendor_payment", "action_vendor"),
):
    act = env.ref(xid, raise_if_not_found=False)
    if act and act.res_model == "hellenia.payment.partner.wizard":
        pass_(key, act.name)
    else:
        fail(key, "acción incorrecta o ausente")

# --- get_views sin error (simula RPC UI) ---
try:
    views = env["hellenia.payment.partner.wizard"].get_views([(False, "form")])
    if "form" in views.get("views", {}):
        pass_("wizard_get_views", "form OK")
    else:
        fail("wizard_get_views", "sin vista form")
except Exception as exc:  # noqa: BLE001
    fail("wizard_get_views", str(exc))

setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
env.cr.commit()

customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD")], limit=1)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_18 = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1)
tax_purchase = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase")], limit=1)


def _method_line(journal, label, ptype="inbound"):
    lines = journal.inbound_payment_method_line_ids if ptype == "inbound" else journal.outbound_payment_method_line_ids
    return lines.filtered(lambda l: l.name == label)[:1]


# --- Flujo clientes: facturas pendientes ---
try:
    with env.cr.savepoint():
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({
                "product_id": product.id, "quantity": 1, "price_unit": 1500,
                "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
            })],
        })
        inv.action_post()
        mline = _method_line(bnkd, "Transferencia", "inbound")
        wiz = env["hellenia.payment.partner.wizard"].create({
            "partner_type": "customer",
            "partner_id": customer.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": mline.id if mline else False,
        })
        line = wiz.line_ids.filtered(lambda l: l.move_id == inv)
        fields_ok = all(
            getattr(line, f, False) is not False or f in ("ncf",)
            for f in ("invoice_name", "invoice_date", "amount_total", "amount_residual", "amount_to_pay")
        ) if line else False
        if line and fields_ok:
            pass_("customer_pending_invoices", f"lines={len(wiz.line_ids)} ncf={line.ncf or '—'}")
        else:
            fail("customer_pending_invoices", f"lines={len(wiz.line_ids)}")
except Exception as exc:  # noqa: BLE001
    fail("customer_pending_invoices", str(exc))

# --- Flujo proveedores ---
try:
    with env.cr.savepoint():
        bill = env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": vendor.id,
            "invoice_date": date.today(),
            "invoice_line_ids": [Command.create({
                "product_id": product.id, "quantity": 1, "price_unit": 900,
                "tax_ids": [Command.set(tax_purchase.ids)] if tax_purchase else [],
            })],
        })
        bill.action_post()
        mline = _method_line(bnkd, "Transferencia", "outbound")
        wiz = env["hellenia.payment.partner.wizard"].create({
            "partner_type": "supplier",
            "partner_id": vendor.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": mline.id if mline else False,
        })
        line = wiz.line_ids.filtered(lambda l: l.move_id == bill)
        if line:
            pass_("vendor_pending_bills", f"lines={len(wiz.line_ids)}")
        else:
            fail("vendor_pending_bills", "sin líneas")
except Exception as exc:  # noqa: BLE001
    fail("vendor_pending_bills", str(exc))

# --- Retenciones múltiples ---
try:
    with env.cr.savepoint():
        wiz = env["hellenia.payment.partner.wizard"].create({
            "partner_type": "supplier",
            "partner_id": vendor.id,
            "journal_id": bnkd.id,
            "wh_itbis_30": True,
            "wh_isr_10": True,
        })
        wiz._recompute_withholdings()
        if len(wiz.withholding_line_ids) >= 1:
            pass_("withholdings_section", f"count={len(wiz.withholding_line_ids)}")
        else:
            fail("withholdings_section", "sin líneas retención")
except Exception as exc:  # noqa: BLE001
    fail("withholdings_section", str(exc))

# --- Métodos de pago español ---
generic = {"Manual Payment", "Checks", "Customer Payments", "Vendor Payments"}
journals = env["account.journal"].search([("type", "in", ["bank", "cash"]), ("active", "=", True)])
methods = set(journals.mapped("inbound_payment_method_line_ids.name") + journals.mapped("outbound_payment_method_line_ids.name"))
bad = methods & generic
if not bad:
    pass_("payment_methods_es", sorted(methods))
else:
    fail("payment_methods_es", str(bad))

for label in ("Transferencia", "Efectivo", "Tarjeta", "Cheque"):
    if label in methods:
        pass_(f"method_{label.lower()}", label)
    else:
        fail(f"method_{label.lower()}", "no encontrado")

# --- Asiento balanceado ---
try:
    with env.cr.savepoint():
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 500})],
        })
        inv.action_post()
        mline = _method_line(bnkd, "Transferencia", "inbound")
        wiz = env["hellenia.payment.partner.wizard"].create({
            "partner_type": "customer",
            "partner_id": customer.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": mline.id if mline else False,
        })
        line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
        line.amount_to_pay = inv.amount_residual
        action = wiz.action_register_payments()
        pay = env["account.payment"].search(action.get("domain", []), limit=1)
        move = pay.move_id
        deb = sum(move.line_ids.mapped("debit"))
        cred = sum(move.line_ids.mapped("credit"))
        if abs(deb - cred) < 0.02:
            pass_("balanced_entry", f"D={deb:.2f} C={cred:.2f}")
        else:
            fail("balanced_entry", f"D={deb} C={cred}")
except Exception as exc:  # noqa: BLE001
    fail("balanced_entry", str(exc))

# --- 606 / 607 smoke ---
try:
    with env.cr.savepoint():
        for rtype, key in (("607", "report_607"), ("606", "report_606")):
            wiz = env["justech.do.fiscal.report.wizard"].create({
                "report_type": rtype,
                "date_from": date.today().replace(month=1, day=1),
                "date_to": date.today(),
            })
            if wiz.action_generate():
                pass_(key, rtype)
            else:
                fail(key, "sin resultado")
except Exception as exc:  # noqa: BLE001
    fail("report_607", str(exc))

# --- Lista pagos: create deshabilitado, botón Nuevo ---
view = env.ref("hellenia_account.view_account_payment_tree_customer_hellenia", raise_if_not_found=False)
if view and 'create="false"' in (view.arch_db or ""):
    pass_("list_create_disabled", "create=false")
else:
    fail("list_create_disabled", "vista no actualizada")

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t.get("status") == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t.get("status") == "FAIL"),
    "total": len(report["tests"]),
}
report["production_ready"] = False

print("PHASE17_4:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
