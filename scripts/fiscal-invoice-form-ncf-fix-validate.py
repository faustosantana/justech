#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revalidación obligatoria: factura compra B01 marzo + set mínimo (carga completa)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence/fiscal-invoice-form-ncf-fix"
SESSION_FILE = Path("/tmp/fiscal_stabilize_session.json")

# IDs fijos del fallo + set obligatorio
DOCS = [
    ("purchase_b01_march", 1367, "B0100008679", "Histórico compatible"),
    ("sale_b01_march", 3037, "B0100000201", "Histórico compatible"),
    ("purchase_e31_march", 1377, "E310000002365", "Histórico compatible"),
    ("sale_b02_march", 2491, "B0200000035", "Histórico compatible"),
    ("credit_note", 4181, "B0400000022", "Válido"),
    ("new_justech", 4182, "B0300000004", "Válido"),
]

report = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "passed": False,
    "tests": {},
    "js_errors": [],
    "page_errors": [],
    "failed_requests": [],
}


def check(key, ok, detail=""):
    report["tests"][key] = {"ok": bool(ok), "detail": str(detail)[:1000]}


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


def open_move(page, mid, key, expected_ncf, expected_status):
    errors_before = len(report["js_errors"])
    page.goto(f"{page._base}/odoo/account.move/{mid}", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_selector(".o_form_view, .o_form_sheet, .o_action_manager", timeout=60000)
    page.wait_for_timeout(2500)
    tab = page.locator("a, button, .nav-link", has_text="Comprobante Fiscal")
    if tab.count():
        tab.first.click()
        page.wait_for_timeout(1200)
    body = page.inner_text("body")
    content = page.content()
    has_form = "o_form" in content
    no_rpc = "RPC_ERROR" not in content and "OwlError" not in content
    ncf_ok = expected_ncf in body
    tipo_ok = "Tipo de comprobante" in body or "Crédito Fiscal" in body or "Consumo" in body or "Nota de" in body or "B03" in body or "B04" in body
    status_ok = expected_status in body
    incomplete_bad = expected_ncf and "Incompleto" in body and expected_status != "Incompleto"
    # Prefer status field value: if Histórico compatible present, incomplete in manager group is ok
    # Manager group may still show stored dgii state — only fail if display status is Incompleto
    status_display_ok = expected_status in body and not (expected_status == "Histórico compatible" and False)
    new_js = report["js_errors"][errors_before:]
    owl_js = [e for e in new_js if "Owl" in e or "RPC" in e]
    check(f"{key}_form_loaded", has_form and no_rpc, {"url": page.url, "has_form": has_form})
    check(f"{key}_ncf_visible", ncf_ok, expected_ncf)
    check(f"{key}_tipo_visible", tipo_ok, body[:200])
    check(f"{key}_status", status_ok, expected_status)
    check(f"{key}_no_owl_rpc_js", len(owl_js) == 0, owl_js[:3])
    page.screenshot(path=str(EVIDENCE / f"{key}.png"), full_page=True)
    # RPC read of display fields
    rows = rpc(
        page,
        "account.move",
        "read",
        args=[[mid], ["fiscal_ncf_display", "fiscal_document_type_display", "fiscal_status_display",
                      "justech_do_ncf", "l10n_latam_document_number", "justech_do_dgii_fiscal_state"]],
    )
    rec = rows[0]
    check(f"{key}_rpc_ncf", rec.get("fiscal_ncf_display") == expected_ncf, rec)
    check(f"{key}_rpc_status", rec.get("fiscal_status_display") == expected_status, rec)
    check(f"{key}_no_incomplete_display", rec.get("fiscal_status_display") != "Incompleto", rec)
    return rec


def main():
    sess = json.loads(SESSION_FILE.read_text())
    base = sess["base_url"].rstrip("/")
    domain = urlparse(base).hostname or "erp.justech.do"
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
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
        page._base = base
        page.on("pageerror", lambda e: report["page_errors"].append(str(e)[:300]))
        page.on("console", lambda m: report["js_errors"].append(m.text[:300]) if m.type == "error" else None)

        def on_response(resp):
            if resp.status >= 400 and ("/web/" in resp.url or "/odoo/" in resp.url):
                report["failed_requests"].append({"url": resp.url[:200], "status": resp.status})

        page.on("response", on_response)

        # Warm assets once, then cold-open failing invoice FIRST
        page.goto(f"{base}/odoo", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(5000)

        for key, mid, ncf, status in DOCS:
            open_move(page, mid, key, ncf, status)

        # 4 companies: one hist each via RPC
        companies = rpc(
            page,
            "res.company",
            "search_read",
            args=[[["name", "ilike", "PlugSafe|Omni|Just Office|JUSTECH"]]],
            kwargs={"fields": ["name"], "limit": 20},
        )
        # simpler per-name
        for cname in ("PlugSafe", "Omni Solutions", "Just Office", "JUSTECH"):
            cos = rpc(page, "res.company", "search_read", args=[[["name", "ilike", cname]]], kwargs={"fields": ["name"], "limit": 1})
            if not cos:
                check(f"company_{cname}", False, "missing")
                continue
            cid = cos[0]["id"]
            rows = rpc(
                page,
                "account.move",
                "search_read",
                args=[[
                    ["company_id", "=", cid],
                    ["state", "=", "posted"],
                    ["move_type", "in", ["out_invoice", "in_invoice"]],
                    "|",
                    ["justech_do_ncf", "!=", False],
                    ["l10n_latam_document_number", "!=", False],
                ]],
                kwargs={
                    "fields": ["name", "fiscal_ncf_display", "fiscal_document_type_display", "fiscal_status_display"],
                    "limit": 2,
                    "order": "id desc",
                },
            )
            ok = bool(rows) and all(r.get("fiscal_ncf_display") and r.get("fiscal_document_type_display") and r.get("fiscal_status_display") != "Incompleto" for r in rows)
            check(f"company_{cname}", ok, rows)

        check("no_page_errors", len(report["page_errors"]) == 0, report["page_errors"][:5])
        check(
            "no_critical_http",
            not any(r["status"] >= 500 for r in report["failed_requests"]),
            report["failed_requests"][:5],
        )

        ctx.close()
        browser.close()

    report["passed"] = all(t["ok"] for t in report["tests"].values())
    (EVIDENCE / "validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
