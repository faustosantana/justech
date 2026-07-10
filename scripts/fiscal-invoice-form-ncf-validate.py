#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación visual: NCF histórico Adel visible en formulario de factura."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence/fiscal-invoice-form-ncf"
SESSION_FILE = Path("/tmp/fiscal_stabilize_session.json")

# IDs known from shell validation (justech_dev)
SAMPLES = {
    "purchase_b01_march": None,  # filled via RPC search
    "purchase_e31_march": None,
    "sale_b01_march": None,
    "sale_b02_march": None,
}

report = {"ts": datetime.now(timezone.utc).isoformat(), "passed": False, "tests": {}, "js_errors": []}


def check(key, ok, detail=""):
    report["tests"][key] = {"ok": bool(ok), "detail": str(detail)[:900]}


def rpc(page, model, method, args=None, kwargs=None):
    return page.evaluate(
        """async ({model, method, args, kwargs}) => {
        const r = await fetch('/web/dataset/call_kw/' + model + '/' + method, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc:'2.0', method:'call', id:1,
                params:{model, method, args: args||[], kwargs: kwargs||{}}})
        });
        const data = await r.json();
        if (data.error) throw new Error(JSON.stringify(data.error));
        return data.result;
    }""",
        {"model": model, "method": method, "args": args or [], "kwargs": kwargs or {}},
    )


def main():
    sess = json.loads(SESSION_FILE.read_text())
    base = sess["base_url"].rstrip("/")
    domain = urlparse(base).hostname or "erp.justech.do"
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="light")
        ctx.add_cookies(
            [
                {
                    "name": "session_id",
                    "value": sess["session_id"],
                    "domain": domain,
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                }
            ]
        )
        page = ctx.new_page()
        page.on("console", lambda m: report["js_errors"].append(m.text[:200]) if m.type == "error" else None)
        page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(5000)

        queries = [
            ("purchase_b01_march", [["name", "=", "FP/2026/03/0001"]]),
            ("purchase_e31_march", [["name", "=", "FP/2026/03/0004"]]),
            (
                "sale_b01_march",
                [
                    ["state", "=", "posted"],
                    ["move_type", "=", "out_invoice"],
                    ["l10n_latam_document_number", "=ilike", "B01%"],
                    ["justech_do_ncf", "=", False],
                    ["invoice_date", ">=", "2026-03-01"],
                    ["invoice_date", "<=", "2026-03-31"],
                ],
            ),
            (
                "sale_b02_march",
                [
                    ["state", "=", "posted"],
                    ["move_type", "=", "out_invoice"],
                    ["l10n_latam_document_number", "=ilike", "B02%"],
                    ["justech_do_ncf", "=", False],
                    ["invoice_date", ">=", "2026-03-01"],
                    ["invoice_date", "<=", "2026-03-31"],
                ],
            ),
            (
                "purchase_e31_hist",
                [
                    ["state", "=", "posted"],
                    ["move_type", "=", "in_invoice"],
                    ["l10n_latam_document_number", "=ilike", "E31%"],
                    ["justech_do_ncf", "=", False],
                ],
            ),
            (
                "credit_note",
                [
                    ["state", "=", "posted"],
                    ["move_type", "in", ["out_refund", "in_refund"]],
                    "|",
                    ["justech_do_ncf", "!=", False],
                    ["l10n_latam_document_number", "!=", False],
                ],
            ),
            (
                "new_justech_sale",
                [
                    ["state", "=", "posted"],
                    ["move_type", "=", "out_invoice"],
                    ["justech_do_ncf", "!=", False],
                ],
            ),
            (
                "new_justech_purchase",
                [
                    ["state", "=", "posted"],
                    ["move_type", "=", "in_invoice"],
                    ["justech_do_ncf", "!=", False],
                ],
            ),
        ]

        first_mid = None
        for key, domain_q in queries:
            rows = rpc(
                page,
                "account.move",
                "search_read",
                args=[domain_q],
                kwargs={
                    "fields": [
                        "name",
                        "move_type",
                        "justech_fiscal_ncf",
                        "justech_fiscal_document_type",
                        "justech_fiscal_source",
                        "justech_fiscal_status",
                        "justech_fiscal_expense_type",
                        "justech_fiscal_income_type",
                        "justech_fiscal_partner_vat",
                        "justech_do_ncf",
                        "l10n_latam_document_number",
                    ],
                    "limit": 1,
                    "order": "id desc",
                },
            )
            if not rows:
                check(f"{key}_found", False, "no record")
                continue
            rec = rows[0]
            mid = rec["id"]
            if first_mid is None:
                first_mid = mid
            has_source = bool(rec.get("justech_do_ncf") or rec.get("l10n_latam_document_number"))
            check(f"{key}_ncf", bool(rec.get("justech_fiscal_ncf")) or not has_source, rec)
            check(f"{key}_tipo", bool(rec.get("justech_fiscal_document_type")) or not has_source, rec)
            check(f"{key}_origen", bool(rec.get("justech_fiscal_source")), rec)

            page.goto(f"{base}/odoo/account.move/{mid}", wait_until="domcontentloaded", timeout=120000)
            try:
                page.wait_for_selector(".o_form_view, .o_form_sheet, .o_content", timeout=30000)
            except Exception:
                page.wait_for_timeout(5000)
                page.reload(wait_until="domcontentloaded", timeout=120000)
                page.wait_for_timeout(5000)
            page.wait_for_timeout(2000)
            # open fiscal tab if present
            tab = page.locator("a, button, .nav-link", has_text="Comprobante Fiscal")
            for _ in range(3):
                if tab.count():
                    tab.first.click()
                    page.wait_for_timeout(1500)
                    break
                page.wait_for_timeout(2000)
            content = page.content()
            ncf = rec.get("justech_fiscal_ncf") or ""
            tipo = rec.get("justech_fiscal_document_type") or ""
            # Prefer visible text from fiscal fields over raw HTML race
            body_text = page.inner_text("body") if page.locator("body").count() else content
            ui_ok = (
                "RPC_ERROR" not in content
                and "o_form" in content
                and (not ncf or ncf in body_text or ncf in content)
            )
            check(
                f"{key}_form_ui",
                ui_ok,
                {"url": page.url, "ncf": ncf, "tipo": tipo, "has_form": "o_form" in content},
            )
            page.screenshot(path=str(EVIDENCE / f"{key}.png"), full_page=True)

        # dark mode smoke
        ctx2 = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        ctx2.add_cookies(
            [
                {
                    "name": "session_id",
                    "value": sess["session_id"],
                    "domain": domain,
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                }
            ]
        )
        page2 = ctx2.new_page()
        dark_id = first_mid or 1
        page2.goto(f"{base}/odoo/account.move/{dark_id}", wait_until="domcontentloaded", timeout=120000)
        page2.wait_for_timeout(3000)
        check("dark_form", "RPC_ERROR" not in page2.content())
        page2.screenshot(path=str(EVIDENCE / "dark_form.png"), full_page=True)
        ctx2.close()
        ctx.close()
        browser.close()

    check("no_js_errors", len(report["js_errors"]) == 0, report["js_errors"][:3])
    report["passed"] = all(t["ok"] for t in report["tests"].values())
    (EVIDENCE / "visual_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
