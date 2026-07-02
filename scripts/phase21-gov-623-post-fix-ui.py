#!/usr/bin/env python3
"""Re-verificar 623 UI post-fix v12.3 con datos P21-GOV-623-PROOF."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
PARTNER_VAT = "101733934"
PARTNER_NAME = "P21 GOV"
PERIOD = "202607"
EVIDENCE = Path("/workspace/evidence/phase21-gov-623-proof")
report = {"phase": "21-gov-623-post-fix", "timestamp_utc": datetime.now(timezone.utc).isoformat(), "ok": False}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1200})
        page.goto(f"{BASE}/web/login?db={DB}")
        page.fill("#login", "admin")
        page.fill("#password", "admin")
        page.click('button[type="submit"]')
        page.wait_for_timeout(8000)
        page.goto(f"{BASE}/odoo/action-658", wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(6000)
        if "justech.do.fiscal.report" in page.url and "wizard" not in page.url:
            page.goto(f"{BASE}/odoo/action-658", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
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
        gen = page.get_by_role("button", name=re.compile("Generar", re.I))
        if gen.count():
            gen.first.click(timeout=15000)
            page.wait_for_timeout(12000)
        load = page.get_by_role("button", name=re.compile("Cargar período", re.I))
        if load.count():
            load.first.click(timeout=15000)
            page.wait_for_timeout(12000)
        body = page.inner_text("body")
        rows = page.locator(".o_field_x2many_list .o_data_row, .o_list_table .o_data_row")
        report["line_count"] = rows.count()
        report["has_vat"] = PARTNER_VAT in body
        report["has_500"] = "500" in body
        m_valid = re.search(r"Válidos para exportar\s*(\d+)", body)
        m_total = re.search(r"Total documentos\s*(\d+)", body)
        report["valid_count"] = int(m_valid.group(1)) if m_valid else 0
        report["total_docs"] = int(m_total.group(1)) if m_total else 0
        report["ok"] = report["line_count"] > 0 and PARTNER_VAT in body
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(EVIDENCE / "screenshots" / "12-623-post-fix.png"), full_page=True)
        (EVIDENCE / "post-fix-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
        browser.close()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
