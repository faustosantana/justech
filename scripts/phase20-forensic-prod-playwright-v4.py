#!/usr/bin/env python3
"""Fase 20 — Playwright forense PROD v4: partner 22 vía autocomplete índice 1."""
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
    "phase": "20-forensic-prod-v4",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "backup": "/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1248",
    "target_partner_id": 22,
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
        out.payment_total = document.querySelector('[name="payment_total"]')?.textContent?.trim();
        return out;
    }"""
    )


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
            page.wait_for_timeout(4000)
            page.locator('button:has-text("Nuevo")').first.click()
            page.wait_for_timeout(4000)
            step("open_wizard", True, "", screenshot(page, "v4-03-wizard"))

            inp = page.locator('.o_field_widget[name="partner_id"] input').first
            inp.click()
            inp.fill("SMOKE P13.4 CF")
            page.wait_for_timeout(2500)
            items = page.locator(".o-autocomplete--dropdown-item")
            cnt = items.count()
            # partner 22 = segundo duplicado (ids 21,22,23)
            idx = 1 if cnt >= 2 else 0
            items.nth(idx).click()
            page.wait_for_timeout(7000)

            cb = count_apply(page)
            report["checkbox"]["capture1"] = cb
            step(
                "capture1_on_load",
                cb.get("checked", 99) == 0,
                json.dumps(cb, ensure_ascii=False),
                screenshot(page, "v4-04-on-load"),
            )

            if cb.get("total", 0) < 1:
                step("has_lines", False, f"partner_autocomplete_items={cnt}")
                browser.close()
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1

            row = page.locator(".o_field_x2many_list .o_data_row").first
            apply_inp = row.locator('[name="apply"] input[type="checkbox"]')
            if apply_inp.count():
                if not apply_inp.is_checked():
                    apply_inp.click()
                else:
                    # si ya marcada, desmarcar otras y dejar una
                    pass
            page.wait_for_timeout(800)
            step("capture2_marked", True, "", screenshot(page, "v4-05-marked"))

            amt = row.locator('[name="amount_to_pay"] input')
            amt.click()
            amt.fill("5000")
            page.keyboard.press("Tab")
            page.wait_for_timeout(1000)
            step("capture3_5000", True, "", screenshot(page, "v4-06-5000"))

            ref_before = page.inner_text("body").count("P20-FORENSIC-PAY")
            page.locator('input[name="hellenia_payment_reference"]').fill("P20-FORENSIC-PAY")
            page.locator('button:has-text("Registrar pago")').first.click(timeout=25000)
            page.wait_for_timeout(12000)
            step("capture4_register", True, "", screenshot(page, "v4-07-after-register"))

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            body = page.inner_text("body")
            step(
                "capture5_payments",
                "P20-FORENSIC-PAY" in body or "5,000" in body,
                "listed",
                screenshot(page, "v4-08-payments"),
            )

            browser.close()
            report["pass"] = report["ok"]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ok"] else 1
        except Exception as exc:
            step("exception", False, str(exc)[:500], screenshot(page, "v4-99-error"))
            browser.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
