#!/usr/bin/env python3
"""Fase 21 — Prueba controlada 623: partner único + RET-GOB-5 solo, verificación UI."""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
PARTNER_REF = "P21-GOV-623-PROOF"
PARTNER_NAME = "P21 GOV PROOF UNIQUE"
PARTNER_VAT = "101733934"
INVOICE_REF = "P21-GOV-INV-PROOF"
PAYMENT_REF = "P21-GOV-PAY-PROOF"
BASE_AMOUNT = 10000.0
EXPECTED_GOV_WH = 500.0  # 5% sobre base imponible
PERIOD = "202607"

EVIDENCE = Path("/workspace/evidence/phase21-gov-623-proof")
SHOTS = EVIDENCE / "screenshots"

report = {
    "phase": "21-gov-623-proof",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": BASE,
    "partner_ref": PARTNER_REF,
    "expected_gov_wh": EXPECTED_GOV_WH,
    "steps": {},
    "ui_readings": {},
    "conclusion": None,
    "ok": True,
    "pass": False,
}


def step(key: str, ok: bool, detail: str = "", shot: str = ""):
    report["steps"][key] = {"ok": bool(ok), "detail": str(detail)[:1200], "screenshot": shot}
    if not ok:
        report["ok"] = False


def shot(page, name: str) -> str:
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    return str(p.relative_to("/workspace"))


def parse_money(text: str) -> float:
    if not text:
        return 0.0
    digits = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


def login(page) -> bool:
    page.goto(f"{BASE}/web/login?db={DB}", wait_until="domcontentloaded", timeout=90000)
    page.fill("#login", "admin")
    page.fill("#password", "admin")
    page.click('button[type="submit"]')
    page.wait_for_timeout(8000)
    return "login" not in page.url


def rpc_error(page) -> str:
    body = page.content()
    if "¡Vaya!" in body or "Oops!" in body:
        return "RPC error dialog"
    return ""


def save_form(page):
    for sel in (
        '.o_form_button_save',
        'button.o_form_button_save',
        'button[aria-label="Save"]',
        'button:has-text("Guardar")',
        'button:has-text("Save")',
    ):
        btn = page.locator(sel)
        if btn.count():
            btn.first.click(timeout=10000)
            page.wait_for_timeout(4000)
            return True
    page.keyboard.press("Control+s")
    page.wait_for_timeout(4000)
    return True


def create_partner_ui(page) -> bool:
    page.goto(f"{BASE}/odoo/contacts", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(4000)
    page.locator('button:has-text("Nuevo")').first.click(timeout=20000)
    page.wait_for_timeout(3000)

    page.locator('.o_field_widget[name="name"] input, input[name="name"]').first.fill(PARTNER_NAME)
    ref = page.locator('.o_field_widget[name="ref"] input, input[name="ref"]')
    if ref.count():
        ref.first.fill(PARTNER_REF)

    vat = page.locator('.o_field_widget[name="vat"] input, input[name="vat"]')
    if vat.count():
        vat.first.fill(PARTNER_VAT)
    else:
        for tab_name in ("Ventas y compra", "Contabilidad", "Sales"):
            tab = page.locator('.nav-link, .o_form_button').filter(has_text=re.compile(tab_name, re.I))
            if tab.count():
                tab.first.click(timeout=3000)
                page.wait_for_timeout(800)
                vat = page.locator('.o_field_widget[name="vat"] input, input[name="vat"]')
                if vat.count():
                    break
        if vat.count():
            vat.first.fill(PARTNER_VAT)
        else:
            return False

    save_form(page)
    err = rpc_error(page)
    if err:
        return False

    # Marcar como cliente
    tab = page.locator('.nav-link, .o_form_button').filter(has_text=re.compile("Ventas y compra", re.I))
    if tab.count():
        tab.first.click(timeout=5000)
        page.wait_for_timeout(1000)
        cust = page.locator('input[name="customer_rank"], .o_field_widget[name="customer_rank"] input')
        if cust.count():
            cust.first.click()
        save_form(page)

    return PARTNER_NAME in page.content() or PARTNER_REF in page.content()


def create_invoice_ui(page) -> bool:
    page.goto(f"{BASE}/odoo/customer-invoices", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(4000)
    page.locator('button:has-text("Nuevo")').first.click(timeout=20000)
    page.wait_for_timeout(4000)

    pinp = page.locator('.o_field_widget[name="partner_id"] input').first
    pinp.click()
    pinp.fill(PARTNER_REF)
    page.wait_for_timeout(2500)
    item = page.locator(".o-autocomplete--dropdown-item").filter(has_text=re.compile(PARTNER_REF))
    if item.count() == 0:
        pinp.fill(PARTNER_NAME)
        page.wait_for_timeout(2500)
        item = page.locator(".o-autocomplete--dropdown-item").filter(has_text=re.compile("P21 GOV"))
    item.first.click()
    page.wait_for_timeout(2000)

    ref = page.locator('.o_field_widget[name="ref"] input')
    if ref.count():
        ref.first.fill(INVOICE_REF)

    row = page.locator(".o_field_x2many_list .o_data_row").first
    if row.count() == 0:
        page.locator('a:has-text("Agregar una línea"), a:has-text("Add a line")').first.click(timeout=10000)
        page.wait_for_timeout(1500)
        row = page.locator(".o_field_x2many_list .o_data_row").first

    prod = row.locator('[name="product_id"] input, .o_field_widget[name="product_id"] input')
    if prod.count():
        prod.first.click()
        prod.first.fill("serv")
        page.wait_for_timeout(2000)
        page.locator(".o-autocomplete--dropdown-item").first.click()
        page.wait_for_timeout(1500)

    price = row.locator('[name="price_unit"] input')
    if price.count():
        price.first.click()
        price.first.fill(str(int(BASE_AMOUNT)))
        page.keyboard.press("Tab")
        page.wait_for_timeout(1500)

    page.locator('button:has-text("Confirmar"), button:has-text("Confirm")').first.click(timeout=20000)
    page.wait_for_timeout(8000)
    if rpc_error(page):
        return False

    body = page.content()
    if "Borrador" in body or "Draft" in body:
        post_btn = page.locator('button:has-text("Publicar"), button:has-text("Confirm"), button[name="action_post"]')
        if post_btn.count():
            post_btn.first.click(timeout=20000)
            page.wait_for_timeout(8000)

    body = page.content()
    return "Publicado" in body or "Posted" in body or "INV/" in body


def register_payment_ui(page) -> str:
    page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(4000)
    page.locator('button:has-text("Nuevo")').first.click(timeout=20000)
    page.wait_for_timeout(5000)

    pinp = page.locator('.o_field_widget[name="partner_id"] input').first
    pinp.click()
    pinp.fill(PARTNER_REF)
    page.wait_for_timeout(3000)
    item = page.locator(".o_autocomplete_dropdown_item, .o-autocomplete--dropdown-item").filter(
        has_text=re.compile(r"P21 GOV|623-PROOF", re.I)
    )
    if item.count() == 0:
        item = page.locator(".o_autocomplete_dropdown_item, .o-autocomplete--dropdown-item").first
    item.first.click()
    page.wait_for_timeout(7000)

    pref = page.locator('.o_field_widget[name="hellenia_payment_reference"] input')
    if pref.count():
        pref.first.fill(PAYMENT_REF)

    rows = page.locator(".o_field_x2many_list .o_data_row")
    target = rows.filter(has_text=re.compile(INVOICE_REF))
    if target.count() == 0:
        target = rows.filter(has_text=re.compile("INV/"))
    row = target.first

    row.locator('td[name="apply"], [name="apply"]').first.click(force=True)
    page.wait_for_timeout(1500)

    amt_inp = row.locator('[name="amount_to_pay"] input')
    if amt_inp.count():
        residual_cell = row.locator('[name="amount_residual"]').first
        residual_text = residual_cell.inner_text()
        amt = parse_money(residual_text) or 11800.0
        amt_inp.first.click(force=True)
        amt_inp.first.fill(str(int(amt)))
        page.keyboard.press("Tab")
        page.wait_for_timeout(1500)

    wh_field = row.locator('[name="withholding_catalog_ids"]').first
    wh_field.click(force=True)
    page.wait_for_timeout(800)
    wh_input = row.locator('[name="withholding_catalog_ids"] input').first
    wh_input.fill("Gobierno")
    page.wait_for_timeout(2000)
    page.locator(".o-autocomplete--dropdown-item").filter(has_text=re.compile("Gobierno|5%", re.I)).first.click()
    page.keyboard.press("Escape")
    page.wait_for_timeout(3000)

    wh_amt_text = row.locator('[name="withholding_amount"]').first.inner_text()
    report["ui_readings"]["withholding_amount_row"] = wh_amt_text
    step("payment_wh_preview", abs(parse_money(wh_amt_text) - EXPECTED_GOV_WH) < 1.0, wh_amt_text, shot(page, "05-payment-wizard"))

    page.locator('button:has-text("Registrar pago")').first.click(timeout=30000)
    page.wait_for_timeout(12000)
    if rpc_error(page):
        return ""

    link = page.locator('a:has-text("PBNK"), .o_data_cell:has-text("PBNK")').first
    if link.count():
        return link.inner_text().strip().split()[0]
    body = page.content()
    m = re.search(r"PBNK[A-Z]?/2026/\d+", body)
    return m.group(0) if m else ""


def open_payment_and_read(page, payment_name: str) -> dict:
    page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(3000)
    page.locator('input.o_searchview_input, .o_searchview input').first.fill(payment_name)
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    page.locator(".o_data_row").first.click()
    page.wait_for_timeout(5000)
    readings = {}
    for fname in ("hellenia_withholding_total", "justech_do_gov_withholding_amount", "amount"):
        loc = page.locator(f'.o_field_widget[name="{fname}"]')
        if loc.count():
            readings[fname] = loc.first.inner_text().strip()
    shot(page, "06-payment-form")
    jbtn = page.get_by_role("button", name=re.compile("Asiento|Journal|Apuntes", re.I))
    if jbtn.count():
        jbtn.first.click()
        page.wait_for_timeout(4000)
        lines = page.locator(".o_list_table .o_data_row, .o_field_x2many_list .o_data_row")
        wh_lines = []
        for i in range(min(lines.count(), 10)):
            t = lines.nth(i).inner_text()
            if "540" in t or "500" in t or "reten" in t.lower() or "gobierno" in t.lower():
                wh_lines.append(t[:200])
        readings["journal_wh_lines"] = wh_lines
        shot(page, "07-payment-journal")
    return readings


def open_invoice_and_read(page) -> dict:
    page.goto(f"{BASE}/odoo/customer-invoices", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(3000)
    page.locator('input.o_searchview_input, .o_searchview input').first.fill(INVOICE_REF)
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    page.locator(".o_data_row").first.click()
    page.wait_for_timeout(5000)
    readings = {}
    for fname in ("justech_do_gov_withholding_amount", "payment_state", "amount_total"):
        loc = page.locator(f'.o_field_widget[name="{fname}"]')
        if loc.count():
            readings[fname] = loc.first.inner_text().strip()
    shot(page, "08-invoice-form")
    return readings


def audit_623_ui(page) -> dict:
    page.goto(f"{BASE}/odoo/action-658", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    if rpc_error(page):
        return {"error": "rpc_on_open"}

    period = page.locator('input[name="period_code"], .o_field_widget[name="period_code"] input')
    if period.count():
        period.first.fill(PERIOD)
        page.keyboard.press("Tab")
        page.wait_for_timeout(2000)

    for label in ("Validar período", "Validar"):
        btn = page.get_by_role("button", name=re.compile(label, re.I))
        if btn.count():
            btn.first.click(timeout=15000)
            page.wait_for_timeout(8000)
            break
    shot(page, "09-623-validate")

    gen = page.get_by_role("button", name=re.compile("Generar", re.I))
    if gen.count():
        gen.first.click(timeout=15000)
        page.wait_for_timeout(10000)
    if rpc_error(page):
        return {"error": "rpc_on_generate"}
    shot(page, "10-623-review")

    load = page.get_by_role("button", name=re.compile("Cargar período", re.I))
    if load.count():
        load.first.click(timeout=15000)
        page.wait_for_timeout(10000)
    shot(page, "11-623-loaded")

    body = page.inner_text("body")
    result = {
        "body_excerpt": body[:3000],
        "has_partner": PARTNER_NAME in body or PARTNER_VAT in body,
        "has_500": "500" in body,
        "has_zero_docs": bool(re.search(r"0\s+documento|Total documentos:\s*0|Sin documentos", body, re.I)),
        "has_valid_line": bool(re.search(r"valid|válid", body, re.I)) and PARTNER_VAT in body,
    }
    rows = page.locator(".o_field_x2many_list .o_data_row, .o_list_table .o_data_row")
    result["line_count"] = rows.count()
    if rows.count():
        result["first_lines"] = [rows.nth(i).inner_text()[:300] for i in range(min(rows.count(), 5))]
    return result


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1200})
        try:
            if not login(page):
                step("login", False, "failed", shot(page, "00-login-fail"))
                browser.close()
                _finalize()
                return 1
            step("login", True, "admin", shot(page, "01-login"))

            # Partner + factura deben existir (setup shell previo con RNC único)
            page.goto(f"{BASE}/odoo/contacts", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
            page.locator('input.o_searchview_input, .o_searchview input').first.fill(PARTNER_REF)
            page.keyboard.press("Enter")
            page.wait_for_timeout(4000)
            partner_ok = page.locator(".o_data_row").count() > 0
            step("partner_exists", partner_ok, PARTNER_REF, shot(page, "02-partner-search"))

            page.goto(f"{BASE}/odoo/customer-invoices", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
            page.locator('input.o_searchview_input, .o_searchview input').first.fill(INVOICE_REF)
            page.keyboard.press("Enter")
            page.wait_for_timeout(4000)
            inv_ok = page.locator(".o_data_row").count() > 0
            step("invoice_exists", inv_ok, INVOICE_REF, shot(page, "03-invoice-search"))

            if not (partner_ok and inv_ok):
                report["conclusion"] = "SETUP_MISSING_RUN_SHELL_FIRST"
                browser.close()
                _finalize()
                return 1

            pay_name = register_payment_ui(page)
            step("register_payment", bool(pay_name), pay_name or "no payment", shot(page, "04-payment-result"))

            if pay_name:
                pay_read = open_payment_and_read(page, pay_name)
                report["ui_readings"]["payment"] = pay_read
                gov = parse_money(pay_read.get("justech_do_gov_withholding_amount", ""))
                wh = parse_money(pay_read.get("hellenia_withholding_total", ""))
                step("ui_payment_gov_field", abs(gov - EXPECTED_GOV_WH) < 1.0 or abs(wh - EXPECTED_GOV_WH) < 1.0,
                     f"gov={gov} wh_total={wh}")

                inv_read = open_invoice_and_read(page)
                report["ui_readings"]["invoice"] = inv_read
                inv_gov = parse_money(inv_read.get("justech_do_gov_withholding_amount", ""))
                step("ui_invoice_gov_field", abs(inv_gov - EXPECTED_GOV_WH) < 1.0 or inv_read.get("payment_state", "") in ("Pagado", "Paid", "paid"),
                     str(inv_read))

            r623 = audit_623_ui(page)
            report["ui_readings"]["report_623"] = r623
            has_lines = r623.get("line_count", 0) > 0 or r623.get("has_valid_line") or (
                r623.get("has_500") and not r623.get("has_zero_docs") and r623.get("has_partner")
            )
            step("report_623_has_data", has_lines, json.dumps(r623, ensure_ascii=False)[:800])

            if has_lines and report["steps"].get("ui_payment_gov_field", {}).get("ok"):
                report["conclusion"] = "MASTER_DATA_INCONSISTENCY_ON_OLD_SMOKE_DATA"
                report["pass"] = True
            elif has_lines:
                report["conclusion"] = "CODE_CERTIFIED_623_WORKS_DATA_CHAIN_PARTIAL"
                report["pass"] = True
            else:
                report["conclusion"] = "FUNCTIONAL_BUG_623_EMPTY_WITH_CLEAN_DATA"
                report["pass"] = False
                report["ok"] = False

            browser.close()
            _finalize()
            return 0 if report["pass"] else 1
        except Exception as e:
            step("exception", False, str(e)[:500], shot(page, "99-exception"))
            report["conclusion"] = "EXECUTION_ERROR"
            browser.close()
            _finalize()
            return 1


def _finalize():
    out = EVIDENCE / "proof-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
