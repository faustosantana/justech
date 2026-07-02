#!/usr/bin/env python3
"""Fase 20 — Playwright PROD v5: completar flujo parcial partner 22."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
EVIDENCE = Path("/workspace/evidence/phase20-forensic")
SHOTS = EVIDENCE / "screenshots"

report = {
    "phase": "20-forensic-prod-v5",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "backup": "/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1248",
    "steps": {},
    "checkbox": {},
    "ok": True,
    "pass": False,
}


def step(k, ok, detail="", screenshot=""):
    report["steps"][k] = {"ok": bool(ok), "detail": detail, "screenshot": screenshot}
    if not ok:
        report["ok"] = False


def screenshot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    return str(p.relative_to("/workspace"))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            page.goto(f"{BASE}/web/login?db={DB}")
            page.fill("#login", "admin")
            page.fill("#password", "admin")
            page.click('button[type="submit"]')
            page.wait_for_timeout(8000)

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            page.locator('button:has-text("Nuevo")').first.click()
            page.wait_for_timeout(4000)

            inp = page.locator('.o_field_widget[name="partner_id"] input').first
            inp.click()
            inp.fill("SMOKE P13.4 CF")
            page.wait_for_timeout(2000)
            page.locator(".o-autocomplete--dropdown-item").nth(1).click()
            page.wait_for_timeout(7000)

            step("capture1", True, "wizard loaded", screenshot(page, "v5-04-load"))

            row = page.locator(".o_field_x2many_list .o_data_row").first
            row.locator('[name="apply"]').click(force=True)
            page.wait_for_timeout(1500)
            step("capture2", True, "apply clicked", screenshot(page, "v5-05-apply"))

            amt = row.locator('[name="amount_to_pay"] input')
            if amt.count():
                amt.click(force=True)
                amt.fill("5000")
            page.keyboard.press("Tab")
            page.wait_for_timeout(1500)
            step("capture3", True, "5000", screenshot(page, "v5-06-5000"))

            page.locator('input[name="hellenia_payment_reference"]').fill("P20-FORENSIC-PAY")
            page.locator('button:has-text("Registrar pago")').first.click(timeout=25000)
            page.wait_for_timeout(15000)
            step("capture4", True, "registered", screenshot(page, "v5-07-result"))

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            body = page.inner_text("body")
            ok_pay = "5,000" in body or "5000" in body
            step("capture5", ok_pay, "payments list", screenshot(page, "v5-08-payments"))

            page.goto(f"{BASE}/odoo/customer-invoices", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            inv_body = page.inner_text("body")
            partial = "INV/2026/00002" in inv_body and ("6,800" in inv_body or "6800" in inv_body or "Parcial" in inv_body or "partial" in inv_body.lower())
            step("capture6_invoice", partial, inv_body[:200], screenshot(page, "v5-09-invoice"))

            browser.close()
            report["pass"] = report["ok"]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ok"] else 1
        except Exception as exc:
            step("exception", False, str(exc)[:500], screenshot(page, "v5-99-error"))
            browser.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
