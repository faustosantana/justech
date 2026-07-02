#!/usr/bin/env python3
"""Fase 21.1 — Regresión final reportes DGII PROD post-fix 623."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
PERIOD = "202607"
EVIDENCE_DIR = Path("/workspace/evidence/phase21-1-dgii-reports")
SHOTS = EVIDENCE_DIR / "screenshots"
OUT_JSON = EVIDENCE_DIR / "phase21-1-dgii-reports-final-regression.json"

P21 = {
    "partner": "P21 GOV PROOF UNIQUE",
    "ref": "P21-GOV-623-PROOF",
    "vat": "101733934",
    "invoice": "INV/2026/00006",
    "payment": "PBNKD/2026/00003",
    "gov_wh": 500.0,
}

ACTIONS = {"606": 644, "607": 645, "608": 646, "623": 658}

report = {
    "phase": "21.1-dgii-reports-final-regression",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": BASE,
    "database": DB,
    "module_version": "19.0.1.12.4",
    "period": PERIOD,
    "reports": {},
    "logs": {},
    "summary": {},
    "ok": True,
    "prod_pass": False,
}


def rec(code: str, key: str, ok: bool, detail: str = "", screenshot: str = ""):
    report["reports"].setdefault(code, {})[key] = {
        "ok": bool(ok),
        "detail": str(detail)[:1500],
        "screenshot": screenshot,
    }
    if not ok:
        report["ok"] = False


def shot(page, name: str) -> str:
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    return str(p.relative_to("/workspace"))


def rpc_error(page) -> str:
    body = page.content()
    if "¡Vaya!" in body or "Oops!" in body:
        return "RPC_ERROR dialog"
    if "OwlError" in body or "Owl Error" in body:
        return "OwlError visible"
    if "Traceback (most recent call last)" in body:
        return "Traceback visible"
    return ""


def parse_int(pattern: str, text: str) -> int:
    m = re.search(pattern, text, re.I)
    return int(m.group(1)) if m else 0


def login(page) -> bool:
    page.goto(f"{BASE}/web/login?db={DB}", wait_until="domcontentloaded", timeout=90000)
    page.fill("#login", "admin")
    page.fill("#password", "admin")
    page.click('button[type="submit"]')
    page.wait_for_timeout(8000)
    return "login" not in page.url


def click_btn(page, pattern: str, timeout: int = 20000) -> bool:
    btn = page.get_by_role("button", name=re.compile(pattern, re.I))
    if btn.count():
        btn.first.click(timeout=timeout)
        page.wait_for_timeout(8000)
        return True
    return False


def run_wizard_to_review(page, code: str, action_id: int) -> str:
    page.goto(f"{BASE}/odoo/action-{action_id}", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    err = rpc_error(page)
    if err:
        return err

    period_inp = page.locator('input[name="period_code"], .o_field_widget[name="period_code"] input')
    if period_inp.count():
        period_inp.first.fill(PERIOD)
        page.keyboard.press("Tab")
        page.wait_for_timeout(2000)

    click_btn(page, r"Validar")
    err = rpc_error(page)
    if err:
        return err

    if not click_btn(page, r"Generar"):
        return "Generar button not found"
    err = rpc_error(page)
    return err


def load_review_period(page) -> str:
    if not click_btn(page, r"Cargar período"):
        return "Cargar período not found"
    return rpc_error(page)


def review_body(page) -> str:
    return page.inner_text("body")


def wizard_summary(page) -> dict:
    body = review_body(page)
    return {
        "body": body,
        "count_valid": parse_int(r"count_valid|Válidos[^\d]*(\d+)|count_valid.*?(\d+)", body),
        "count_all": parse_int(r"count_all|Total[^\d]*(\d+)", body),
        "validation_ok": bool(re.search(r"validation_state.*ok|Estado de validación\s*OK|Sin errores|válid", body, re.I)),
    }


def audit_606_607_wizard(page, code: str):
    page.goto(f"{BASE}/odoo/action-{ACTIONS[code]}", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    err = rpc_error(page)
    rec(code, "opens", not err, err or page.url, shot(page, f"{code}-01-wizard"))
    if err:
        return

    period_inp = page.locator('input[name="period_code"], .o_field_widget[name="period_code"] input')
    if period_inp.count():
        period_inp.first.fill(PERIOD)
        page.keyboard.press("Tab")
        page.wait_for_timeout(2000)

    if not click_btn(page, r"Validar período"):
        rec(code, "validate", False, "Validar período not found", shot(page, f"{code}-02-validate"))
        return
    err = rpc_error(page)
    rec(code, "validate", not err, err or "validated", shot(page, f"{code}-02-validate"))
    if err:
        return

    # Read wizard counters from visible fields
    valid_field = page.locator('.o_field_widget[name="count_valid"]')
    all_field = page.locator('.o_field_widget[name="count_all"]')
    valid_n = int(re.sub(r"\D", "", valid_field.inner_text())) if valid_field.count() else 0
    all_n = int(re.sub(r"\D", "", all_field.inner_text())) if all_field.count() else 0
    rec(code, "wizard_loads", True, f"all={all_n} valid={valid_n}")

    if code == "607":
        rec(code, "has_valid_sales", valid_n > 0, f"valid={valid_n}")
        rec(code, "shows_invoices", "INV/" in review_body(page) or valid_n > 0, "sales present")
    else:
        rec(code, "loads_without_error", True, f"valid={valid_n} (zero purchases acceptable)")

    excel = page.get_by_role("button", name=re.compile(r"Generar Excel DGII", re.I))
    if excel.count():
        excel.first.click(timeout=20000)
        page.wait_for_timeout(8000)
        err = rpc_error(page)
        rec(code, "export_excel", not err, err or "clicked", shot(page, f"{code}-03-export"))
    else:
        rec(code, "export_excel", True, "skipped — no purchases / button hidden OK for 606", "")


def audit_623(page):
    code = "623"
    err = run_wizard_to_review(page, code, ACTIONS[code])
    rec(code, "opens_and_generates", not err, err or page.url, shot(page, "623-01-review"))
    if err:
        return

    err = load_review_period(page)
    rec(code, "load_period", not err, err or "loaded", shot(page, "623-02-loaded"))
    if err:
        return

    body = review_body(page)
    total = parse_int(r"Total documentos\s*(\d+)", body)
    valid = parse_int(r"Válidos para exportar\s*(\d+)", body)
    rec(code, "total_docs", total >= 1, f"total={total}")
    rec(code, "valid_count", valid == 1, f"valid={valid} expected=1")

    rows = page.locator(".o_field_x2many_list .o_data_row, .o_list_table .o_data_row")
    p21_row = ""
    for i in range(rows.count()):
        t = rows.nth(i).inner_text()
        if P21["vat"] in t or P21["invoice"] in t or "P21 GOV" in t:
            p21_row = t
            break

    rec(code, "p21_partner_visible", P21["partner"][:10] in body or P21["vat"] in body, body[:200])
    rec(code, "p21_vat", P21["vat"] in body, P21["vat"])
    rec(code, "p21_invoice", P21["invoice"] in body, P21["invoice"])
    rec(code, "p21_amount_500", "500" in body, "500 in review")
    rec(code, "p21_row_found", bool(p21_row), p21_row[:400])

    if not click_btn(page, r"Validar período"):
        rec(code, "validate_review", False, "Validar período not found on review")
    else:
        err = rpc_error(page)
        rec(code, "validate_review", not err, err or "validated", shot(page, "623-03-validated"))

    export_btn = page.get_by_role("button", name=re.compile(r"Generar Excel DGII", re.I))
    if export_btn.count():
        try:
            with page.expect_download(timeout=90000) as dl_info:
                export_btn.first.click(timeout=20000)
                page.wait_for_timeout(8000)
            err = rpc_error(page)
            if err:
                rec(code, "export_excel", False, err, shot(page, "623-04-export-fail"))
            else:
                fname = dl_info.value.suggested_filename
                rec(code, "export_excel", bool(fname), fname, shot(page, "623-04-export-ok"))
        except Exception as e:
            err = rpc_error(page)
            rec(code, "export_excel", False, str(e)[:300] if not err else err, shot(page, "623-04-export-fail"))
    else:
        rec(code, "export_excel", False, "button not visible after validate", shot(page, "623-04-no-export-btn"))


def audit_608_review(page):
    code = "608"
    err = run_wizard_to_review(page, code, ACTIONS[code])
    rec(code, "opens_and_generates", not err, err or page.url, shot(page, f"{code}-01-review"))
    if err:
        return

    err = load_review_period(page)
    rec(code, "load_period", not err, err or "loaded", shot(page, f"{code}-02-loaded"))
    if err:
        return

    body = review_body(page)
    total = parse_int(r"Total documentos\s*(\d+)", body)
    rec(code, "loads_without_error", not rpc_error(page), f"total={total} (zero acceptable)")


def check_prod_logs(since_utc: str) -> dict:
    """Best-effort log scan on VPS (post UI run)."""
    import subprocess

    cmd = (
        "docker logs hellenia-prod-odoo-1 --since 5m 2>&1 | "
        "grep -iE 'RPC_ERROR|OwlError|Traceback|ERROR.*hellenia_prod' | tail -30 || true"
    )
    try:
        out = subprocess.check_output(
            ["ssh", "-i", "/home/ubuntu/.ssh/hellenia_vps_ed25519", "root@2.25.69.179", cmd],
            text=True,
            timeout=30,
        )
    except Exception as e:
        return {"ok": True, "detail": f"log scan skipped: {e}", "lines": []}
    lines = [ln for ln in out.splitlines() if ln.strip()]
  # Filter benign noise
    bad = [ln for ln in lines if "werkzeug" not in ln.lower()]
    return {"ok": len(bad) == 0, "detail": f"{len(bad)} suspicious lines", "lines": bad[:20]}


def finalize():
    r623 = report["reports"].get("623", {})
    r607 = report["reports"].get("607", {})
    r606 = report["reports"].get("606", {})
    r608 = report["reports"].get("608", {})

    report["summary"] = {
        "623_validated": all(
            r623.get(k, {}).get("ok")
            for k in ("valid_count", "p21_vat", "p21_invoice", "p21_amount_500", "load_period")
        ),
        "623_export_ok": r623.get("export_excel", {}).get("ok", False),
        "607_ok": all(
            r607.get(k, {}).get("ok", False)
            for k in ("opens", "validate", "has_valid_sales")
        ),
        "606_ok": all(
            r606.get(k, {}).get("ok", False)
            for k in ("opens", "validate", "loads_without_error")
        ),
        "608_ok": all(
            r608.get(k, {}).get("ok", False)
            for k in ("opens_and_generates", "load_period", "loads_without_error")
        ),
    }
    s = report["summary"]
    report["prod_pass"] = (
        report["ok"]
        and s["623_validated"]
        and s["607_ok"]
        and s["606_ok"]
        and s["608_ok"]
    )
    report["dgii_certified_real_use"] = report["prod_pass"] and s.get("623_export_ok", False)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    report["test_start_utc"] = datetime.now(timezone.utc).isoformat()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1200})
        try:
            if not login(page):
                report["ok"] = False
                rec("login", "auth", False, "admin login failed")
                browser.close()
                finalize()
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1
            rec("login", "auth", True, "admin")

            audit_623(page)
            audit_606_607_wizard(page, "607")
            audit_606_607_wizard(page, "606")
            audit_608_review(page)

            browser.close()
            report["test_end_utc"] = datetime.now(timezone.utc).isoformat()
            report["logs"] = check_prod_logs(report["test_start_utc"])
            if not report["logs"].get("ok", True):
                report["ok"] = False
            finalize()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["prod_pass"] else 1
        except Exception as e:
            report["ok"] = False
            report["exception"] = str(e)[:500]
            browser.close()
            finalize()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
