#!/usr/bin/env python3
"""Fase 20 — Playwright forense PROD v3: partner 22, wizard con factura existente."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
LOGIN, PASSWORD = "admin", "admin"
PARTNER_ID = 22
EVIDENCE = Path("/workspace/evidence/phase20-forensic")
SHOTS = EVIDENCE / "screenshots"

report = {
    "phase": "20-forensic-prod-v3",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "partner_id": PARTNER_ID,
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


def count_apply(page):
    return page.evaluate(
        """() => {
        const rows = [...document.querySelectorAll('.o_field_x2many_list .o_data_row')];
        const out = {total:0, checked:0, details:[]};
        for (const row of rows) {
            const ac = row.querySelector('[name="apply"]');
            if (!ac) continue;
            out.total++;
            const inp = ac.querySelector('input[type="checkbox"]');
            const chk = inp ? inp.checked : ac.classList.contains('o_field_boolean_true');
            if (chk) out.checked++;
            out.details.push({
                invoice: row.querySelector('[name="invoice_name"]')?.textContent?.trim(),
                checked: chk,
                amount: row.querySelector('[name="amount_to_pay"] input')?.value
                    || row.querySelector('[name="amount_to_pay"]')?.textContent?.trim(),
                residual: row.querySelector('[name="amount_residual"]')?.textContent?.trim(),
            });
        }
        const totalField = document.querySelector('[name="payment_total"]')?.textContent?.trim();
        out.payment_total_ui = totalField;
        return out;
    }"""
    )


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            page.goto(f"{BASE}/web/login?db={DB}")
            page.fill("#login", LOGIN)
            page.fill("#password", PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_timeout(8000)
            if "login" in page.url:
                step("login", False, "fail")
                browser.close()
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1
            step("login", True, LOGIN, screenshot(page, "v3-01-login"))

            page.goto(f"{BASE}/odoo/action-650/new?default_partner_id={PARTNER_ID}", wait_until="domcontentloaded")
            page.wait_for_timeout(8000)

            # Si partner no cargó, seleccionar manualmente
            if not page.locator('.o_field_widget[name="partner_id"] input').input_value():
                inp = page.locator('.o_field_widget[name="partner_id"] input').first
                inp.click()
                inp.fill("SMOKE P13.4 CF")
                page.wait_for_timeout(2000)
                items = page.locator(".o-autocomplete--dropdown-item")
                if items.count() >= 2:
                    items.nth(1).click()  # segundo duplicado = id 22 típicamente
                else:
                    items.first.click()
                page.wait_for_timeout(6000)

            cb = count_apply(page)
            report["checkbox"]["capture1"] = cb
            step(
                "capture1_on_load",
                cb.get("checked", 1) == 0,
                json.dumps(cb, ensure_ascii=False),
                screenshot(page, "v3-04-on-load"),
            )

            if cb.get("total", 0) < 1:
                step("has_invoices", False, "sin líneas en wizard")
                browser.close()
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1

            row = page.locator(".o_field_x2many_list .o_data_row").first
            apply_inp = row.locator('[name="apply"] input[type="checkbox"]')
            if apply_inp.count() and not apply_inp.is_checked():
                apply_inp.click()
            page.wait_for_timeout(800)
            step("capture2_one_marked", True, "", screenshot(page, "v3-05-one-marked"))

            amt = row.locator('[name="amount_to_pay"] input')
            amt.click()
            amt.fill("5000")
            page.keyboard.press("Tab")
            page.wait_for_timeout(1000)
            step("capture3_5000", True, "", screenshot(page, "v3-06-5000"))

            page.locator('input[name="hellenia_payment_reference"]').fill("P20-FORENSIC-PAY")
            page.locator('button:has-text("Registrar pago")').first.click(timeout=20000)
            page.wait_for_timeout(12000)
            step("capture4_after_register", True, "", screenshot(page, "v3-07-after-register"))

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            body = page.inner_text("body")
            has_5k = ("5,000" in body) or ("5000" in body)
            has_multi_11800 = body.count("11,800") > 2
            step(
                "capture5_payments",
                has_5k and not has_multi_11800,
                f"has_5k={has_5k} extra_11800={has_multi_11800}",
                screenshot(page, "v3-08-payments"),
            )

            browser.close()
            report["pass"] = report["ok"]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ok"] else 1
        except Exception as exc:
            step("exception", False, str(exc)[:500], screenshot(page, "v3-99-error"))
            browser.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
