#!/usr/bin/env python3
"""Fase 21 — Auditoría UI PROD: reportes DGII + contables."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
EVIDENCE = Path("/workspace/evidence/phase21-prod-reports")
SHOTS = EVIDENCE / "screenshots"
EVIDENCE.mkdir(parents=True, exist_ok=True)

report = {
    "phase": "21-prod-ui-full",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": BASE,
    "database": DB,
    "dgii": {},
    "accounting": {},
    "ok": True,
    "pass": False,
}

DGII_ACTIONS = {
    "606": 644,
    "607": 645,
    "608": 646,
    "623": 658,
}

ACCOUNTING_URLS = {
    "general_ledger": "/odoo/accounting/general-ledger",
    "trial_balance": "/odoo/accounting/trial-balance",
    "balance_sheet": "/odoo/accounting/balance-sheet",
    "profit_loss": "/odoo/accounting/profit-and-loss",
    "partner_ledger": "/odoo/accounting/partner-ledger",
    "aged_receivable": "/odoo/accounting/aged-receivable",
    "journal_report": "/odoo/accounting/journal-report",
}


def step(section: str, key: str, ok: bool, detail: str = "", shot: str = ""):
    report.setdefault(section, {})[key] = {"ok": ok, "detail": detail, "screenshot": shot}
    if not ok:
        report["ok"] = False


def screenshot(page, name: str) -> str:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to("/workspace"))


def has_rpc_error(page) -> str:
    body = page.content()
    if "¡Vaya!" in body or "Oops!" in body:
        return "RPC error dialog"
    if "Traceback" in body and "Error" in body:
        return "Traceback visible"
    return ""


def login(page) -> bool:
    page.goto(f"{BASE}/web/login?db={DB}", wait_until="domcontentloaded", timeout=90000)
    page.fill("#login", "admin")
    page.fill("#password", "admin")
    page.click('button[type="submit"]')
    page.wait_for_timeout(8000)
    if "login" in page.url:
        return False
    return True


def audit_dgii(page, code: str, action_id: int) -> None:
    url = f"{BASE}/odoo/action-{action_id}"
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    err = has_rpc_error(page)
    step("dgii", f"{code}_opens", not err, err or url, screenshot(page, f"dgii-{code}-open"))
    if err:
        return

    # Wizard should show report type
    body = page.inner_text("body")
    step("dgii", f"{code}_wizard", code in body or "Período" in body, f"visible labels", "")

    period = "202606" if code != "623" else "202607"
    period_inp = page.locator('input[name="period_code"], .o_field_widget[name="period_code"] input')
    if period_inp.count():
        period_inp.first.fill(period)
        page.keyboard.press("Tab")
        page.wait_for_timeout(2000)

    validate_btn = page.get_by_role("button", name=re.compile("Validar", re.I))
    if validate_btn.count():
        validate_btn.first.click(timeout=15000)
        page.wait_for_timeout(8000)
        err = has_rpc_error(page)
        step("dgii", f"{code}_validate", not err, err or "validated", screenshot(page, f"dgii-{code}-validate"))

    generate_btn = page.get_by_role("button", name=re.compile("Generar", re.I))
    if generate_btn.count():
        generate_btn.first.click(timeout=15000)
        page.wait_for_timeout(10000)
        err = has_rpc_error(page)
        step("dgii", f"{code}_generate", not err, err or page.url, screenshot(page, f"dgii-{code}-generate"))


def audit_accounting(page, key: str, path: str) -> None:
    url = f"{BASE}{path}"
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(6000)
    err = has_rpc_error(page)
    step("accounting", f"{key}_opens", not err, err or url, screenshot(page, f"acct-{key}-open"))
    if err:
        return

    body = page.inner_text("body")
    step("accounting", f"{key}_content", len(body) > 200, f"chars={len(body)}", "")

    pdf_btn = page.get_by_role("button", name=re.compile("PDF|Imprimir|Print", re.I))
    xlsx_btn = page.get_by_role("button", name=re.compile("XLSX|Excel|Export", re.I))
    step("accounting", f"{key}_pdf_btn", pdf_btn.count() > 0, f"count={pdf_btn.count()}", "")
    step("accounting", f"{key}_xlsx_btn", xlsx_btn.count() > 0, f"count={xlsx_btn.count()}", "")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1200})
        try:
            if not login(page):
                step("dgii", "login", False, "admin login failed", screenshot(page, "login-fail"))
                browser.close()
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1
            step("dgii", "login", True, "admin", screenshot(page, "login-ok"))

            for code, aid in DGII_ACTIONS.items():
                audit_dgii(page, code, aid)

            for key, path in ACCOUNTING_URLS.items():
                audit_accounting(page, key, path)

            dgii_ok = all(v.get("ok") for k, v in report.get("dgii", {}).items() if k.endswith("_opens"))
            acct_opens = all(v.get("ok") for k, v in report.get("accounting", {}).items() if k.endswith("_opens"))
            report["pass"] = report["ok"] and dgii_ok and acct_opens
            browser.close()
            out = EVIDENCE / "ui-audit-full.json"
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["pass"] else 1
        except Exception as e:
            step("dgii", "exception", False, str(e)[:500], screenshot(page, "exception"))
            browser.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
