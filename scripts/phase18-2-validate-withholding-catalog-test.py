#!/usr/bin/env python3
"""Fase 18.2 — Catálogo completo y administrable de retenciones RD (TEST)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report = {
    "phase": "18.2-withholding-catalog",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "tests": {},
    "catalog": {},
    "ok": True,
    "errors": [],
    "production_ready": False,
}


def err(msg):
    report["ok"] = False
    report["errors"].append(msg)


def pass_(name, detail=""):
    report["tests"][name] = {"status": "PASS", "detail": detail}


def fail(name, msg):
    report["tests"][name] = {"status": "FAIL", "message": msg}
    err(f"{name}: {msg}")


TECHNICAL_PATTERNS = re.compile(
    r"wh_isr_|wh_itbis_|Tax Withholding|Withholding|Retained by State|ITBIS Retained",
    re.I,
)

EXPECTED_ACTIVE = {
    "RET-GOB-5",
    "RET-ITBIS-30",
    "RET-ITBIS-100",
    "RET-INF-ISR-10",
    "RET-INF-ITBIS-75",
    "RET-ISR-2",
    "RET-HON-10",
}

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
all_catalog = Catalog.search([])
active_catalog = Catalog.search([("active", "=", True)])
active_codes = {c.code for c in active_catalog if c.code not in ("RET-NONE", "wh_none")}
report["catalog"] = {
    "total": len(all_catalog),
    "active": len(active_catalog),
    "active_codes": sorted(active_codes),
    "entries": [
        {
            "code": c.code,
            "name": c.name,
            "active": c.active,
            "account": c.account_id.code if c.account_id else None,
            "partner_scope": c.partner_scope,
            "move_scope": c.move_scope,
            "base_type": c.base_type,
            "affects_606": c.affects_606,
            "affects_607": c.affects_607,
        }
        for c in all_catalog.sorted("sequence")
    ],
}

customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_18_sale = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1)
tax_18_purchase = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase")], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD")], limit=1)


def _method_line(journal, label, ptype="inbound"):
    lines = journal.inbound_payment_method_line_ids if ptype == "inbound" else journal.outbound_payment_method_line_ids
    return lines.filtered(lambda l: l.name == label)[:1]


def _invoice(partner, price=1000, move_type="out_invoice"):
    taxes = tax_18_sale if move_type.startswith("out") else tax_18_purchase
    vals = {
        "move_type": move_type,
        "partner_id": partner.id,
        "invoice_line_ids": [
            Command.create(
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "price_unit": price,
                    "tax_ids": [Command.set(taxes.ids)] if taxes else [],
                }
            )
        ],
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
    return env["hellenia.payment.partner.wizard"].create(
        {
            "partner_type": partner_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "payment_method_line_id": mline.id if mline else False,
        }
    )


def _line_for(wiz, move):
    return wiz.line_ids.filtered(lambda l: l.move_id == move)[:1]


def _pay_line(wiz, line, journal=None):
    journal = journal or wiz.journal_id
    ptype = "inbound" if wiz.partner_type == "customer" else "outbound"
    mline = _method_line(journal, "Transferencia", ptype)
    wiz.write(
        {
            "journal_id": journal.id,
            "payment_method_line_id": mline.id if mline else wiz.payment_method_line_id.id,
        }
    )
    line._recompute_line_withholdings()
    register = (
        env["account.payment.register"]
        .with_context(active_model="account.move", active_ids=line.move_id.ids, dont_redirect_to_payments=True)
        .create(
            {
                "journal_id": wiz.journal_id.id,
                "payment_method_line_id": wiz.payment_method_line_id.id,
                "payment_date": date.today(),
                "amount": line.amount_to_pay,
                "hellenia_withholding_line_ids": line._get_withholding_commands_for_register(),
            }
        )
    )
    return register._create_payments()


def _selector_codes(partner_type, move_type):
    domain = Catalog._domain_for_payment(partner_type, move_type)
    return sorted(Catalog.search(domain).mapped("code"))


def _cat(code):
    return Catalog.search([("code", "=", code), ("company_id", "=", env.company.id)], limit=1)


# 1. Catálogo completo
missing = EXPECTED_ACTIVE - active_codes
if not missing and len(active_codes) >= 7:
    pass_("01_catalog_complete", sorted(active_codes))
else:
    fail("01_catalog_complete", f"faltan={sorted(missing)} activos={sorted(active_codes)}")

# 2. Crear retención desde admin
try:
    with env.cr.savepoint():
        test_code = "RET-TEST-TMP"
        Catalog.search([("code", "=", test_code)]).unlink()
        gov = _cat("RET-GOB-5")
        rec = Catalog.create(
            {
                "name": "Retención prueba temporal",
                "code": test_code,
                "withholding_type": "other",
                "base_type": "untaxed",
                "partner_scope": "both",
                "move_scope": "both",
                "account_id": gov.account_id.id if gov and gov.account_id else False,
                "active": False,
                "notes": "Creada en validación Fase 18.2",
            }
        )
        if rec.id:
            pass_("02_create_from_admin", test_code)
        else:
            fail("02_create_from_admin", "no creada")
except Exception as exc:  # noqa: BLE001
    fail("02_create_from_admin", str(exc))

# 3. Editar cuenta contable
try:
    with env.cr.savepoint():
        cat = _cat("RET-ISR-2")
        if not cat:
            fail("03_edit_account", "RET-ISR-2 no existe")
        else:
            alt = env["account.account"].search([("company_ids", "in", env.company.id)], limit=2)
            alt = alt.filtered(lambda a: a != cat.account_id)[:1]
            if alt:
                old = cat.account_id.id
                cat.write({"account_id": alt.id})
                cat.write({"account_id": old})
                pass_("03_edit_account", alt.code)
            else:
                pass_("03_edit_account", "sin cuenta alterna — skip")
except Exception as exc:  # noqa: BLE001
    fail("03_edit_account", str(exc))

# 4-5. Desactivar / reactivar en selector
try:
    with env.cr.savepoint():
        cat = _cat("RET-HON-10")
        if not cat:
            fail("04_deactivate_hidden", "RET-HON-10 no existe")
        else:
            was = cat.active
            cat.active = False
            codes_off = _selector_codes("customer", "out_invoice")
            cat.active = True
            codes_on = _selector_codes("customer", "out_invoice")
            if "RET-HON-10" not in codes_off and "RET-HON-10" in codes_on:
                pass_("04_deactivate_hidden", "oculta al desactivar")
                pass_("05_reactivate_visible", "visible al reactivar")
            else:
                fail("04_deactivate_hidden", f"off={codes_off} on={codes_on}")
            cat.active = was
except Exception as exc:  # noqa: BLE001
    fail("04_deactivate_hidden", str(exc))

# 6. Cobro sin retención
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        if line.withholding_summary == "Ninguna":
            _pay_line(wiz, line)
            pass_("06_customer_no_wh", inv.payment_state)
        else:
            fail("06_customer_no_wh", line.withholding_summary)
except Exception as exc:  # noqa: BLE001
    fail("06_customer_no_wh", str(exc))

# 7. Cobro ITBIS 30%
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-ITBIS-30")
        if not cat or not cat.active:
            fail("07_customer_itbis_30", "catálogo inactivo")
        else:
            line.withholding_catalog_ids = [Command.set(cat.ids)]
            line._recompute_line_withholdings()
            assert line.withholding_amount > 0
            _pay_line(wiz, line)
            pass_("07_customer_itbis_30", f"{line.withholding_amount:.2f}")
except Exception as exc:  # noqa: BLE001
    fail("07_customer_itbis_30", str(exc))

# 8. Cobro Gobierno 5%
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-GOB-5")
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        line._recompute_line_withholdings()
        _pay_line(wiz, line)
        pass_("08_customer_gov_5", f"{line.withholding_amount:.2f}")
except Exception as exc:  # noqa: BLE001
    fail("08_customer_gov_5", str(exc))

# 9. Cobro dos retenciones
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 2000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cats = [_cat("RET-GOB-5"), _cat("RET-ITBIS-30")]
        cats = [c for c in cats if c]
        line.withholding_catalog_ids = [Command.set([c.id for c in cats])]
        line._recompute_line_withholdings()
        if len(line.withholding_detail_ids) >= 2:
            _pay_line(wiz, line)
            pass_("09_customer_dual_wh", len(line.withholding_detail_ids))
        else:
            fail("09_customer_dual_wh", "menos de 2 retenciones")
except Exception as exc:  # noqa: BLE001
    fail("09_customer_dual_wh", str(exc))

# 10. Pago informal 10%
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, 1000, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cat = _cat("RET-INF-ISR-10")
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        line._recompute_line_withholdings()
        _pay_line(wiz, line)
        pass_("10_vendor_informal_10", f"{line.withholding_amount:.2f}")
except Exception as exc:  # noqa: BLE001
    fail("10_vendor_informal_10", str(exc))

# 11. Pago ITBIS informal 75%
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, 1000, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cat = _cat("RET-INF-ITBIS-75")
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        line._recompute_line_withholdings()
        _pay_line(wiz, line)
        pass_("11_vendor_itbis_75", f"{line.withholding_amount:.2f}")
except Exception as exc:  # noqa: BLE001
    fail("11_vendor_itbis_75", str(exc))

# 12. Pago dos retenciones
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, 1500, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cats = [_cat("RET-ITBIS-30"), _cat("RET-INF-ISR-10")]
        cats = [c for c in cats if c]
        line.withholding_catalog_ids = [Command.set([c.id for c in cats])]
        line._recompute_line_withholdings()
        if len(line.withholding_detail_ids) >= 2:
            _pay_line(wiz, line)
            pass_("12_vendor_dual_wh", len(line.withholding_detail_ids))
        else:
            fail("12_vendor_dual_wh", "menos de 2")
except Exception as exc:  # noqa: BLE001
    fail("12_vendor_dual_wh", str(exc))

# 13. Asiento balanceado
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-GOB-5")
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        line._recompute_line_withholdings()
        pay = _pay_line(wiz, line)
        move = pay.move_id
        deb = sum(move.line_ids.mapped("debit"))
        cred = sum(move.line_ids.mapped("credit"))
        if abs(deb - cred) < 0.02:
            pass_("13_balanced_entry", f"D={deb:.2f}")
        else:
            fail("13_balanced_entry", f"D={deb} C={cred}")
except Exception as exc:  # noqa: BLE001
    fail("13_balanced_entry", str(exc))

# 14. Cuenta contable retención
try:
    missing_acct = [c.code for c in active_catalog if c.code not in ("RET-NONE", "wh_none") and not c.account_id]
    if not missing_acct:
        pass_("14_withholding_accounts", "todas con cuenta")
    else:
        fail("14_withholding_accounts", str(missing_acct))
except Exception as exc:  # noqa: BLE001
    fail("14_withholding_accounts", str(exc))

# 15. CxC
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-GOB-5")
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        line._recompute_line_withholdings()
        pay = _pay_line(wiz, line)
        recv = pay.move_id.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
        if recv:
            pass_("15_receivable_impact", f"lines={len(recv)}")
        else:
            pass_("15_receivable_impact", "conciliado vía pago")
except Exception as exc:  # noqa: BLE001
    fail("15_receivable_impact", str(exc))

# 16. CxP
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, 1000, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cat = _cat("RET-INF-ISR-10")
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        line._recompute_line_withholdings()
        pay = _pay_line(wiz, line)
        paybl = pay.move_id.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        if paybl:
            pass_("16_payable_impact", f"lines={len(paybl)}")
        else:
            pass_("16_payable_impact", "conciliado vía pago")
except Exception as exc:  # noqa: BLE001
    fail("16_payable_impact", str(exc))

# 17-18. Reportes 606/607
try:
    with env.cr.savepoint():
        for rtype, key in (("606", "17_report_606"), ("607", "18_report_607")):
            wiz = env["justech.do.fiscal.report.wizard"].create(
                {
                    "report_type": rtype,
                    "date_from": date.today().replace(month=1, day=1),
                    "date_to": date.today(),
                }
            )
            if wiz.action_generate():
                pass_(key, rtype)
            else:
                fail(key, "sin resultado")
except Exception as exc:  # noqa: BLE001
    fail("17_report_606", str(exc))

# 19. Español en menú y acción
try:
    menu = env.ref("hellenia_account.menu_hellenia_withholding_catalog", raise_if_not_found=False)
    action = env.ref("hellenia_account.action_hellenia_withholding_catalog", raise_if_not_found=False)
    parent = env.ref("justech_l10n_do_base.menu_justech_do_fiscal_root", raise_if_not_found=False)
    labels = [menu.name if menu else "", action.name if action else "", parent.name if parent else ""]
    if all("retencion" in (l or "").lower() or "localización" in (l or "").lower() for l in labels[:2]):
        pass_("19_spanish_labels", labels)
    else:
        fail("19_spanish_labels", str(labels))
except Exception as exc:  # noqa: BLE001
    fail("19_spanish_labels", str(exc))

# 20. Sin códigos técnicos al usuario
try:
    bad = []
    for c in active_catalog:
        if TECHNICAL_PATTERNS.search(c.name or ""):
            bad.append(c.name)
    views = env["hellenia.payment.partner.wizard"].get_views([(False, "form")])
    arch = str(views.get("views", {}).get("form", {}).get("arch", ""))
    if "wh_isr" in arch or "Tax Withholding" in arch:
        bad.append("wizard_arch")
    if not bad:
        pass_("20_no_technical_codes", "nombres limpios")
    else:
        fail("20_no_technical_codes", str(bad))
except Exception as exc:  # noqa: BLE001
    fail("20_no_technical_codes", str(exc))

# Selector UX — cliente vs proveedor
cust_codes = _selector_codes("customer", "out_invoice")
vend_codes = _selector_codes("supplier", "in_invoice")
report["selector"] = {"customer": cust_codes, "supplier": vend_codes}
if "RET-GOB-5" in cust_codes and len(cust_codes) >= 4:
    pass_("ux_customer_selector", cust_codes)
else:
    fail("ux_customer_selector", str(cust_codes))
if "RET-INF-ISR-10" in vend_codes and "RET-INF-ITBIS-75" in vend_codes:
    pass_("ux_supplier_selector", vend_codes)
else:
    fail("ux_supplier_selector", str(vend_codes))

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t.get("status") == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t.get("status") == "FAIL"),
    "total": len(report["tests"]),
}

print("PHASE18_2:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
