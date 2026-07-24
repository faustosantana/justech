#!/usr/bin/env python3
"""Capture J-10S stabilization screenshots against FE DEV :3011 (real data)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3011"
API = "http://127.0.0.1:8001/api/v1"
OUT = Path(__file__).resolve().parent / "screenshots"


def login_api() -> dict:
    body = json.dumps(
        {
            "email": "uat-nr-admin@example.com",
            "password": "UatDevNumericRelations2026!",
            "tenant_slug": "uat-numeric-relations",
        }
    ).encode()
    req = urllib.request.Request(
        f"{API}/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def inject_auth(page, tokens: dict) -> None:
    page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=60000)
    page.evaluate(
        """(t) => {
          localStorage.setItem('jaios_access_token', t.access_token);
          localStorage.setItem('jaios_refresh_token', t.refresh_token || '');
          if (t.tenant_id) localStorage.setItem('jaios_tenant_id', t.tenant_id);
          if (t.role) localStorage.setItem('jaios_role', t.role);
        }""",
        tokens,
    )


def shot(page, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    page.screenshot(path=str(path), full_page=False)
    print(f"wrote {path.name} ({path.stat().st_size})")


def wait_text(page, text: str, timeout=120000) -> None:
    page.get_by_text(text, exact=False).first.wait_for(timeout=timeout)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tokens = login_api()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        inject_auth(page, tokens)

        # Historial 50 — signals + charts + why
        page.goto(
            f"{BASE}/lottery/admin/control-center/motor/historial-numero?number=50&auto=1&featured=1",
            wait_until="domcontentloaded",
            timeout=120000,
        )
        wait_text(page, "EXPEDIENTE DEL NÚMERO")
        page.wait_for_timeout(5000)

        page.get_by_text("Señales y predicciones").first.scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        shot(page, "01_signal_card.png")

        page.get_by_text("Apariciones por año").first.scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        shot(page, "03_five_charts.png")

        page.get_by_role("button", name="Condición positiva").click()
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="Ver caso").first.click()
        page.wait_for_timeout(4000)
        why_btn = page.get_by_role("button", name="¿Por qué se fortaleció?")
        if why_btn.count():
            why_btn.first.click()
            page.wait_for_timeout(1200)
            page.get_by_text("¿Por qué se fortaleció el número").first.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        shot(page, "04_why_block.png")

        # Empty / sparse signals
        page.goto(
            f"{BASE}/lottery/admin/control-center/motor/historial-numero?number=99&auto=1&featured=1",
            wait_until="domcontentloaded",
            timeout=120000,
        )
        wait_text(page, "EXPEDIENTE DEL NÚMERO")
        page.wait_for_timeout(6000)
        page.get_by_text("Señales").first.scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        shot(page, "02_signals_empty_state.png")

        # Table 1
        page.goto(f"{BASE}/lottery/admin/control-center/motor/table1", wait_until="domcontentloaded")
        wait_text(page, "Tabla 1")
        page.wait_for_timeout(2500)
        shot(page, "05_table_1_simplified.png")
        if page.get_by_text("Ver cálculo").count():
            page.get_by_text("Ver cálculo").first.click()
            page.wait_for_timeout(900)
        shot(page, "06_table_1_calculation_collapsed.png")

        # Table 2
        page.goto(f"{BASE}/lottery/admin/control-center/motor/table2", wait_until="domcontentloaded")
        wait_text(page, "Tabla 2")
        page.wait_for_timeout(2500)
        shot(page, "07_table_2_simplified.png")
        if page.get_by_text("Ver cálculo").count():
            page.get_by_text("Ver cálculo").first.click()
            page.wait_for_timeout(900)
        shot(page, "08_table_2_calculation_collapsed.png")

        # Audit
        page.goto(f"{BASE}/lottery/admin/control-center/motor/auditoria", wait_until="domcontentloaded")
        wait_text(page, "Auditoría")
        page.wait_for_timeout(2000)
        # Prefer labeled number field
        filled = False
        for label in ("Número", "Numero", "número"):
            loc = page.get_by_label(label, exact=False)
            if loc.count():
                loc.first.fill("50")
                filled = True
                break
        if not filled:
            page.locator("input").first.fill("50")
        shot(page, "09_audit_filters.png")
        for name in ("Buscar", "Auditar", "Ejecutar", "Consultar"):
            btn = page.get_by_role("button", name=name)
            if btn.count():
                btn.first.click()
                break
        page.wait_for_timeout(10000)
        shot(page, "10_audit_result.png")

        # Desktop hub
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(f"{BASE}/lottery/admin/control-center", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        shot(page, "13_desktop_final.png")

        # Mobile 375
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(
            f"{BASE}/lottery/admin/control-center/motor/historial-numero?number=50&auto=1&featured=1",
            wait_until="domcontentloaded",
        )
        wait_text(page, "EXPEDIENTE")
        page.wait_for_timeout(4000)
        for label in ("Metodología", "Menú", "Navegación"):
            b = page.get_by_role("button", name=label)
            if b.count():
                try:
                    b.first.click()
                    page.wait_for_timeout(700)
                except Exception:
                    pass
                break
        shot(page, "11_mobile_single_navigation_375.png")

        # Mobile 768
        page.set_viewport_size({"width": 768, "height": 900})
        page.goto(f"{BASE}/lottery/admin/control-center", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for label in ("Metodología", "Menú"):
            b = page.get_by_role("button", name=label)
            if b.count():
                try:
                    b.first.click()
                    page.wait_for_timeout(700)
                except Exception:
                    pass
                break
        shot(page, "12_mobile_single_navigation_768.png")

        browser.close()
        missing = [
            n
            for n in [
                "01_signal_card.png",
                "02_signals_empty_state.png",
                "03_five_charts.png",
                "04_why_block.png",
                "05_table_1_simplified.png",
                "06_table_1_calculation_collapsed.png",
                "07_table_2_simplified.png",
                "08_table_2_calculation_collapsed.png",
                "09_audit_filters.png",
                "10_audit_result.png",
                "11_mobile_single_navigation_375.png",
                "12_mobile_single_navigation_768.png",
                "13_desktop_final.png",
            ]
            if not (OUT / n).exists()
        ]
        print("done missing=", missing)
        print("files=", sorted(x.name for x in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
