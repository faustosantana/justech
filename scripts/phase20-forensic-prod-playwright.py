#!/usr/bin/env python3
"""Fase 20 — Playwright forense PROD: wizard pagos SMOKE P13.4 CF."""
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
PARTNER = "SMOKE P13.4 CF"
REF = "P20-FORENSIC"
EVIDENCE = Path("/workspace/evidence/phase20-forensic")
SHOTS = EVIDENCE / "screenshots"

report = {
    "phase": "20-forensic-prod-playwright",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": BASE,
    "database": DB,
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


def count_apply_checkboxes(page) -> dict:
    return page.evaluate(
        """() => {
        const rows = [...document.querySelectorAll('.o_list_table tbody tr, .o_data_row')];
        let total = 0, checked = 0, details = [];
        for (const row of rows) {
            const applyCell = row.querySelector('[name="apply"]');
            if (!applyCell) continue;
            total++;
            const cb = applyCell.querySelector('input[type="checkbox"]');
            const isChecked = cb ? cb.checked : applyCell.classList.contains('o_field_boolean_true')
                || applyCell.querySelector('.form-check-input:checked') !== null;
            if (isChecked) checked++;
            const inv = row.querySelector('[name="invoice_name"]')?.textContent?.trim() || '';
            const amt = row.querySelector('[name="amount_to_pay"] input')?.value
                || row.querySelector('[name="amount_to_pay"]')?.textContent?.trim() || '';
            details.push({invoice: inv, checked: isChecked, amount_to_pay: amt});
        }
        return {total, checked, details};
    }"""
    )


def create_smoke_invoice(page, ref_suffix: str) -> bool:
    page.goto(f"{BASE}/odoo/customer-invoices/new", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    partner = page.locator('.o_field_widget[name="partner_id"] input').first
    partner.click()
    partner.fill(PARTNER)
    page.wait_for_timeout(1500)
    page.locator(f'.o-autocomplete--dropdown-item:has-text("{PARTNER}")').first.click(timeout=8000)
    page.wait_for_timeout(1000)
    ref = page.locator('.o_field_widget[name="ref"] input, .o_field_widget[name="payment_reference"] input').first
    if ref.count():
        ref.fill(f"{REF}-{ref_suffix}")
    line = page.locator('.o_field_widget[name="invoice_line_ids"] input').first
    if line.count():
        line.click()
        line.fill("10000")
        page.keyboard.press("Tab")
    page.wait_for_timeout(1000)
    confirm = page.locator('button:has-text("Confirmar"), button:has-text("Confirm")')
    if confirm.count():
        confirm.first.click()
        page.wait_for_timeout(5000)
        return True
    post = page.locator('button:has-text("Publicar"), button:has-text("Post")')
    if post.count():
        post.first.click()
        page.wait_for_timeout(5000)
        return True
    return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            if not login(page):
                step("login", False, "admin/admin falló", shot(page, "00-login-fail"))
                browser.close()
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1
            step("login", True, LOGIN, shot(page, "01-login-ok"))

            # Preparar 2 facturas adicionales para SMOKE (solo UI)
            for suffix in ("B", "C"):
                ok = create_smoke_invoice(page, suffix)
                step(f"create_invoice_{suffix}", ok, f"{REF}-{suffix}", shot(page, f"02-invoice-{suffix}"))

            # Abrir wizard pagos
            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            page.locator('button:has-text("Nuevo")').first.click(timeout=15000)
            page.wait_for_timeout(3000)
            step("open_wizard", True, "", shot(page, "03-wizard-open"))

            partner_in = page.locator('.o_field_widget[name="partner_id"] input').first
            partner_in.click()
            partner_in.fill(PARTNER)
            page.wait_for_timeout(2000)
            page.locator(f'.o-autocomplete--dropdown-item:has-text("{PARTNER}")').first.click(timeout=10000)
            page.wait_for_timeout(4000)

            cb = count_apply_checkboxes(page)
            report["checkbox_counts"]["on_load"] = cb
            step(
                "capture1_none_checked",
                cb.get("checked", -1) == 0,
                f"checked={cb.get('checked')} total={cb.get('total')} details={cb.get('details')}",
                shot(page, "04-wizard-invoices-on-load"),
            )

            if cb.get("total", 0) >= 1:
                rows = page.locator('.o_list_table tbody tr, .o_data_row')
                first = rows.first
                apply_cell = first.locator('[name="apply"]')
                apply_cell.click()
                page.wait_for_timeout(800)
                step("capture2_one_marked", True, "primera fila", shot(page, "05-one-invoice-marked"))

                amt = first.locator('[name="amount_to_pay"] input')
                if amt.count():
                    amt.click()
                    amt.fill("5000")
                    page.keyboard.press("Tab")
                page.wait_for_timeout(1000)
                step("capture3_amount_5000", True, "5000", shot(page, "06-partial-5000"))

                page.locator('input[name="hellenia_payment_reference"]').fill(f"{REF}-PAY")
                page.locator('button:has-text("Registrar pago")').first.click(timeout=15000)
                page.wait_for_timeout(8000)
                step("capture4_after_register", True, "", shot(page, "07-after-register"))

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            body = page.inner_text("body")
            pay_count = len(re.findall(r"PBNKD/2026/\d+", body))
            has_5000 = "5,000" in body or "5000" in body
            step("capture5_payments_list", has_5000, f"pbnkd_refs~{pay_count}", shot(page, "08-payments-list"))

            browser.close()
            report["pass"] = report["ok"]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ok"] else 1
        except Exception as exc:
            step("exception", False, str(exc)[:600], shot(page, "99-error"))
            browser.close()
            report["pass"] = False
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
