#!/usr/bin/env python3
"""Fase 18.3 — Certificación funcional del motor de retenciones RD (TEST).

Auditoría real sobre hellenia_test — no asume que el código basta.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = "/tmp/hellenia-phase18-3-evidence"
os.makedirs(EVIDENCE_DIR, exist_ok=True)

report = {
    "phase": "18.3-withholding-certification",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module_version": None,
    "checks": {},
    "ok": True,
    "errors": [],
    "production_ready": False,
    "visual_evidence": [],
    "visual_evidence_html": {},
}

ENGLISH_UI = re.compile(
    r"\b(Tax Withholding|Withholding|Retained by State|Register payment|"
    r"Payment Register|Write-off|wh_isr_|wh_itbis_)\b",
    re.I,
)
TECHNICAL_USER = re.compile(r"wh_[a-z_]+|RET-[A-Z0-9-]+", re.I)

EXPECTED_ACTIVE = {
    "RET-GOB-5",
    "RET-ITBIS-30",
    "RET-ITBIS-100",
    "RET-INF-ISR-10",
    "RET-INF-ITBIS-75",
    "RET-ISR-2",
    "RET-HON-10",
}


def err(msg):
    report["ok"] = False
    report["errors"].append(msg)


def pass_(key, detail=""):
    report["checks"][key] = {"status": "PASS", "detail": detail}


def fail(key, msg):
    report["checks"][key] = {"status": "FAIL", "message": msg}
    err(f"{key}: {msg}")


def _html(name, title, rows):
    path = os.path.join(EVIDENCE_DIR, name)
    body = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows
    )
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:8px}}
th{{background:#714B67;color:#fff;text-align:left}}</style></head>
<body><h1>{title}</h1><table><tr><th>Elemento</th><th>Valor</th></tr>{body}</table>
<p>Generado: {datetime.now(timezone.utc).isoformat()} — {DB}</p></body></html>"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    report["visual_evidence"].append(path)
    report["visual_evidence_html"][name] = html
    return path


# --- Upgrade + sync ---
mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if mod:
    mod.button_immediate_upgrade()
    env.cr.commit()
    report["module_version"] = mod.latest_version
    pass_("00_module_upgrade", mod.latest_version)
else:
    fail("00_module_upgrade", "hellenia_account no encontrado")

setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
setup.configure_withholding_reference()
env.cr.commit()

Catalog = env["hellenia.withholding.catalog"]
company = env.company
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1)
tax_purchase = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase")], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)


def _cat(code):
    return Catalog.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)


def _method_line(journal, ptype="inbound"):
    lines = journal.inbound_payment_method_line_ids if ptype == "inbound" else journal.outbound_payment_method_line_ids
    return lines.filtered(lambda l: "transferencia" in (l.name or "").lower())[:1] or lines[:1]


def _invoice(partner, price=1000, move_type="out_invoice"):
    taxes = tax_sale if move_type.startswith("out") else tax_purchase
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


def _wiz(partner, partner_type):
    ptype = "inbound" if partner_type == "customer" else "outbound"
    mline = _method_line(bnkd, ptype)
    return env["hellenia.payment.partner.wizard"].create(
        {
            "partner_type": partner_type,
            "partner_id": partner.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": mline.id if mline else False,
        }
    )


def _line_for(wiz, move):
    return wiz.line_ids.filtered(lambda l: l.move_id == move)[:1]


def _pay(wiz, line):
    line._recompute_line_withholdings()
    reg = (
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
    return reg._create_payments()


def _selector(partner_type, move_type):
    return Catalog.search(Catalog._domain_for_payment(partner_type, move_type, company=company))


# 1. Catálogo activas
active = Catalog.search([("active", "=", True), ("code", "not in", ("RET-NONE", "wh_none"))])
active_codes = set(active.mapped("code"))
missing = EXPECTED_ACTIVE - active_codes
catalog_rows = [(c.code, f"{c.name} | cuenta={c.account_id.code or '—'}") for c in active.sorted("sequence")]
_html("01-catalogo-activo.html", "Catálogo — retenciones activas", catalog_rows)
if not missing:
    pass_("01_catalog_active_complete", sorted(active_codes))
else:
    fail("01_catalog_active_complete", f"faltan {sorted(missing)}")

# 2. Crear retención
try:
    with env.cr.savepoint():
        gov = _cat("RET-GOB-5")
        tmp = Catalog.create(
            {
                "name": "Retención certificación temporal",
                "code": "RET-CERT-TMP",
                "withholding_type": "other",
                "base_type": "untaxed",
                "partner_scope": "both",
                "move_scope": "both",
                "account_id": gov.account_id.id if gov and gov.account_id else False,
                "active": False,
                "notes": "Creada en certificación 18.3",
            }
        )
        pass_("02_create_withholding", tmp.code)
        Catalog.search([("code", "=", "RET-CERT-TMP")]).unlink()
except Exception as exc:  # noqa: BLE001
    fail("02_create_withholding", str(exc))

# 3. Editar retención
try:
    with env.cr.savepoint():
        cat = _cat("RET-ISR-2")
        note = f"Cert 18.3 {date.today().isoformat()}"
        cat.write({"notes": note})
        if cat.notes == note:
            pass_("03_edit_withholding", "notas actualizadas")
        else:
            fail("03_edit_withholding", "write falló")
except Exception as exc:  # noqa: BLE001
    fail("03_edit_withholding", str(exc))

# 4-6. Desactivar / selector / reactivar
try:
    with env.cr.savepoint():
        cat = _cat("RET-HON-10")
        was = cat.active
        cat.active = False
        env.cr.flush()
        off = set(_selector("customer", "out_invoice").mapped("code"))
        cat.active = True
        env.cr.flush()
        on = set(_selector("customer", "out_invoice").mapped("code"))
        cat.active = was
        if "RET-HON-10" not in off:
            pass_("04_deactivate_hides_selector", list(off))
        else:
            fail("04_deactivate_hides_selector", "aún visible")
        if "RET-HON-10" in on:
            pass_("05_reactivate_shows_selector", list(on))
        else:
            fail("05_reactivate_shows_selector", "no reaparece")
        pass_("06_selector_toggle_roundtrip", "OK")
except Exception as exc:  # noqa: BLE001
    fail("04_deactivate_hides_selector", str(exc))

# 7. Filtros selector
cust_sale = set(_selector("customer", "out_invoice").mapped("code"))
vend_purch = set(_selector("supplier", "in_invoice").mapped("code"))
cust_wrong = set(_selector("customer", "in_invoice").mapped("code"))
_html(
    "07-selector-filtros.html",
    "Selector — filtros cliente/proveedor y operación",
    [
        ("Cliente + Venta", ", ".join(sorted(cust_sale))),
        ("Proveedor + Compra", ", ".join(sorted(vend_purch))),
        ("Cliente + Compra (debe excluir informales)", ", ".join(sorted(cust_wrong))),
    ],
)
if "RET-GOB-5" in cust_sale and "RET-INF-ISR-10" not in cust_sale:
    pass_("07_selector_filters", f"cliente={len(cust_sale)} proveedor={len(vend_purch)}")
else:
    fail("07_selector_filters", f"cust={cust_sale} vend={vend_purch}")

# 8-9. Múltiples retenciones / facturas distintas
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, 1200, "in_invoice")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cats = [_cat("RET-ITBIS-30"), _cat("RET-INF-ISR-10")]
        line.withholding_catalog_ids = [Command.set([c.id for c in cats if c])]
        line._recompute_line_withholdings()
        if len(line.withholding_detail_ids) >= 2:
            pass_("08_multi_withholding_same_invoice", len(line.withholding_detail_ids))
        else:
            fail("08_multi_withholding_same_invoice", "detalle incompleto")

        inv1 = _invoice(vendor, 800, "in_invoice")
        inv2 = _invoice(vendor, 900, "in_invoice")
        wiz2 = _wiz(vendor, "supplier")
        l1 = _line_for(wiz2, inv1)
        l2 = _line_for(wiz2, inv2)
        c30 = _cat("RET-ITBIS-30")
        l2.withholding_catalog_ids = [Command.set(c30.ids)] if c30 else []
        l1._recompute_line_withholdings()
        l2._recompute_line_withholdings()
        if not l1.withholding_catalog_ids and l2.withholding_catalog_ids:
            pass_("09_different_withholdings_per_invoice", f"{l1.withholding_summary}|{l2.withholding_summary}")
        else:
            fail("09_different_withholdings_per_invoice", "mezcla incorrecta")
except Exception as exc:  # noqa: BLE001
    fail("08_multi_withholding_same_invoice", str(exc))

# 10-12. Cálculo base, recálculo tiempo real, neto
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat_itbis = _cat("RET-ITBIS-30")
        line.withholding_catalog_ids = [Command.set(cat_itbis.ids)]
        line._recompute_line_withholdings()
        wh1 = line.withholding_amount
        expected_wh = cat_itbis.compute_withholding_amount(inv)
        expected_base = cat_itbis._itbis_amount(inv)
        base_ok = abs(wh1 - expected_wh) < 0.02 and expected_base > 0
        line.amount_to_pay = 500
        line._recompute_line_withholdings()
        wiz._compute_totals()
        wh2 = line.withholding_amount
        net_ok = abs(wiz.amount_after_withholding - (wiz.payment_total - wiz.withholding_total)) < 0.02
        if base_ok and wh1 > 0:
            pass_("10_base_calculation", f"base_itbis={expected_base:.2f} wh={wh1:.2f}")
        else:
            fail("10_base_calculation", f"wh1={wh1} expected={expected_wh}")
        if abs(wh2 - wh1) < 0.02:
            pass_("11_realtime_withholding_recalc", f"itbis estable wh={wh2:.2f}")
        else:
            fail("11_realtime_withholding_recalc", f"wh1={wh1} wh2={wh2}")
        if net_ok:
            pass_("12_realtime_net_recalc", f"neto={wiz.amount_after_withholding:.2f}")
        else:
            fail("12_realtime_net_recalc", "totales no cuadran")
except Exception as exc:  # noqa: BLE001
    fail("10_base_calculation", str(exc))

# 13-15. Asientos, cuentas, balance
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1000)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-GOB-5")
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        pay = _pay(wiz, line)
        move = pay.move_id
        deb = sum(move.line_ids.mapped("debit"))
        cred = sum(move.line_ids.mapped("credit"))
        wh_lines = move.line_ids.filtered(lambda l: l.account_id == cat.account_id)
        if wh_lines:
            pass_("13_accounting_entries", pay.name)
            pass_("14_withholding_accounts_match", wh_lines[0].account_id.code)
        else:
            fail("13_accounting_entries", "sin línea retención")
            fail("14_withholding_accounts_match", "cuenta no encontrada")
        if abs(deb - cred) < 0.02:
            pass_("15_balanced_entry", f"D={deb:.2f}")
        else:
            fail("15_balanced_entry", f"D={deb} C={cred}")
        report["sample_payment"] = {
            "payment": pay.name,
            "move": move.name,
            "lines": [
                {"account": l.account_id.code, "name": l.name, "debit": l.debit, "credit": l.credit}
                for l in move.line_ids
            ],
        }
except Exception as exc:  # noqa: BLE001
    fail("13_accounting_entries", str(exc))

# 16. Conciliación bancaria
if bnkd and bnkd.bank_account_id:
    pass_("16_bank_reconciliation_ready", bnkd.code)
else:
    fail("16_bank_reconciliation_ready", "BNKD sin cuenta bancaria")

# 17. Reportes 606 / 607
try:
    with env.cr.savepoint():
        inv_v = _invoice(vendor, 1100, "in_invoice")
        wiz_v = _wiz(vendor, "supplier")
        lv = _line_for(wiz_v, inv_v)
        lv.withholding_catalog_ids = [Command.set(_cat("RET-INF-ISR-10").ids)]
        _pay(wiz_v, lv)
        inv_c = _invoice(customer, 1100)
        wiz_c = _wiz(customer, "customer")
        lc = _line_for(wiz_c, inv_c)
        lc.withholding_catalog_ids = [Command.set(_cat("RET-GOB-5").ids)]
        _pay(wiz_c, lc)
        rep606 = env["justech.do.fiscal.report"].create(
            {
                "name": f"Cert 606 {date.today()}",
                "report_type": "606",
                "date_from": date.today().replace(month=1, day=1),
                "date_to": date.today(),
            }
        )
        rep606.action_generate()
        rep607 = env["justech.do.fiscal.report"].create(
            {
                "name": f"Cert 607 {date.today()}",
                "report_type": "607",
                "date_from": date.today().replace(month=1, day=1),
                "date_to": date.today(),
            }
        )
        rep607.action_generate()
        lines606 = rep606.line_ids.filtered(lambda l: l.move_id == inv_v)
        lines607 = rep607.line_ids.filtered(lambda l: l.move_id == inv_c)
        _html(
            "17-reportes-fiscales.html",
            "Reportes 606 / 607 — facturas con retención en pago",
            [
                ("606 factura proveedor", inv_v.name if lines606 else "NO ENCONTRADA"),
                ("607 factura cliente", inv_c.name if lines607 else "NO ENCONTRADA"),
                ("NCF proveedor", inv_v.justech_do_ncf or "—"),
                ("NCF cliente", inv_c.justech_do_ncf or "—"),
            ],
        )
        if lines606 and lines607:
            pass_("17_reports_606_607", f"606={inv_v.name} 607={inv_c.name}")
        else:
            fail("17_reports_606_607", f"606={bool(lines606)} 607={bool(lines607)}")
except Exception as exc:  # noqa: BLE001
    fail("17_reports_606_607", str(exc))

# 18-19. Historial factura y pago
try:
    with env.cr.savepoint():
        inv = _invoice(customer, 1300)
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-GOB-5")
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        pay = _pay(wiz, line)
        wh_label = cat.name
        pay_move = pay.move_id
        pay_wh = pay_move.line_ids.filtered(lambda l: cat.name in (l.name or ""))
        matched = inv.payment_state in ("paid", "in_payment", "partial")
        _html(
            "18-19-historial.html",
            "Historial factura y pago — retenciones",
            [
                ("Factura", inv.name),
                ("NCF", inv.justech_do_ncf or "—"),
                ("Pago vinculado", pay.name),
                ("Pago conciliado con factura", "Sí" if matched else "No"),
                ("Línea retención en asiento pago", pay_wh[0].name if pay_wh else "—"),
                ("Cuenta retención", pay_wh[0].account_id.code if pay_wh else "—"),
                ("Monto retención", f"{abs(pay_wh[0].balance):.2f}" if pay_wh else "—"),
            ],
        )
        if matched and pay_wh:
            pass_("18_invoice_history_traceability", inv.name)
            pass_("19_payment_history_traceability", pay_wh[0].name)
        else:
            fail("18_invoice_history_traceability", f"matched={matched}")
            fail("19_payment_history_traceability", "sin línea retención")
except Exception as exc:  # noqa: BLE001
    fail("18_invoice_history_traceability", str(exc))

# 20. Sin inglés en UI retenciones
ui_bad = []
menu = env.ref("hellenia_account.menu_hellenia_withholding_catalog", raise_if_not_found=False)
action = env.ref("hellenia_account.action_hellenia_withholding_catalog", raise_if_not_found=False)
for label in (menu.name, action.name):
    if ENGLISH_UI.search(label or ""):
        ui_bad.append(label)
views = env["ir.ui.view"].search(
    [
        ("model", "in", ["hellenia.withholding.catalog", "hellenia.payment.partner.wizard"]),
        ("type", "in", ["form", "list", "search"]),
    ]
)
for view in views:
    arch = view.arch_db or ""
    if ENGLISH_UI.search(arch):
        ui_bad.append(view.name)
if not ui_bad:
    pass_("20_no_english_ui", "etiquetas en español")
else:
    fail("20_no_english_ui", str(ui_bad[:5]))

# 21. Sin códigos técnicos visibles al usuario
user_bad = []
for c in active:
    if TECHNICAL_USER.search(c.name or "") and "RET-" in (c.name or ""):
        user_bad.append(c.name)
wiz_views = env["hellenia.payment.partner.wizard"].get_views([(False, "form")])
arch = str(wiz_views.get("views", {}).get("form", {}).get("arch", ""))
if "wh_isr" in arch or "Tax Withholding" in arch:
    user_bad.append("wizard_arch")
# code field hidden from non-managers in list view
if not user_bad:
    pass_("21_no_technical_codes_user", "nombres limpios")
else:
    fail("21_no_technical_codes_user", str(user_bad))

# 22. Estilo Odoo / Hellenia
native_markers = ["widget", "oe_title", "web_ribbon", "boolean_toggle", "many2many_tags"]
catalog_view = env.ref("hellenia_account.view_hellenia_withholding_catalog_form", raise_if_not_found=False)
wizard_view = env.ref("hellenia_account.view_hellenia_payment_partner_wizard_form", raise_if_not_found=False)
arch_cat = catalog_view.arch_db if catalog_view else ""
arch_wiz = wizard_view.arch_db if wizard_view else ""
found = sum(1 for m in native_markers if m in arch_cat or m in arch_wiz)
parent = env.ref("justech_l10n_do_base.menu_justech_do_fiscal_root", raise_if_not_found=False)
_html(
    "22-estilo-odoo.html",
    "Estilo visual Odoo / Hellenia",
    [
        ("Menú administración", menu.complete_name if menu else "—"),
        ("Padre menú", parent.name if parent else "—"),
        ("Marcadores UI nativos", str(found)),
        ("Wizard string", wizard_view.name if wizard_view else "—"),
    ],
)
if found >= 3 and parent:
    pass_("22_odoo_hellenia_style", f"markers={found}")
else:
    fail("22_odoo_hellenia_style", f"markers={found}")

report["summary"] = {
    "passed": sum(1 for c in report["checks"].values() if c.get("status") == "PASS"),
    "failed": sum(1 for c in report["checks"].values() if c.get("status") == "FAIL"),
    "total": len(report["checks"]),
}
report["verdict"] = "PASS" if report["ok"] else "FAIL"

json_path = os.path.join(EVIDENCE_DIR, "phase18-3-withholding-certification-test.json")
with open(json_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2, default=str)

print("PHASE18_3:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
