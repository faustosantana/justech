#!/usr/bin/env python3
"""Fase 20 — Playwright PROD v6: registrar pago parcial (scroll + register)."""
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

report = {"phase": "20-v6", "timestamp_utc": datetime.now(timezone.utc).isoformat(), "steps": {}, "ok": True, "pass": False}


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
        page = browser.new_page(viewport={"width": 1920, "height": 1200})
        try:
            page.goto(f"{BASE}/web/login?db={DB}")
            page.fill("#login", "admin")
            page.fill("#password", "admin")
            page.click('button[type="submit"]')
            page.wait_for_timeout(8000)
            page.goto(f"{BASE}/odoo/customer-payments")
            page.wait_for_timeout(3000)
            page.locator('button:has-text("Nuevo")').first.click()
            page.wait_for_timeout(4000)
            inp = page.locator('.o_field_widget[name="partner_id"] input').first
            inp.click()
            inp.fill("SMOKE P13.4 CF")
            page.wait_for_timeout(2000)
            page.locator(".o-autocomplete--dropdown-item").nth(1).click()
            page.wait_for_timeout(7000)
            row = page.locator(".o_field_x2many_list .o_data_row").first
            row.locator('[name="apply"]').click(force=True)
            page.wait_for_timeout(1000)
            amt = row.locator('[name="amount_to_pay"] input')
            amt.click(force=True)
            amt.fill("5000")
            page.keyboard.press("Tab")
            page.wait_for_timeout(1500)
            step("before_register", True, "", screenshot(page, "v6-06-5000"))
            page.locator('button:has-text("Registrar pago")').first.click(timeout=25000)
            page.wait_for_timeout(18000)
            step("after_register", True, page.url, screenshot(page, "v6-07-after"))
            browser.close()
            report["pass"] = report["ok"]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        except Exception as e:
            step("exception", False, str(e)[:400], screenshot(page, "v6-99"))
            browser.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
