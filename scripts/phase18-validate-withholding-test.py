#!/usr/bin/env python3
"""Fase 18 — Motor retenciones por factura en wizard de pagos (TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report = {
    "phase": "18-withholding-engine",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
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


def _dgii_period():
    util = env["justech.do.dgii.period"]
    code = util.default_period_code()
    date_from, date_to = util.period_bounds_from_code(code)
    return code, date_from, date_to


mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if mod:
    mod.button_immediate_upgrade()
    env.cr.commit()
    pass_("module_upgrade", mod.latest_version)
else:
    fail("module_upgrade", "hellenia_account no encontrado")

setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
setup.configure_withholding_reference()
env.cr.commit()

Catalog = env["hellenia.withholding.catalog"]
catalogs = {c.code: c for c in Catalog.search([("active", "=", True), ("code", "not in", ("wh_none", "RET-NONE"))])}
if catalogs:
    pass_("catalog_loaded", list(catalogs.keys()))
else:
    fail("catalog_loaded", "sin retenciones activas")


def _cat(*codes):
    for code in codes:
        if code in catalogs:
            return catalogs[code]
    return None

customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_18 = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1)
tax_purchase = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase")], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD")], limit=1)
csh = env["account.journal"].search([("code", "=", "CSH1")], limit=1)


def _method_line(journal, label, ptype="inbound"):
    lines = journal.inbound_payment_method_line_ids if ptype == "inbound" else journal.outbound_payment_method_line_ids
    return lines.filtered(lambda l: l.name == label)[:1]


def _invoice(partner, price=1000, move_type="out_invoice"):
    taxes = tax_18 if move_type.startswith("out") else tax_purchase
    vals = {
        "move_type": move_type,
        "partner_id": partner.id,
        "invoice_line_ids": [Command.create({
            "product_id": product.id,
            "quantity": 1,
            "price_unit": price,
            "tax_ids": [Command.set(taxes.ids)] if taxes else [],
        })],
    }
    if move_type.startswith("in"):
        vals["invoice_date"] = date.today()
    inv = env["account.move"].create(vals)
    inv.action_post()
    return inv


def _wiz(partner, partner_type, journal=None):
    journal = journal or bnkd
    ptype = "inbound" if partner_type == "customer" else "outbound"
    mline = _method_line(journal, "Transferencia", ptype)
    return env["hellenia.payment.partner.wizard"].create({
        "partner_type": partner_type,
        "partner_id": partner.id,
        "journal_id": journal.id,
        "payment_method_line_id": mline.id if mline else False,
    })


def _line_for(wiz, move):
    return wiz.line_ids.filtered(lambda l: l.move_id == move)[:1]


def _pay_line(wiz, line, journal=None):
    journal = journal or wiz.journal_id
    ptype = "inbound" if wiz.partner_type == "customer" else "outbound"
    mline = _method_line(journal, "Transferencia", ptype)
    wiz.write({
        "journal_id": journal.id,
        "payment_method_line_id": mline.id if mline else wiz.payment_method_line_id.id,
    })
    line._recompute_line_withholdings()
    register = env["account.payment.register"].with_context(
        active_model="account.move", active_ids=line.move_id.ids, dont_redirect_to_payments=True
    ).create({
        "journal_id": wiz.journal_id.id,
        "payment_method_line_id": wiz.payment_method_line_id.id,
        "payment_date": date.today(),
        "amount": line.amount_to_pay,
        "hellenia_withholding_line_ids": line._get_withholding_commands_for_register(),
    })
    return register._create_payments()


# 1. Sin retención
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        assert line.withholding_summary == "Ninguna"
        _pay_line(wiz, line)
        if inv.payment_state in ("paid", "in_payment", "partial"):
            pass_("01_no_withholding", inv.payment_state)
        else:
            fail("01_no_withholding", inv.payment_state)
except Exception as exc:  # noqa: BLE001
    fail("01_no_withholding", str(exc))

# 2. Una retención
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, 1000, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cat = _cat("RET-ITBIS-30", "wh_itbis_30")
        if not cat:
            fail("02_single_withholding", "catálogo ITBIS 30 no activo")
        else:
            line.withholding_catalog_ids = [Command.set(cat.ids)]
            line._recompute_line_withholdings()
            assert line.withholding_amount > 0
            _pay_line(wiz, line)
            pass_("02_single_withholding", f"wh={line.withholding_amount:.2f}")
except Exception as exc:  # noqa: BLE001
    fail("02_single_withholding", str(exc))

# 3. Dos retenciones misma factura
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, 1000, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cats = [_cat("RET-ITBIS-30", "wh_itbis_30"), _cat("RET-INF-ISR-10", "wh_isr_10")]
        cats = [c for c in cats if c]
        if len(cats) < 2:
            fail("03_dual_same_invoice", "faltan catálogos")
        else:
            line.withholding_catalog_ids = [Command.set([c.id for c in cats])]
            line._recompute_line_withholdings()
            assert len(line.withholding_detail_ids) >= 2
            _pay_line(wiz, line)
            pass_("03_dual_same_invoice", len(line.withholding_detail_ids))
except Exception as exc:  # noqa: BLE001
    fail("03_dual_same_invoice", str(exc))

# 4. Dos facturas distintas retenciones
try:
    with env.cr.savepoint():
        inv1 = _invoice(vendor, 800, "in_invoice")
        inv2 = _invoice(vendor, 900, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        l1 = _line_for(wiz, inv1)
        l2 = _line_for(wiz, inv2)
        cat30 = _cat("RET-ITBIS-30", "wh_itbis_30")
        if cat30:
            l2.withholding_catalog_ids = [Command.set(cat30.ids)]
            l2._recompute_line_withholdings()
        assert l1.withholding_summary == "Ninguna"
        assert l2.withholding_amount > 0 or not cat30
        for ln in (l1, l2):
            ln.amount_to_pay = ln.move_id.amount_residual
        l1._recompute_line_withholdings()
        _pay_line(wiz, l1)
        _pay_line(wiz, l2)
        pass_("04_mixed_two_invoices", f"{l1.withholding_summary}|{l2.withholding_summary}")
except Exception as exc:  # noqa: BLE001
    fail("04_mixed_two_invoices", str(exc))

# 5. Tres facturas mixtas
try:
    with env.cr.savepoint():
        invs = [_invoice(vendor, 700 + i * 100, "in_invoice") for i in range(3)]
        wiz = _wiz(vendor, "supplier")
        lines = [_line_for(wiz, inv) for inv in invs]
        cat_gov = _cat("RET-GOB-5", "wh_isr_gov")
        cat30 = _cat("RET-ITBIS-30", "wh_itbis_30")
        cat10 = _cat("RET-INF-ISR-10", "wh_isr_10")
        if cat_gov:
            lines[1].withholding_catalog_ids = [Command.set(cat_gov.ids)]
        if cat30 and cat10:
            lines[2].withholding_catalog_ids = [Command.set([cat30.id, cat10.id])]
        for ln in lines:
            ln._recompute_line_withholdings()
            ln.amount_to_pay = ln.move_id.amount_residual
            _pay_line(wiz, ln)
        pass_("05_three_mixed", [ln.withholding_summary for ln in lines])
except Exception as exc:  # noqa: BLE001
    fail("05_three_mixed", str(exc))

# 6. Pago parcial con retención
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 2000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-GOB-5", "wh_isr_gov")
        if cat:
            line.withholding_catalog_ids = [Command.set(cat.ids)]
        line.amount_to_pay = inv.amount_residual / 2
        line._recompute_line_withholdings()
        _pay_line(wiz, line)
        if inv.payment_state == "partial":
            pass_("06_partial_with_wh", inv.payment_state)
        else:
            fail("06_partial_with_wh", inv.payment_state)
except Exception as exc:  # noqa: BLE001
    fail("06_partial_with_wh", str(exc))

# 7. Pago total con retención
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, 1500, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cat = _cat("RET-INF-ISR-10", "wh_isr_10")
        if cat:
            line.withholding_catalog_ids = [Command.set(cat.ids)]
        line.amount_to_pay = inv.amount_residual
        line._recompute_line_withholdings()
        _pay_line(wiz, line)
        if inv.payment_state in ("paid", "in_payment"):
            pass_("07_full_with_wh", inv.payment_state)
        else:
            fail("07_full_with_wh", inv.payment_state)
except Exception as exc:  # noqa: BLE001
    fail("07_full_with_wh", str(exc))

# 8-9 proveedor/cliente
for key, partner, ptype, cat_codes in (
    ("08_vendor_withholding", vendor, "supplier", ("RET-ITBIS-30", "wh_itbis_30")),
    ("09_customer_withholding", customer, "customer", ("RET-GOB-5", "wh_isr_gov")),
):
    try:
        with env.cr.savepoint():
            mt = "in_invoice" if ptype == "supplier" else "out_invoice"
            inv = _invoice(partner, 1000, mt)
            wiz = _wiz(partner, ptype)
            line = _line_for(wiz, inv)
            cat = _cat(*cat_codes) if isinstance(cat_codes, tuple) else _cat(cat_codes)
            if cat:
                line.withholding_catalog_ids = [Command.set(cat.ids)]
            line._recompute_line_withholdings()
            _pay_line(wiz, line)
            pass_(key, line.withholding_summary)
    except Exception as exc:  # noqa: BLE001
        fail(key, str(exc))

# 10-11 reportes 606/607 (período mensual YYYYMM)
try:
    with env.cr.savepoint():
        period_code, date_from, date_to = _dgii_period()
        for rtype, key in (("606", "10_report_606"), ("607", "11_report_607")):
            wiz = env["justech.do.fiscal.report.wizard"].create({
                "report_type": rtype,
                "period_code": period_code,
                "date_from": date_from,
                "date_to": date_to,
            })
            if wiz.action_generate():
                pass_(key, f"{rtype} {period_code}")
            else:
                fail(key, "sin resultado")
except Exception as exc:  # noqa: BLE001
    fail("10_report_606", str(exc))

# 12. Asiento balanceado
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-GOB-5", "wh_isr_gov")
        if cat:
            line.withholding_catalog_ids = [Command.set(cat.ids)]
        line._recompute_line_withholdings()
        pay = _pay_line(wiz, line)
        move = pay.move_id
        deb = sum(move.line_ids.mapped("debit"))
        cred = sum(move.line_ids.mapped("credit"))
        if abs(deb - cred) < 0.02:
            pass_("12_balanced_entry", f"D={deb:.2f}")
        else:
            fail("12_balanced_entry", f"D={deb} C={cred}")
except Exception as exc:  # noqa: BLE001
    fail("12_balanced_entry", str(exc))

# 13. Conciliación smoke
if bnkd and bnkd.bank_account_id:
    pass_("13_reconciliation_ready", bnkd.code)
else:
    fail("13_reconciliation_ready", "BNKD incompleto")

# 14. PDF smoke
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 500)
        html, _ = env["ir.actions.report"]._render_qweb_html("account.account_invoices", inv.ids)
        text = html.decode() if isinstance(html, bytes) else str(html)
        if "Proforma Invoice" not in text:
            pass_("14_pdf_ok", inv.name)
        else:
            fail("14_pdf_ok", "Proforma en PDF")
except Exception as exc:  # noqa: BLE001
    fail("14_pdf_ok", str(exc))

# 15. Wizard RPC / registry
try:
    env["hellenia.payment.partner.wizard"].get_views([(False, "form")])
    w = env["hellenia.payment.partner.wizard"].create({
        "partner_type": "customer",
        "partner_id": customer.id,
        "journal_id": bnkd.id,
    })
    pass_("15_wizard_rpc", w.id)
except Exception as exc:  # noqa: BLE001
    fail("15_wizard_rpc", str(exc))

# UX: Ninguna por defecto
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        if not line.withholding_catalog_ids and line.withholding_summary == "Ninguna":
            pass_("ux_default_none", "Ninguna")
        else:
            fail("ux_default_none", line.withholding_summary)
except Exception as exc:  # noqa: BLE001
    fail("ux_default_none", str(exc))

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t.get("status") == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t.get("status") == "FAIL"),
    "total": len(report["tests"]),
}
report["production_ready"] = False

print("PHASE18:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
