#!/usr/bin/env python3
"""Fase 20.1 — Playwright TEST: wizard pagos (partner_id explícito, sin búsqueda por nombre)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://test.hellenia.cloud"
DB = "hellenia_test"
LOGIN, PASSWORD = "it@justech.do", "CertFiscal20!"
PARTNER_ID = 2361
PARTNER_REF = "SMOKE-P134-CF-2361"
PARTIAL = 5000.0
EVIDENCE = Path("/workspace/evidence/phase20-1")
SHOTS = EVIDENCE / "screenshots"
VIDEO = EVIDENCE / "video"

report = {
    "phase": "20.1-playwright-test",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": BASE,
    "partner_id": PARTNER_ID,
    "partner_ref": PARTNER_REF,
    "steps": {},
    "checkbox_on_load": {},
    "ok": True,
    "pass": False,
}


def step(k, ok, detail="", shot=""):
    report["steps"][k] = {"ok": bool(ok), "detail": detail, "screenshot": shot}
    if not ok:
        report["ok"] = False


def shot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    return str(p.relative_to("/workspace"))


def parse_money(text):
    if not text:
        return 0.0
    digits = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


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
            const chk = inp ? inp.checked : false;
            if (chk) out.checked++;
            const amtInp = row.querySelector('[name="amount_to_pay"] input');
            const amtCell = row.querySelector('[name="amount_to_pay"]');
            const amt = amtInp ? amtInp.value : (amtCell?.textContent?.trim() || '');
            out.details.push({
                invoice: row.querySelector('[name="invoice_name"]')?.textContent?.trim(),
                checked: chk,
                amount_to_pay: amt,
                amount_to_pay_num: parseFloat((amt||'').replace(/[^\\d.]/g,'')) || 0,
            });
        }
        out.payment_total = document.querySelector('[name="payment_total"]')?.textContent?.trim();
        out.payment_total_num = parseFloat((out.payment_total||'').replace(/[^\\d.]/g,'')) || 0;
        return out;
    }"""
    )


def select_partner_by_id(page):
    """Selecciona partner exclusivamente por partner_id (ref único o id en autocomplete)."""
    inp = page.locator('.o_field_widget[name="partner_id"] input').first
    inp.click()
    inp.fill("")
    page.wait_for_timeout(500)
    inp.fill(PARTNER_REF)
    page.wait_for_timeout(2000)
    item = page.locator(".o-autocomplete--dropdown-item").filter(
        has_text=re.compile(str(PARTNER_ID))
    )
    if item.count() == 0:
        inp.fill(str(PARTNER_ID))
        page.wait_for_timeout(2000)
        item = page.locator(".o-autocomplete--dropdown-item").first
    item.first.click()
    page.wait_for_timeout(6000)


def set_row_apply(page, row_index, checked):
    rows = page.locator(".o_field_x2many_list .o_data_row")
    cell = rows.nth(row_index).locator('td[name="apply"]')
    cell.click(force=True)
    page.wait_for_timeout(600)
    state = count_apply(page)
    row = state["details"][row_index] if row_index < len(state.get("details", [])) else {}
    if bool(row.get("checked")) != checked:
        cell.click(force=True)
        page.wait_for_timeout(600)


def uncheck_all(page):
    state = count_apply(page)
    for i, d in enumerate(state.get("details", [])):
        if d.get("checked"):
            set_row_apply(page, i, False)
    return count_apply(page)


def main():
    data_file = EVIDENCE / "smoke-test-data.json"
    target_invoice = None
    if data_file.exists():
        data = json.loads(data_file.read_text(encoding="utf-8"))
        invs = data.get("invoices") or []
        if invs:
            target_invoice = invs[0]["name"]

    VIDEO.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(VIDEO),
        )
        page = context.new_page()
        try:
            page.goto(f"{BASE}/web/login?db={DB}")
            page.fill("#login", LOGIN)
            page.fill("#password", PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_timeout(8000)
            if "login" in page.url:
                step("login", False, "credencial falló")
                context.close()
                browser.close()
                print(json.dumps(report, indent=2, ensure_ascii=False))
                return 1
            step("login", True, LOGIN, shot(page, "01-login"))

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            page.locator('button:has-text("Nuevo")').first.click()
            page.wait_for_timeout(4000)

            select_partner_by_id(page)
            cb = count_apply(page)
            report["checkbox_on_load"] = cb
            step(
                "01_wizard_none_checked",
                cb.get("checked", 99) == 0 and cb.get("total", 0) >= 3,
                json.dumps(cb, ensure_ascii=False),
                shot(page, "02-wizard-on-load"),
            )
            amounts_ok = all(
                (not d.get("checked")) and parse_money(str(d.get("amount_to_pay", ""))) < 0.01
                for d in cb.get("details", [])
            )
            total_ok = parse_money(str(cb.get("payment_total", ""))) < 0.01
            step(
                "01_amount_zero_on_load",
                amounts_ok and total_ok,
                f"amounts_ok={amounts_ok} total_ok={total_ok}",
            )

            cb = uncheck_all(page)
            step("01b_uncheck_all", cb.get("checked", 1) == 0, json.dumps(cb, ensure_ascii=False))

            rows = page.locator(".o_field_x2many_list .o_data_row")
            target_idx = 0
            if target_invoice:
                for i, d in enumerate(cb.get("details", [])):
                    if target_invoice in (d.get("invoice") or ""):
                        target_idx = i
                        break
            set_row_apply(page, target_idx, True)
            page.wait_for_timeout(1000)
            cb = count_apply(page)
            step(
                "02_one_marked",
                cb.get("checked", 0) == 1,
                json.dumps(cb, ensure_ascii=False),
                shot(page, "03-one-marked"),
            )

            amt = rows.nth(target_idx).locator('[name="amount_to_pay"] input')
            amt.click(force=True)
            amt.fill("")
            amt.fill(str(int(PARTIAL)))
            page.keyboard.press("Tab")
            page.wait_for_timeout(1500)
            cb = count_apply(page)
            step(
                "03_partial_5000",
                cb.get("checked", 0) == 1
                and any(
                    abs(d.get("amount_to_pay_num", 0) - PARTIAL) < 0.01
                    for d in cb.get("details", [])
                    if d.get("checked")
                ),
                json.dumps(cb, ensure_ascii=False),
                shot(page, "04-partial-5000"),
            )

            page.locator('button:has-text("Registrar pago")').first.click(timeout=25000)
            page.wait_for_timeout(15000)
            step("04_register", "account.payment" in page.url, page.url, shot(page, "05-after-register"))

            page.goto(f"{BASE}/odoo/customer-payments", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            body = page.inner_text("body")
            payments_5k = body.count("5,000") + body.count("5000")
            step("05_one_payment_5k", payments_5k >= 1, f"count_5k={payments_5k}", shot(page, "06-payments"))

            context.close()
            browser.close()
            vfiles = list(VIDEO.glob("*.webm"))
            report["video"] = str(vfiles[0].relative_to("/workspace")) if vfiles else ""
            report["pass"] = report["ok"]
            (EVIDENCE / "playwright-report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if report["ok"] else 1
        except Exception as exc:
            step("exception", False, str(exc)[:500], shot(page, "99-error"))
            context.close()
            browser.close()
            (EVIDENCE / "playwright-report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 1


if __name__ == "__main__":
    sys.exit(main())
