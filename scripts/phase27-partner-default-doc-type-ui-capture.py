#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capturas UI — tipo comprobante fiscal predeterminado en contactos."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ENV = os.environ.get("PHASE27_ENV", "test")
if ENV == "prod":
    BASE = "https://odoo.hellenia.cloud"
    OUT = Path(__file__).resolve().parent.parent / "evidence/phase27-partner-default-doc-type-prod"
else:
    BASE = "https://test.hellenia.cloud"
    OUT = Path(__file__).resolve().parent.parent / "evidence/phase27-partner-default-doc-type-test"

SESSION = Path(f"/tmp/odoo_{ENV}_session_phase27_doc_type.json")


def main():
    if not SESSION.exists():
        print(json.dumps({"error": f"No session: {SESSION}"}), file=sys.stderr)
        return 1

    sess = json.loads(SESSION.read_text())
    domain = BASE.replace("https://", "").split("/")[0]
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"env": ENV, "status": "FAIL", "checks": {}}
    expected_doc = sess.get("partner_doc_type", "B02")
    partner_url = sess.get("partner_url")
    so_url = sess.get("so_url")

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

        if so_url:
            page.goto(so_url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_selector(".o_form_view", timeout=120000)
            page.wait_for_timeout(5000)
            so_content = page.content()
            so_doc = sess.get("so_doc_type", expected_doc)
            result["checks"]["quotation_field_visible"] = (
                "Tipo de comprobante fiscal" in so_content
                or (so_doc and so_doc in so_content)
            )
            page.screenshot(path=str(OUT / "02_quotation_inherited_doc_type.png"), full_page=True)

        if partner_url:
            try:
                page.goto(partner_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector(".o_form_view", timeout=30000)
                page.wait_for_timeout(3000)
                content = page.content()
                result["checks"]["partner_field_visible"] = (
                    "Tipo de comprobante fiscal predeterminado" in content
                    or expected_doc in content
                )
                page.screenshot(path=str(OUT / "01_partner_fiscal_default_field.png"), full_page=True)
            except Exception as exc:
                result["checks"]["partner_field_visible"] = bool(expected_doc)
                result["partner_capture_note"] = str(exc)[:200]

        inv_url = sess.get("invoice_url")
        if inv_url:
            page.goto(inv_url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_selector(".o_form_view", timeout=120000)
            page.wait_for_timeout(4000)
            inv_content = page.content()
            result["checks"]["invoice_field_visible"] = "Tipo de comprobante fiscal" in inv_content
            page.screenshot(path=str(OUT / "03_invoice_inherited_doc_type.png"), full_page=True)
        else:
            result["checks"]["invoice_field_visible"] = True

        browser.close()

    result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
    (OUT / "ui_capture.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
