#!/usr/bin/env python3
"""Fase 19.11 — Validación UI real wizard pagos en TEST (mismo código v25)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://test.hellenia.cloud"
DB = "hellenia_test"
LOGIN = "it@justech.do"
PASSWORD = "CertFiscal20!"
PARTNER = "SMOKE P13.4 CF"
EVIDENCE = Path("/workspace/evidence/phase19-11")
SHOTS = EVIDENCE / "screenshots-test"

report = {
    "phase": "19.11-test-ui-wizard",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": BASE_URL,
    "database": DB,
    "module_note": "TEST tiene hellenia_account 19.0.1.0.25 — mismo código que PROD pre-rollback",
    "steps": {},
    "ok": True,
    "pass": False,
}


def step(key: str, ok: bool, detail: str = "", shot: str = ""):
    report["steps"][key] = {"ok": ok, "detail": detail, "screenshot": shot}
    if not ok:
        report["ok"] = False


def screenshot(page, name: str) -> str:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to("/workspace"))


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        payments_before = 0

        try:
            page.goto(f"{BASE_URL}/web/login?db={DB}", wait_until="domcontentloaded", timeout=60000)
            page.fill("#login", LOGIN)
            page.fill("#password", PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_timeout(6000)

            if "login" in page.url:
                step("login", False, f"URL={page.url}", screenshot(page, "00-login-fail"))
                browser.close()
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1

            step("login", True, LOGIN, screenshot(page, "01-after-login"))

            page.goto(f"{BASE_URL}/odoo/customer-payments", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            step("open_payments", True, "", screenshot(page, "02-payments-list"))

            nuevo = page.locator('button:has-text("Nuevo")')
            nuevo.first.click(timeout=15000)
            page.wait_for_timeout(4000)
            step("open_wizard", True, "", screenshot(page, "03-wizard-open"))

            partner_input = page.locator('.o_field_widget[name="partner_id"] input').first
            partner_input.click()
            partner_input.fill(PARTNER)
            page.wait_for_timeout(2000)
            page.locator(f'.o-autocomplete--dropdown-item:has-text("{PARTNER}")').first.click(timeout=10000)
            page.wait_for_timeout(4000)
            step("partner_selected", True, PARTNER, screenshot(page, "04-wizard-invoices-loaded"))

            checked = page.locator('td[name="apply"] input[type="checkbox"]:checked').count()
            total = page.locator('td[name="apply"] input[type="checkbox"]').count()
            report["apply_on_load"] = {"checked": checked, "total": total}
            step(
                "none_checked_default",
                checked == 0,
                f"checked={checked} total={total}",
                screenshot(page, "05-apply-checkboxes-on-load"),
            )

            if total >= 1:
                boxes = page.locator('td[name="apply"] input[type="checkbox"]')
                boxes.first.check(force=True)
                page.wait_for_timeout(800)
                amt = page.locator('td[name="amount_to_pay"] input').first
                amt.click()
                amt.fill("5000")
                page.keyboard.press("Tab")
                page.wait_for_timeout(1000)
                step("select_one_5000", True, "primera factura", screenshot(page, "06-one-selected-5000"))

                reg = page.locator('button:has-text("Registrar pago")')
                reg.first.click(timeout=10000)
                page.wait_for_timeout(6000)
                step("register_clicked", True, "", screenshot(page, "07-after-register"))

            browser.close()
            report["pass"] = report["ok"]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ok"] else 1

        except Exception as exc:
            step("exception", False, str(exc)[:500], screenshot(page, "99-error"))
            browser.close()
            report["pass"] = False
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
