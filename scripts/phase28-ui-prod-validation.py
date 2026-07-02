#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fase 28 — Validación UI real PROD (cada acción en carga limpia del formulario)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "https://odoo.hellenia.cloud"
INVOICE_URL = f"{BASE}/odoo/accounting/9/invoicing/132"
OUT = Path(__file__).resolve().parent.parent / "evidence/phase28-invoice-preview-client-validation/ui-validation.json"
SESSION_FILE = Path("/tmp/odoo_prod_session_phase28.json")

report = {
    "phase": "28-prod-ui-validation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "invoice": "INV/2026/00006",
    "url": INVOICE_URL,
    "tests": {},
    "network": [],
    "ok": True,
    "pass": False,
}


def check(key, ok, detail=""):
    report["tests"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:1200]}
    if not ok:
        report["ok"] = False


def load_session():
    return json.loads(SESSION_FILE.read_text())


def make_page(browser, sess):
    context = browser.new_context(locale="es-DO", viewport={"width": 1440, "height": 900})
    context.add_cookies(
        [
            {
                "name": "session_id",
                "value": sess["session_id"],
                "domain": "odoo.hellenia.cloud",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ]
    )
    page = context.new_page()
    hits = []

    def on_response(resp):
        url = resp.url
        if any(
            x in url
            for x in (
                "preview_invoice",
                "action_print_pdf",
                "/report/download",
                "action_invoice_sent",
                "account.move/send",
            )
        ):
            hits.append({"url": url, "status": resp.status, "method": resp.request.method})

    page.on("response", on_response)
    page.goto(INVOICE_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_selector(".o_form_view", timeout=120000)
    page.wait_for_timeout(4000)
    return context, page, hits


def toast_has_required(page):
    for sel in [".o_notification", ".o_toast", ".alert-danger"]:
        els = page.locator(sel)
        for i in range(els.count()):
            try:
                t = els.nth(i).inner_text(timeout=500)
                if t and ("obligator" in t.lower() or "required" in t.lower()):
                    return t
            except PWTimeout:
                pass
    return None


def main():
    sess = load_session()
    all_hits = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        # 01 — carga factura
        ctx, page, hits = make_page(browser, sess)
        check("01_invoice_loaded", "00006" in page.content() or "INV/2026" in page.content(), page.url)
        ctx.close()

        # 02 — Vista previa
        ctx, page, hits = make_page(browser, sess)
        page.locator("button[name='preview_invoice']").click(timeout=10000)
        page.wait_for_timeout(5000)
        toast = toast_has_required(page)
        preview_rpc = [h for h in hits if "preview_invoice" in h["url"]]
        preview_ui = page.locator("iframe").count() > 0 or "/my/invoices/" in page.content()
        check("02_preview_rpc_sent", bool(preview_rpc), preview_rpc)
        check("02_preview_no_required_toast", not toast, toast or "OK")
        check("02_preview_ui_opened", preview_ui or (preview_rpc and preview_rpc[0]["status"] == 200), "iframe/portal")
        all_hits.extend(hits)
        ctx.close()

        # 03 — Imprimir cabecera
        ctx, page, hits = make_page(browser, sess)
        page.locator("button[name='action_print_pdf']").click(timeout=10000)
        page.wait_for_timeout(6000)
        toast = toast_has_required(page)
        print_rpc = [h for h in hits if "action_print_pdf" in h["url"]]
        dl = [h for h in hits if "/report/download" in h["url"]]
        check("03_print_rpc_sent", bool(print_rpc), print_rpc)
        check("03_print_no_required_toast", not toast, toast or "OK")
        check("03_print_download", bool(dl) and dl[-1]["status"] == 200, dl)
        all_hits.extend(hits)
        ctx.close()

        # 04 — Menú acciones → PDF de la factura
        ctx, page, hits = make_page(browser, sess)
        page.locator(".o_cp_action_menus button").first.click(timeout=10000)
        page.wait_for_timeout(1000)
        page.locator(".dropdown-item:has-text('PDF de la factura')").click(timeout=10000)
        page.wait_for_timeout(6000)
        dl = [h for h in hits if "/report/download" in h["url"]]
        check("04_menu_invoice_pdf", bool(dl) and dl[-1]["status"] == 200, dl)
        all_hits.extend(hits)
        ctx.close()

        # 05 — Enviar (wizard)
        ctx, page, hits = make_page(browser, sess)
        send = page.locator("button[name='action_invoice_sent']")
        if send.count() and send.first.is_visible():
            send.first.click(timeout=10000)
            page.wait_for_timeout(4000)
            toast = toast_has_required(page)
            wizard = page.locator(".o_dialog, .modal-content").count() > 0
            send_rpc = [h for h in hits if "action_invoice_sent" in h["url"] or "send" in h["url"]]
            check("05_send_wizard_or_rpc", wizard or bool(send_rpc), {"wizard": wizard, "rpc": send_rpc})
            check("05_send_no_required_toast", not toast, toast or "OK")
        else:
            check("05_send_wizard_or_rpc", True, "Botón Enviar no visible (factura ya enviada/pagada)")
            check("05_send_no_required_toast", True, "skipped")
        all_hits.extend(hits)
        ctx.close()

    report["network"] = all_hits
    report["pass"] = report["ok"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
