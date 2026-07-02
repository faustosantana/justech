#!/usr/bin/env python3
"""Fase 22 — Auditoría UI reportes financieros PROD."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
OUT = Path("/workspace/evidence/phase22-financial-reports-ui.json")
SHOTS = Path("/workspace/evidence/phase22-financial-reports/screenshots")

REPORTS = {
    "profit_loss": "/odoo/accounting/profit-and-loss",
    "balance_sheet": "/odoo/accounting/balance-sheet",
    "trial_balance": "/odoo/accounting/trial-balance",
    "general_ledger": "/odoo/accounting/general-ledger",
    "journal_report": "/odoo/accounting/journal-report",
    "partner_ledger": "/odoo/accounting/partner-ledger",
    "aged_receivable": "/odoo/accounting/aged-receivable",
    "aged_payable": "/odoo/accounting/aged-payable",
}

report = {"phase": "22-financial-ui", "timestamp_utc": datetime.now(timezone.utc).isoformat(), "reports": {}, "ok": True}


def rec(key, ok, detail="", shot=""):
    report["reports"][key] = {"ok": bool(ok), "detail": detail, "screenshot": shot}
    if not ok:
        report["ok"] = False


def rpc_err(page):
    b = page.content()
    if "¡Vaya!" in b or "Oops!" in b or "OwlError" in b:
        return "RPC/Owl"
    if "Traceback (most recent call last)" in b:
        return "Traceback"
    return ""


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1200})
        page.goto(f"{BASE}/web/login?db={DB}")
        page.fill("#login", "admin")
        page.fill("#password", "admin")
        page.click('button[type="submit"]')
        page.wait_for_timeout(8000)
        if "login" in page.url:
            rec("login", False, "fail")
            browser.close()
            OUT.write_text(json.dumps(report, indent=2))
            return 1

        for key, path in REPORTS.items():
            page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(6000)
            err = rpc_err(page)
            body = page.inner_text("body")
            shot = SHOTS / f"{key}.png"
            page.screenshot(path=str(shot), full_page=True)
            rec(f"{key}_opens", not err, err or path, str(shot.relative_to("/workspace")))
            rec(f"{key}_content", len(body) > 300, f"chars={len(body)}")
            pdf = page.get_by_role("button", name=re.compile(r"PDF|Imprimir|Print", re.I))
            xlsx = page.get_by_role("button", name=re.compile(r"XLSX|Excel|Export", re.I))
            rec(f"{key}_pdf", pdf.count() > 0, f"count={pdf.count()}")
            rec(f"{key}_xlsx", xlsx.count() > 0, f"count={xlsx.count()}")
            # Coherence hints
            if key == "trial_balance":
                rec(f"{key}_has_amounts", "RD$" in body or "0.00" in body, "amounts visible")
            if key == "profit_loss":
                rec(f"{key}_has_income", "Ingreso" in body or "Income" in body or "RD$" in body, "structure visible")
            if key == "balance_sheet":
                rec(f"{key}_has_assets", "Activo" in body or "Asset" in body or "RD$" in body, "structure visible")
            if key == "aged_receivable":
                rec(f"{key}_has_ar", "47200" in body.replace(",", "") or "47,200" in body or "Cliente" in body, "AR data")

        browser.close()
        OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
