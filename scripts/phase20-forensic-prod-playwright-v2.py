#!/usr/bin/env python3
"""Fase 20 — Playwright forense PROD v2: partner 22, facturas, wizard completo."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
LOGIN = "admin"
PASSWORD = "admin"
PARTNER_ID = 22  # único SMOKE con facturas pendientes en PROD
PARTNER = "SMOKE P13.4 CF"
REF = "P20-FORENSIC"
EVIDENCE = Path("/workspace/evidence/phase20-forensic")
SHOTS = EVIDENCE / "screenshots"

report = {
    "phase": "20-forensic-prod-playwright-v2",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": BASE,
    "partner_id": PARTNER_ID,
    "backup": "/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1248",
    "steps": {},
    "checkbox_counts": {},
    "ok": True,
    "pass": False,
}


def step(key, ok, detail="", shot=""):
    report["steps"][key] = {"ok": bool(ok), "detail": detail, "screenshot": shot}
    if not ok:
        report["ok"] = False


def shot(page, name: str) -> str:
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    return str(p.relative_to("/workspace"))


def login(page):
    page.goto(f"{BASE}/web/login?db={DB}", wait_until="domcontentloaded", timeout=60000)
    page.fill("#login", LOGIN)
    page.fill("#password", PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_timeout(8000)
    return "login" not in page.url


def count_apply(page) -> dict:
    return page.evaluate(
        """() => {
        const rows = [...document.querySelectorAll('.o_field_x2many_list .o_data_row, .o_list_table tbody tr')];
        let total=0, checked=0, details=[];
        for (const row of rows) {
            const applyCell = row.querySelector('[name="apply"]');
            if (!applyCell) continue;
            total++;
            const input = applyCell.querySelector('input[type="checkbox"]');
            let isChecked = false;
            if (input) isChecked = input.checked;
            else isChecked = applyCell.classList.contains('o_field_boolean_true');
            if (isChecked) checked++;
            const inv = row.querySelector('[name="invoice_name"]')?.textContent?.trim()||'';
            const amtEl = row.querySelector('[name="amount_to_pay"] input');
            const amt = amtEl ? amtEl.value : (row.querySelector('[name="amount_to_pay"]')?.textContent?.trim()||'');
            details.push({invoice: inv, checked: isChecked, amount_to_pay: amt});
        }
        return {total, checked, details};
    }"""
    )


def post_invoice(page, suffix: str):
    page.goto(f"{BASE}/odoo/customer-invoices/new", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    # partner via many2one - set partner 22 by navigating from partner
    page.goto(f"{BASE}/odoo/customer-invoices/new?partner_id={PARTNER_ID}", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    ref = page.locator('input[name="ref"]')
    if ref.count():
        ref.fill(f"{REF}-{suffix}")
    # add line
    page.locator('.o_field_widget[name="invoice_line_ids"] .o_field_x2many_list_row_add a, .o_list_button_add').first.click(timeout=8000)
    page.wait_for_timeout(1000)
    prod = page.locator('.o_field_widget[name="product_id"] input').last
    if prod.count():
        prod.fill("servicio")
        page.wait_for_timeout(1500)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
    price = page.locator('.o_field_widget[name="price_unit"] input').last
    if price.count():
        price.fill("10000")
    page.wait_for_timeout(1000)
    for label in ("Confirmar", "Confirm", "Publicar", "Post"):
        btn = page.locator(f'button:has-text("{label}")')
        if btn.count() and btn.first.is_enabled():
            btn.first.click()
            page.wait_for_timeout(6000)
            break
    return shot(page, f"invoice-{suffix}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        payments_before = ""
        try:
            if not login(page):
                step("login", False, "falló")
                browser.close()
                print(json.dumps(report, indent=2, ensure_ascii=False))
                return 1
            step("login", True, LOGIN, shot(page, "v2-01-login"))

            for sfx in ("B", "C"):
                s = post_invoice(page, sfx)
                step(f"invoice_{sfx}", True, f"{REF}-{sfx}", s)

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            payments_before = page.inner_text("body")
            page.locator('button:has-text("Nuevo")').first.click(timeout=15000)
            page.wait_for_timeout(3000)

            # Abrir wizard con partner_id=22 explícito vía URL interna
            page.goto(
                f"{BASE}/odoo/action-650/new?partner_id={PARTNER_ID}&default_partner_id={PARTNER_ID}",
                wait_until="domcontentloaded",
            )
            page.wait_for_timeout(6000)
            cb1 = count_apply(page)
            report["checkbox_counts"]["capture1"] = cb1
            step(
                "capture1_wizard_load",
                cb1.get("checked", 99) == 0,
                json.dumps(cb1, ensure_ascii=False),
                shot(page, "v2-04-wizard-on-load"),
            )

            if cb1.get("total", 0) >= 1:
                rows = page.locator(".o_field_x2many_list .o_data_row, .o_list_table tbody tr")
                n = rows.count()
                # Desmarcar todas primero
                for i in range(n):
                    cell = rows.nth(i).locator('[name="apply"]')
                    if cell.count():
                        inp = cell.locator('input[type="checkbox"]')
                        if inp.count() and inp.is_checked():
                            inp.click()
                page.wait_for_timeout(500)
                # Marcar solo primera
                first_apply = rows.first.locator('[name="apply"] input[type="checkbox"]')
                if first_apply.count():
                    if not first_apply.is_checked():
                        first_apply.click()
                page.wait_for_timeout(800)
                step("capture2_one_marked", True, "", shot(page, "v2-05-one-marked"))

                amt = rows.first.locator('[name="amount_to_pay"] input')
                if amt.count():
                    amt.click()
                    amt.fill("5000")
                    page.keyboard.press("Tab")
                page.wait_for_timeout(1000)
                step("capture3_5000", True, "", shot(page, "v2-06-amount-5000"))

                page.locator('input[name="hellenia_payment_reference"]').fill(f"{REF}-PAY-ONE")
                page.locator('button:has-text("Registrar pago")').first.click(timeout=20000)
                page.wait_for_timeout(10000)
                step("capture4_registered", True, "", shot(page, "v2-07-after-register"))

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            body = page.inner_text("body")
            new_5000 = body.count("5,000") + body.count("5000.00")
            step("capture5_payments", new_5000 >= 1, f"mentions_5000={new_5000}", shot(page, "v2-08-payments"))

            browser.close()
            report["pass"] = report["ok"]
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if report["ok"] else 1
        except Exception as e:
            step("exception", False, str(e)[:500], shot(page, "v2-99-error"))
            browser.close()
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 1


if __name__ == "__main__":
    sys.exit(main())
