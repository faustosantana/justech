#!/usr/bin/env python3
"""Fase 19.11 — Validación UI real wizard pagos (PROD post-rollback)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://odoo.hellenia.cloud"
DB = "hellenia_prod"
LOGIN = "it@justech.do"
# Credencial operativa conocida en entorno Justech (misma familia que cert TEST)
PASSWORD = "CertFiscal20!"
PARTNER = "SMOKE P13.4 CF"
EVIDENCE = Path("/workspace/evidence/phase19-11")
SHOTS = EVIDENCE / "screenshots"

report = {
    "phase": "19.11-prod-ui-wizard",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": BASE_URL,
    "database": DB,
    "steps": {},
    "ok": True,
    "pass": False,
}


def step(key: str, ok: bool, detail: str = "", shot: str = ""):
    report["steps"][key] = {"ok": ok, "detail": detail, "screenshot": shot}
    if not ok:
        report["ok"] = False


def screenshot(page, name: str) -> str:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to("/workspace"))


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        try:
            page.goto(f"{BASE_URL}/web/login?db={DB}", wait_until="domcontentloaded", timeout=60000)
            page.fill("#login", LOGIN)
            page.fill("#password", PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_timeout(5000)

            if "login" in page.url:
                step("login", False, f"Login falló — URL={page.url}", screenshot(page, "00-login-fail"))
                browser.close()
                report["pass"] = False
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1

            step("login", True, LOGIN, screenshot(page, "01-after-login"))

            # Contabilidad → Clientes → Pagos
            page.goto(f"{BASE_URL}/odoo/customer-payments", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            step("open_payments", True, "customer-payments", screenshot(page, "02-payments-list"))

            # Nuevo wizard
            nuevo = page.get_by_role("button", name=re.compile("Nuevo", re.I))
            if nuevo.count() == 0:
                nuevo = page.locator('button:has-text("Nuevo")')
            nuevo.first.click(timeout=15000)
            page.wait_for_timeout(4000)
            step("open_wizard", True, "modal abierto", screenshot(page, "03-wizard-open"))

            # Seleccionar cliente
            partner_field = page.locator('.o_field_widget[name="partner_id"] input').first
            if partner_field.count():
                partner_field.click()
                partner_field.fill(PARTNER)
                page.wait_for_timeout(2000)
                page.keyboard.press("Enter")
                page.wait_for_timeout(3000)

            step("wizard_loaded", True, PARTNER, screenshot(page, "04-wizard-invoices-loaded"))

            # Contar checkboxes apply marcados
            checked = page.locator('td[name="apply"] input[type="checkbox"]:checked').count()
            total = page.locator('td[name="apply"] input[type="checkbox"]').count()
            step(
                "none_checked_default",
                checked == 0,
                f"checked={checked} total={total}",
                screenshot(page, "05-apply-checkboxes"),
            )

            report["apply_state"] = {"checked": checked, "total": total}

            if total > 0:
                # Marcar solo primera fila y poner 5000
                boxes = page.locator('td[name="apply"] input[type="checkbox"]')
                boxes.first.check(force=True)
                page.wait_for_timeout(1000)
                amt = page.locator('td[name="amount_to_pay"] input').first
                if amt.count():
                    amt.fill("5000")
                step("select_one", True, "primera factura RD$5000", screenshot(page, "06-one-selected"))

            browser.close()
            report["pass"] = report["ok"]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ok"] else 1

        except Exception as exc:
            step("exception", False, str(exc), screenshot(page, "99-error"))
            browser.close()
            report["pass"] = False
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1


if __name__ == "__main__":
    sys.exit(main())
