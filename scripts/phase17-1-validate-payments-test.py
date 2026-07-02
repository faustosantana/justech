#!/usr/bin/env python3
"""Fase 17.1 — Pagos desde menú, retenciones en pago y PDF factura (TEST)."""
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
    "phase": "17.1-payments-pdf",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "El menú Contabilidad → Clientes/Proveedores → Pagos abría account.payment "
        "sin wizard de registro; al crear un pago vacío no se cargaban facturas pendientes. "
        "Solo el flujo factura → Pagar usaba account.payment.register."
    ),
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


# --- Instalar/actualizar módulos ---
for mod_name in ("hellenia_account", "hellenia_reports", "hellenia_ux"):
    mod = env["ir.module.module"].search([("name", "=", mod_name)], limit=1)
    if not mod:
        fail(f"module_{mod_name}", "no encontrado")
        continue
    if mod.state != "installed":
        mod.button_immediate_install()
    else:
        mod.button_immediate_upgrade()
    env.cr.commit()
    pass_(f"module_{mod_name}", mod.state)

setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
setup.configure_withholding_reference()
env["hellenia.ui.menu.customizer"].apply_all()
company.write({"hellenia_show_qr_on_invoice": False})
env.cr.commit()

bnkd = env["account.journal"].search([("code", "=", "BNKD")], limit=1)
bnku = env["account.journal"].search([("code", "=", "BNKU")], limit=1)
csh = env["account.journal"].search([("code", "=", "CSH1")], limit=1)
tax_18 = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1)
tax_purchase = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase")], limit=1)
gov_ret = env["account.tax"].search([("name", "=", "-5% ISR Gov."), ("type_tax_use", "=", "sale")], limit=1)
ret_10 = env["account.tax"].search([("name", "=", "-10% ISR Fee"), ("type_tax_use", "=", "purchase")], limit=1)
ret_30 = env["account.tax"].search([("name", "=", "-30% ITBIS Leg. (N02-05)"), ("type_tax_use", "=", "purchase")], limit=1)
ret_75 = env["account.tax"].search([("name", "=", "-75% ITBIS (N08-10)"), ("type_tax_use", "=", "purchase")], limit=1)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)

tag = f"P171-{date.today().strftime('%m%d')}"
customer = env["res.partner"].search([("name", "ilike", tag), ("customer_rank", ">", 0)], limit=1)
if not customer:
    customer = env["res.partner"].create({"name": f"Cliente {tag}", "customer_rank": 1, "vat": "131313131"})
vendor = env["res.partner"].search([("name", "ilike", tag), ("supplier_rank", ">", 0)], limit=1)
if not vendor:
    vendor = env["res.partner"].create({"name": f"Proveedor {tag}", "supplier_rank": 1, "vat": "132323232"})

manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [Command.link(manager.id)]})

journal_sale = env["account.journal"].search([("type", "=", "sale")], limit=1)
journal_sale.write({"justech_do_use_ncf": True})
doc_b01 = env.ref("justech_l10n_do_base.doc_type_b01", raise_if_not_found=False)
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
doc_b11 = env.ref("justech_l10n_do_base.doc_type_b11", raise_if_not_found=False)
Range = env["justech.do.ncf.range"]


def ensure_range(doc, start=7000):
    rng = Range.search([("document_type_id", "=", doc.id), ("state", "=", "active")], limit=1)
    if rng:
        return rng
    rng = Range.create({
        "name": f"P171 {doc.prefix}",
        "document_type_id": doc.id,
        "company_id": company.id,
        "sequence_start": start,
        "sequence_end": start + 300,
        "date_from": date.today().replace(month=1, day=1),
        "date_to": date.today().replace(month=12, day=31),
        "authorization_number": f"P171-{doc.prefix}",
        "journal_ids": [Command.set(journal_sale.ids)],
    })
    rng.action_activate()
    return rng


if doc_b01:
    ensure_range(doc_b01, 7100)
if doc_b02:
    ensure_range(doc_b02, 7200)
if doc_b04:
    ensure_range(doc_b04, 7300)
if doc_b11:
    j_purchase = env["account.journal"].search([("type", "=", "purchase")], limit=1)
    rng11 = Range.search([("document_type_id", "=", doc_b11.id), ("state", "=", "active")], limit=1)
    if not rng11:
        rng11 = Range.create({
            "name": "P171 B11",
            "document_type_id": doc_b11.id,
            "company_id": company.id,
            "sequence_start": 7400,
            "sequence_end": 7700,
            "date_from": date.today().replace(month=1, day=1),
            "date_to": date.today().replace(month=12, day=31),
            "authorization_number": "P171-B11",
            "journal_ids": [Command.set(j_purchase.ids)] if j_purchase else [],
        })
        rng11.action_activate()

env.cr.commit()


def _method_line(journal, label, payment_type="inbound"):
    lines = journal.inbound_payment_method_line_ids if payment_type == "inbound" else journal.outbound_payment_method_line_ids
    return lines.filtered(lambda l: l.name == label)[:1]


def _make_customer_invoices(count=3, price=1000):
    moves = env["account.move"]
    for i in range(count):
        moves |= env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({
                "product_id": product.id,
                "quantity": 1,
                "price_unit": price + i * 100,
                "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
            })],
        })
    moves.action_post()
    return moves


def _make_vendor_bills(count=3, price=800):
    moves = env["account.move"]
    for i in range(count):
        moves |= env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": vendor.id,
            "invoice_date": date.today(),
            "invoice_line_ids": [Command.create({
                "product_id": product.id,
                "quantity": 1,
                "price_unit": price + i * 50,
                "tax_ids": [Command.set(tax_purchase.ids)] if tax_purchase else [],
            })],
        })
    moves.action_post()
    return moves


def _partner_wizard(partner, partner_type, journal, method_label, **extra):
    ptype = "inbound" if partner_type == "customer" else "outbound"
    mline = _method_line(journal, method_label, ptype)
    wiz = env["hellenia.payment.partner.wizard"].create({
        "partner_type": partner_type,
        "partner_id": partner.id,
        "journal_id": journal.id,
        "payment_method_line_id": mline.id if mline else False,
        **extra,
    })
    return wiz


# 1. Cliente con 3 facturas pendientes en wizard
try:
    with env.cr.savepoint():
        invs = _make_customer_invoices(3)
        wiz = _partner_wizard(customer, "customer", bnkd, "Transferencia")
        pending = wiz.line_ids.filtered(lambda l: l.move_id in invs)
        if len(pending) >= 3:
            pass_("01_customer_3_pending", f"lines={len(wiz.line_ids)}")
        else:
            fail("01_customer_3_pending", f"solo {len(pending)} de 3")
except Exception as exc:  # noqa: BLE001
    fail("01_customer_3_pending", str(exc))

# 2. Proveedor con 3 facturas pendientes
try:
    with env.cr.savepoint():
        bills = _make_vendor_bills(3)
        wiz = _partner_wizard(vendor, "supplier", bnkd, "Transferencia")
        pending = wiz.line_ids.filtered(lambda l: l.move_id in bills)
        if len(pending) >= 3:
            pass_("02_vendor_3_pending", f"lines={len(wiz.line_ids)}")
        else:
            fail("02_vendor_3_pending", f"solo {len(pending)}")
except Exception as exc:  # noqa: BLE001
    fail("02_vendor_3_pending", str(exc))

# 3. Pago parcial
try:
    with env.cr.savepoint():
        inv = _make_customer_invoices(1, 2000)[0]
        wiz = _partner_wizard(customer, "customer", bnkd, "Transferencia")
        line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
        line.apply = True
        line.amount_to_pay = inv.amount_residual / 2
        wiz.action_register_payments()
        if inv.payment_state == "partial":
            pass_("03_partial_payment", f"residual={inv.amount_residual:.2f}")
        else:
            fail("03_partial_payment", inv.payment_state)
except Exception as exc:  # noqa: BLE001
    fail("03_partial_payment", str(exc))

# 4. Pago total
try:
    with env.cr.savepoint():
        inv = _make_customer_invoices(1, 1500)[0]
        wiz = _partner_wizard(customer, "customer", csh, "Efectivo")
        line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
        line.amount_to_pay = inv.amount_residual
        wiz.action_register_payments()
        if inv.payment_state in ("paid", "in_payment"):
            pass_("04_full_payment", inv.payment_state)
        else:
            fail("04_full_payment", inv.payment_state)
except Exception as exc:  # noqa: BLE001
    fail("04_full_payment", str(exc))

# 5. Pago múltiple
try:
    with env.cr.savepoint():
        invs = _make_customer_invoices(2, 500)
        wiz = _partner_wizard(customer, "customer", bnkd, "Transferencia")
        for inv in invs:
            line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
            line.apply = True
            line.amount_to_pay = inv.amount_residual
        wiz.action_register_payments()
        if all(i.payment_state in ("paid", "in_payment") for i in invs):
            pass_("05_multi_payment", invs.mapped("name"))
        else:
            fail("05_multi_payment", invs.mapped("payment_state"))
except Exception as exc:  # noqa: BLE001
    fail("05_multi_payment", str(exc))

# 6-9 métodos de pago
for key, journal, method, ptype, partner, mk in (
    ("06_transfer", bnkd, "Transferencia", "customer", customer, _make_customer_invoices),
    ("07_cash", csh, "Efectivo", "customer", customer, _make_customer_invoices),
    ("08_card", bnkd, "Tarjeta", "customer", customer, _make_customer_invoices),
    ("09_check", bnkd, "Cheque", "supplier", vendor, _make_vendor_bills),
):
    try:
        with env.cr.savepoint():
            doc = mk(1, 900)[0]
            wiz = _partner_wizard(partner, ptype, journal, method)
            line = wiz.line_ids.filtered(lambda l: l.move_id == doc)[:1]
            line.amount_to_pay = doc.amount_residual
            wiz.action_register_payments()
            if doc.payment_state in ("paid", "in_payment", "partial"):
                pass_(key, doc.payment_state)
            else:
                fail(key, doc.payment_state)
    except Exception as exc:  # noqa: BLE001
        fail(key, str(exc))

# 10. Retención 5% en pago cliente
try:
    with env.cr.savepoint():
        inv = _make_customer_invoices(1, 1000)[0]
        wiz = _partner_wizard(customer, "customer", bnkd, "Transferencia", wh_isr_gov=True)
        wiz._recompute_withholdings()
        if wiz.withholding_line_ids and wiz.withholding_total > 0:
            line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
            line.amount_to_pay = inv.amount_residual
            wiz.action_register_payments()
            pass_("10_wh_5_gov", f"wh={wiz.withholding_total:.2f}")
        else:
            fail("10_wh_5_gov", "sin líneas retención")
except Exception as exc:  # noqa: BLE001
    fail("10_wh_5_gov", str(exc))

# 11. Retención ITBIS 30%
try:
    with env.cr.savepoint():
        bill = _make_vendor_bills(1, 1000)[0]
        wiz = _partner_wizard(vendor, "supplier", bnkd, "Transferencia", wh_itbis_30=True)
        wiz._recompute_withholdings()
        if wiz.withholding_line_ids:
            line = wiz.line_ids.filtered(lambda l: l.move_id == bill)[:1]
            line.amount_to_pay = bill.amount_residual
            wiz.action_register_payments()
            pass_("11_wh_30_itbis", f"wh={wiz.withholding_total:.2f}")
        else:
            fail("11_wh_30_itbis", "sin retención")
except Exception as exc:  # noqa: BLE001
    fail("11_wh_30_itbis", str(exc))

# 12. Retención proveedor informal 10%
try:
    with env.cr.savepoint():
        bill = _make_vendor_bills(1, 1000)[0]
        wiz = _partner_wizard(vendor, "supplier", bnkd, "Transferencia", wh_isr_10=True)
        wiz._recompute_withholdings()
        if wiz.withholding_line_ids:
            line = wiz.line_ids.filtered(lambda l: l.move_id == bill)[:1]
            line.amount_to_pay = bill.amount_residual
            wiz.action_register_payments()
            pass_("12_wh_10_informal", f"wh={wiz.withholding_total:.2f}")
        else:
            fail("12_wh_10_informal", "sin retención")
except Exception as exc:  # noqa: BLE001
    fail("12_wh_10_informal", str(exc))

# 13. Dos retenciones misma factura
try:
    with env.cr.savepoint():
        bill = _make_vendor_bills(1, 1000)[0]
        wiz = _partner_wizard(
            vendor, "supplier", bnkd, "Transferencia", wh_itbis_30=True, wh_isr_10=True
        )
        wiz._recompute_withholdings()
        if len(wiz.withholding_line_ids) >= 2:
            line = wiz.line_ids.filtered(lambda l: l.move_id == bill)[:1]
            line.amount_to_pay = bill.amount_residual
            wiz.action_register_payments()
            pass_("13_dual_withholding", f"count={len(wiz.withholding_line_ids)}")
        else:
            fail("13_dual_withholding", f"solo {len(wiz.withholding_line_ids)}")
except Exception as exc:  # noqa: BLE001
    fail("13_dual_withholding", str(exc))

# 14. Asiento balanceado (smoke)
try:
    with env.cr.savepoint():
        inv = _make_customer_invoices(1, 500)[0]
        wiz = _partner_wizard(customer, "customer", bnkd, "Transferencia")
        line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
        line.amount_to_pay = inv.amount_residual
        action = wiz.action_register_payments()
        pay = env["account.payment"].search(action.get("domain", []), limit=1)
        move = pay.move_id
        deb = sum(move.line_ids.mapped("debit"))
        cred = sum(move.line_ids.mapped("credit"))
        if abs(deb - cred) < 0.02:
            pass_("14_balanced_entry", f"D={deb:.2f} C={cred:.2f}")
        else:
            fail("14_balanced_entry", f"D={deb} C={cred}")
except Exception as exc:  # noqa: BLE001
    fail("14_balanced_entry", str(exc))

# 15. Conciliación smoke
if bnkd and bnkd.bank_account_id and bnkd.inbound_payment_method_line_ids:
    pass_("15_reconciliation_ready", bnkd.code)
else:
    fail("15_reconciliation_ready", "BNKD incompleto")

# 16-17. 606 / 607
try:
    with env.cr.savepoint():
        for rtype, key in (("607", "16_report_607"), ("606", "17_report_606")):
            wiz = env["justech.do.fiscal.report.wizard"].create({
                "report_type": rtype,
                "date_from": date.today().replace(month=1, day=1),
                "date_to": date.today(),
            })
            result = wiz.action_generate()
            if result:
                pass_(key, rtype)
            else:
                fail(key, "sin resultado")
except Exception as exc:  # noqa: BLE001
    fail("16_report_607", str(exc))

# 18. PDF factura B01
try:
    with env.cr.savepoint():
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 1000})],
        })
        inv.action_post()
        html, _ = env["ir.actions.report"]._render_qweb_html("account.account_invoices", inv.ids)
        text = html.decode() if isinstance(html, bytes) else str(html)
        title_ok = "FACTURA DE CRÉDITO FISCAL" in text or inv.hellenia_fiscal_document_title() in text
        no_qr = "qr" not in text.lower() or "hellenia-qr" not in text.lower()
        no_proforma = "Proforma Invoice" not in text
        ncf_ok = "Número de Comprobante Fiscal" in text
        if title_ok and no_proforma and ncf_ok:
            pass_("18_pdf_invoice", inv.justech_do_ncf or inv.name)
        else:
            fail("18_pdf_invoice", f"title={title_ok} proforma={no_proforma} ncf={ncf_ok}")
except Exception as exc:  # noqa: BLE001
    fail("18_pdf_invoice", str(exc))

# 19. PDF nota de crédito
try:
    with env.cr.savepoint():
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 500})],
        })
        inv.action_post()
        nc = env["account.move"].create({
            "move_type": "out_refund",
            "partner_id": customer.id,
            "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 500})],
        })
        nc.action_post()
        html, _ = env["ir.actions.report"]._render_qweb_html("account.account_invoices", nc.ids)
        text = html.decode() if isinstance(html, bytes) else str(html)
        if "NOTA DE CRÉDITO" in text and "Proforma Invoice" not in text:
            pass_("19_pdf_credit_note", nc.name)
        else:
            fail("19_pdf_credit_note", "título incorrecto")
except Exception as exc:  # noqa: BLE001
    fail("19_pdf_credit_note", str(exc))

# 20. PDF B02 consumo
try:
    with env.cr.savepoint():
        cons = env["res.partner"].create({"name": f"Consumo {tag}", "customer_rank": 1})
        inv = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": cons.id,
            "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 300})],
        })
        inv.action_post()
        note = inv.hellenia_ncf_legal_note()
        title = inv.hellenia_fiscal_document_title()
        if "consumo" in note.lower() or title == "FACTURA DE CONSUMO":
            pass_("20_pdf_b02_consumption", f"title={title}")
        else:
            fail("20_pdf_b02_consumption", f"title={title} note={note}")
except Exception as exc:  # noqa: BLE001
    fail("20_pdf_b02_consumption", str(exc))

# UI: acción wizard en menú pagos
wiz_action = env.ref("hellenia_account.action_hellenia_register_customer_payment", raise_if_not_found=False)
if wiz_action and wiz_action.res_model == "hellenia.payment.partner.wizard":
    pass_("wizard_action_customer", wiz_action.name)
else:
    fail("wizard_action_customer", "acción no encontrada")

# Métodos genéricos no visibles
generic = {"Manual Payment", "Checks", "Customer Payments", "Vendor Payments"}
journals = env["account.journal"].search([("type", "in", ["bank", "cash"]), ("active", "=", True)])
all_methods = set(journals.mapped("inbound_payment_method_line_ids.name") + journals.mapped("outbound_payment_method_line_ids.name"))
bad = all_methods & generic
if not bad:
    pass_("payment_methods_spanish", sorted(all_methods))
else:
    fail("payment_methods_spanish", str(bad))

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t.get("status") == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t.get("status") == "FAIL"),
    "total": len(report["tests"]),
}
report["production_ready"] = False

print("PHASE17_1:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
