#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capturas UI — vista previa nativa OC (portal iframe + sidebar)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ENV = os.environ.get("PHASE27B_ENV", "test")
if ENV == "prod":
    BASE = "https://odoo.hellenia.cloud"
    SESSION = Path("/tmp/odoo_prod_session_po_native_preview.json")
    OUT = Path(__file__).resolve().parent.parent / "evidence/phase27b-po-native-preview-prod"
else:
    BASE = os.environ.get("PHASE27B_BASE", "https://test.odoo.hellenia.cloud")
    SESSION = Path("/tmp/odoo_test_session_po_native_preview.json")
    OUT = Path(__file__).resolve().parent.parent / "evidence/phase27b-po-native-preview-test"


def main():
    if not SESSION.exists():
        print(json.dumps({"error": f"No session file: {SESSION}"}), file=sys.stderr)
        return 1

    sess = json.loads(SESSION.read_text())
    po_url = sess.get("po_url")
    if not po_url:
        print(json.dumps({"error": "po_url missing in session"}), file=sys.stderr)
        return 1

    domain = BASE.replace("https://", "").replace("http://", "").split("/")[0]
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"env": ENV, "po_url": po_url, "checks": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="es-DO")
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
        page.goto(po_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_selector(".o_form_view", timeout=120000)
        page.wait_for_timeout(2500)

        btn = page.locator("button[name='action_preview_purchase_order']")
        result["checks"]["button_visible"] = btn.count() > 0 and btn.first.is_visible()
        page.screenshot(path=str(OUT / "01_form_with_preview_button.png"), full_page=False)

        if not result["checks"]["button_visible"]:
            browser.close()
            (OUT / "ui_capture.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result))
            return 1

        btn.first.click(timeout=15000)
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        content = page.content()
        url = page.url
        result["preview_url"] = url
        result["checks"]["portal_preview_url"] = "/my/purchase/" in url and "/preview" in url
        result["checks"]["not_bare_html"] = "/report/html/" not in url
        result["checks"]["has_iframe"] = "purchase_order_html" in content
        result["checks"]["has_download"] = "o_download_btn" in content
        result["checks"]["has_print"] = "o_portal_po_print" in content
        result["checks"]["has_back_edit"] = (
            "Back to edit mode" in content or "action-purchase.purchase_rfq" in content
        )

        page.screenshot(path=str(OUT / "02_portal_preview_page.png"), full_page=True)

        frame = page.frame_locator("#purchase_order_html")
        if frame.locator("body").count():
            try:
                frame.locator("body").wait_for(timeout=15000)
                frame_html = frame.locator("body").inner_html(timeout=15000)
                result["checks"]["hellenia_design"] = "jt-po-band" in frame_html or "ORDEN DE COMPRA" in frame_html
            except Exception as exc:
                result["checks"]["hellenia_design"] = False
                result["iframe_error"] = str(exc)
        else:
            result["checks"]["hellenia_design"] = False

        browser.close()

    result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
    (OUT / "ui_capture.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
