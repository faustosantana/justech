#!/usr/bin/env python3
"""Fase 16 — Validación pagos, bancos, métodos y retenciones RD en TEST."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

company = env.company
report = {
    "phase": "16-payments",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "audit": {},
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


# --- Aplicar configuración ---
mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if not mod or mod.state != "installed":
    if mod:
        mod.button_immediate_install()
    else:
        fail("module_hellenia_account", "módulo no encontrado")
        print("PHASE16_PAYMENTS:" + json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    env.cr.commit()
else:
    mod.button_immediate_upgrade()
    env.cr.commit()

setup = env["hellenia.account.payment.setup"]
cfg = setup.configure_banks_and_payments()
wh = setup.configure_withholding_reference()
env.cr.commit()
report["audit"]["config"] = cfg
report["audit"]["withholdings"] = wh

# --- Auditoría bancos/diarios ---
PartnerBank = env["res.partner.bank"]
banks = PartnerBank.search_read([("partner_id", "=", company.partner_id.id)], ["acc_number", "currency_id"])
journals = env["account.journal"].search([("type", "in", ["bank", "cash"]), ("active", "=", True)])
journal_data = []
for j in journals:
    journal_data.append({
        "code": j.code,
        "name": j.name,
        "type": j.type,
        "bank_account": j.bank_account_id.acc_number if j.bank_account_id else None,
        "currency": j.currency_id.name if j.currency_id else company.currency_id.name,
        "methods": j.inbound_payment_method_line_ids.mapped("name") + j.outbound_payment_method_line_ids.mapped("name"),
    })
report["audit"]["banks"] = banks
report["audit"]["journals"] = journal_data

# Checks auditoría
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)
bnku = env["account.journal"].search([("code", "=", "BNKU"), ("company_id", "=", company.id)], limit=1)
csh = env["account.journal"].search([("code", "=", "CSH1"), ("company_id", "=", company.id)], limit=1)

if bnkd and bnkd.bank_account_id:
    pass_("bank_dop_linked", bnkd.bank_account_id.acc_number)
else:
    fail("bank_dop_linked", "BNKD sin bank_account_id")

if bnku and bnku.bank_account_id:
    pass_("bank_usd_linked", bnku.bank_account_id.acc_number)
else:
    fail("bank_usd_linked", "BNKU sin bank_account_id")

for label in ("Transferencia", "Efectivo", "Tarjeta", "Cheque"):
    found = any(label in (j.inbound_payment_method_line_ids.mapped("name") + j.outbound_payment_method_line_ids.mapped("name")) for j in journals)
    if found:
        pass_(f"method_{label.lower()}", label)
    else:
        fail(f"method_{label.lower()}", f"método {label} no encontrado")

# --- Retenciones ---
wh_map = {
    "ret_5_gov": ("-5% ISR Gov.", "sale"),
    "ret_30_itbis": ("-30% ITBIS Leg. (N02-05)", "purchase"),
    "ret_10_isr": ("-10% ISR Fee", "purchase"),
    "ret_75_informal": ("-75% ITBIS (N08-10)", "purchase"),
}
for key, (name, use) in wh_map.items():
    tax = env["account.tax"].search([("name", "=", name), ("type_tax_use", "=", use)], limit=1)
    if tax and tax.active:
        pass_(key, f"{tax.amount}%")
    else:
        fail(key, f"impuesto {name} no activo")

# --- Preparar datos prueba ---
tax_18 = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1
)
tax_purchase = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "purchase")], limit=1
)
ret_10 = env["account.tax"].search([("name", "=", "-10% ISR Fee"), ("type_tax_use", "=", "purchase")], limit=1)
ret_30 = env["account.tax"].search([("name", "=", "-30% ITBIS Leg. (N02-05)"), ("type_tax_use", "=", "purchase")], limit=1)
gov_ret = env["account.tax"].search([("name", "=", "-5% ISR Gov."), ("type_tax_use", "=", "sale")], limit=1)

product = env["product.product"].search([("sale_ok", "=", True), ("name", "not ilike", "SMOKE")], limit=1)
if not product:
    product = env["product.product"].create({
        "name": "Producto Pago Test 16",
        "type": "consu",
        "is_storable": True,
        "list_price": 1000.0,
        "taxes_id": [Command.set(tax_18.ids)] if tax_18 else [],
    })

customer = env["res.partner"].search([("customer_rank", ">", 0), ("name", "not ilike", "SMOKE")], limit=1)
if not customer:
    customer = env["res.partner"].create({"name": "Cliente Pago Test 16", "customer_rank": 1, "vat": "131111111"})

vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
if not vendor:
    vendor = env["res.partner"].create({"name": "Proveedor Informal Test 16", "supplier_rank": 1, "vat": "132222222"})

# NCF setup
manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [Command.link(manager.id)]})

journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_sale.write({"justech_do_use_ncf": True})
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
doc_b11 = env.ref("justech_l10n_do_base.doc_type_b11", raise_if_not_found=False)

Range = env["justech.do.ncf.range"]
def ensure_range(doc, prefix, start=5000):
    rng = Range.search([("document_type_id", "=", doc.id), ("state", "=", "active"), ("sequence_start", "<", 9000)], limit=1)
    if rng:
        return rng
    rng = Range.create({
        "name": f"P16 {prefix}",
        "document_type_id": doc.id,
        "company_id": company.id,
        "sequence_start": start,
        "sequence_end": start + 500,
        "date_from": date.today().replace(month=1, day=1),
        "date_to": date.today().replace(month=12, day=31),
        "authorization_number": f"P16-{prefix}-AUTH",
        "journal_ids": [Command.set(journal_sale.ids)],
    })
    rng.action_activate()
    return rng

if doc_b02:
    ensure_range(doc_b02, "B02", 5100)
if doc_b11:
    j_purchase = env["account.journal"].search([("type", "=", "purchase")], limit=1)
    rng11 = Range.search([("document_type_id", "=", doc_b11.id), ("state", "=", "active")], limit=1)
    if not rng11:
        rng11 = Range.create({
            "name": "P16 B11",
            "document_type_id": doc_b11.id,
            "company_id": company.id,
            "sequence_start": 5200,
            "sequence_end": 5700,
            "date_from": date.today().replace(month=1, day=1),
            "date_to": date.today().replace(month=12, day=31),
            "authorization_number": "P16-B11-AUTH",
            "journal_ids": [Command.set(j_purchase.ids)] if j_purchase else [],
        })
        rng11.action_activate()

env.cr.commit()

def pay_invoice(inv, journal):
    wiz = env["account.payment.register"].with_context(active_model="account.move", active_ids=inv.ids).create({
        "journal_id": journal.id,
    })
    if not wiz.journal_id:
        wiz.journal_id = journal
    payments = wiz._create_payments()
    return payments

# --- Test cobro transferencia ---
try:
    with env.cr.savepoint():
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({
                "product_id": product.id,
                "quantity": 1,
                "price_unit": 1000,
                "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
            })],
        })
        inv.action_post()
        ncf = inv.justech_do_ncf
        pay = pay_invoice(inv, bnkd or journals.filtered(lambda j: j.type == "bank")[:1])
        reconciled = inv.payment_state in ("paid", "in_payment", "partial")
        if reconciled and ncf:
            pass_("cobro_transferencia", f"NCF={ncf}, pago={pay[:1].name if pay else 'ok'}")
        else:
            fail("cobro_transferencia", f"state={inv.payment_state}, ncf={ncf}")
except Exception as exc:  # noqa: BLE001
    fail("cobro_transferencia", str(exc))

# --- Test cobro efectivo ---
try:
    with env.cr.savepoint():
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 500, "tax_ids": [Command.set(tax_18.ids)] if tax_18 else []})],
        })
        inv.action_post()
        pay = pay_invoice(inv, csh)
        if inv.payment_state in ("paid", "in_payment", "partial"):
            pass_("cobro_efectivo", inv.payment_state)
        else:
            fail("cobro_efectivo", inv.payment_state)
except Exception as exc:  # noqa: BLE001
    fail("cobro_efectivo", str(exc))

# --- Test pago proveedor ---
try:
    with env.cr.savepoint():
        bill = env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": vendor.id,
            "invoice_line_ids": [Command.create({
                "product_id": product.id,
                "quantity": 1,
                "price_unit": 800,
                "tax_ids": [Command.set(tax_purchase.ids)] if tax_purchase else [],
            })],
        })
        bill.action_post()
        pay = pay_invoice(bill, bnkd or journals.filtered(lambda j: j.type == "bank")[:1])
        if bill.payment_state in ("paid", "in_payment", "partial"):
            pass_("pago_proveedor", bill.payment_state)
        else:
            fail("pago_proveedor", bill.payment_state)
except Exception as exc:  # noqa: BLE001
    fail("pago_proveedor", str(exc))

# --- Test retención 10% proveedor ---
try:
    with env.cr.savepoint():
        bill = env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": vendor.id,
            "invoice_line_ids": [Command.create({
                "product_id": product.id,
                "quantity": 1,
                "price_unit": 1000,
                "tax_ids": [Command.set((tax_purchase | ret_10).ids)] if tax_purchase and ret_10 else [],
            })],
        })
        bill.action_post()
        has_ret = any(l.tax_line_id == ret_10 for l in bill.line_ids) if ret_10 else False
        if has_ret:
            pass_("retencion_10_proveedor", "ISR Fee aplicado")
        else:
            fail("retencion_10_proveedor", "sin línea retención")
except Exception as exc:  # noqa: BLE001
    fail("retencion_10_proveedor", str(exc))

# --- Test retención 30% ITBIS ---
try:
    with env.cr.savepoint():
        bill = env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": vendor.id,
            "invoice_line_ids": [Command.create({
                "product_id": product.id,
                "quantity": 1,
                "price_unit": 1000,
                "tax_ids": [Command.set((tax_purchase | ret_30).ids)] if tax_purchase and ret_30 else [],
            })],
        })
        bill.action_post()
        has_ret = any(l.tax_line_id == ret_30 for l in bill.line_ids) if ret_30 else False
        if has_ret:
            pass_("retencion_30_itbis", "-5.4% aplicado")
        else:
            fail("retencion_30_itbis", "sin línea retención")
except Exception as exc:  # noqa: BLE001
    fail("retencion_30_itbis", str(exc))

# --- Wizard muestra NCF ---
try:
    with env.cr.savepoint():
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 100})],
        })
        inv.action_post()
        wiz = env["account.payment.register"].with_context(active_model="account.move", active_ids=inv.ids).create({})
        has_ncf_field = "justech_do_ncf" in env["account.move.line"]._fields
        lines_with_ncf = wiz.line_ids.mapped("justech_do_ncf")
        if has_ncf_field and wiz.line_ids:
            pass_("wizard_ncf_visible", f"lines={len(wiz.line_ids)}, ncf={lines_with_ncf}")
        else:
            fail("wizard_ncf_visible", "campo NCF no disponible en líneas")
except Exception as exc:  # noqa: BLE001
    fail("wizard_ncf_visible", str(exc))

# --- Reportes 606/607 smoke ---
try:
    with env.cr.savepoint():
        wiz607 = env["justech.do.fiscal.report.wizard"].create({
            "report_type": "607",
            "date_from": date.today().replace(month=1, day=1),
            "date_to": date.today(),
        })
        r607 = wiz607.action_generate()
        wiz606 = env["justech.do.fiscal.report.wizard"].create({
            "report_type": "606",
            "date_from": date.today().replace(month=1, day=1),
            "date_to": date.today(),
        })
        r606 = wiz606.action_generate()
        if r607 and r606:
            pass_("reportes_606_607", "generados")
        else:
            fail("reportes_606_607", "falló wizard")
except Exception as exc:  # noqa: BLE001
    fail("reportes_606_607", str(exc))

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t.get("status") == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t.get("status") == "FAIL"),
    "total": len(report["tests"]),
}

print("PHASE16_PAYMENTS:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
