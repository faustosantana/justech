#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capturas UI PROD — botón Vista previa + preview OC."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://odoo.hellenia.cloud"
OUT = Path(__file__).resolve().parent.parent / "evidence/phase27b-purchase-order-preview-prod"
SESSION = Path("/tmp/odoo_prod_session_po_preview.json")


def main():
    if not SESSION.exists():
        print("No session file", file=sys.stderr)
        return 1
    sess = json.loads(SESSION.read_text())
    po_url = sess.get("po_url", BASE + "/odoo/purchase/9")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="es-DO")
        ctx.add_cookies(
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
        page = ctx.new_page()
        page.goto(po_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_selector(".o_form_view", timeout=120000)
        page.wait_for_timeout(3000)
        OUT.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUT / "ui_form_with_button.png"), full_page=False)
        btn = page.locator("button[name='action_preview_purchase_order']")
        if btn.count() and btn.first.is_visible():
            with ctx.expect_page() as new_page_info:
                btn.first.click(timeout=10000)
            preview = new_page_info.value
            preview.wait_for_load_state("domcontentloaded", timeout=60000)
            preview.wait_for_timeout(4000)
            preview.screenshot(path=str(OUT / "ui_preview_hellenia.png"), full_page=True)
            ok = "ORDEN DE COMPRA" in preview.content() or "jt-po-band" in preview.content()
            print(json.dumps({"preview_opened": True, "hellenia_design": ok, "url": preview.url}))
        else:
            print(json.dumps({"preview_opened": False, "error": "button not visible"}))
            return 1
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
