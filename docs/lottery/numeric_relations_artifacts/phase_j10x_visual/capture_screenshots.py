#!/usr/bin/env python3
"""J-10X visual capture — single Lottery IA Control Center experience (DEV)."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3012"
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
        data = json.loads(resp.read().decode())
    if not data.get("tenant_id") and isinstance(data.get("tenant"), dict):
        data["tenant_id"] = data["tenant"].get("id")
    return data


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


def goto(page, path: str, wait_ms: int = 2500) -> None:
    page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(wait_ms)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tokens = login_api()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        inject_auth(page, tokens)

        # 01 home identity
        goto(page, "/lottery", 4000)
        body = page.inner_text("body")
        assert "Lottery IA Control Center" in body, "home missing product identity"
        assert "Metodología" not in body, "nested Metodología nav still present"
        shot(page, "01_home_control_center.png")

        # 02 single sidebar labels
        shot(page, "02_single_sidebar.png")

        # 03 no second Inteligencia nav on motor route
        goto(page, "/lottery/admin/control-center/motor/historial-numero", 3000)
        body = page.inner_text("body")
        assert "Lottery IA · Inteligencia" not in body, "nested Inteligencia title still present"
        shot(page, "03_no_dual_nav.png")

        # 04 historial simple (one lottery wall by default)
        goto(
            page,
            "/lottery/admin/control-center/motor/historial-numero?number=50&featured=1",
            3500,
        )
        # open filters if collapsed
        btn = page.get_by_role("button", name="Cambiar búsqueda")
        if btn.count():
            btn.first.click()
            page.wait_for_timeout(500)
        body = page.inner_text("body")
        assert "Loterías del universo activo" in body
        assert "Opciones avanzadas de alcance" in body
        # advanced scopes collapsed — confirm labels not visible until expanded
        assert "Loterías donde buscar confirmaciones" not in body
        shot(page, "04_historial_simple.png")

        # 05 expand advanced once
        page.get_by_role("button", name="Opciones avanzadas de alcance").first.click()
        page.wait_for_timeout(400)
        shot(page, "05_historial_advanced_collapsed_proof.png")

        # 06 comparador
        goto(page, "/lottery/admin/control-center/motor/comparador", 3500)
        body = page.inner_text("body")
        assert "Candidatos (Tabla 1)" in body
        assert "SAME_DRAW" not in body
        shot(page, "06_comparador_simple.png")

        # 07 agrupaciones
        goto(page, "/lottery/admin/control-center/motor/agrupaciones", 4000)
        shot(page, "07_agrupaciones_tabs.png")

        # 08 relaciones
        goto(page, "/lottery/admin/control-center/motor/relaciones", 3500)
        shot(page, "08_relaciones.png")

        # 09 auditoria
        goto(page, "/lottery/admin/control-center/motor/auditoria", 3500)
        shot(page, "09_auditoria.png")

        # 10 catalog seven
        goto(page, "/lottery/lotteries", 4000)
        body = page.inner_text("body")
        assert "Loto Leidsa" not in body
        shot(page, "10_catalogo_siete.png")

        # 11 legacy redirect search → historial
        goto(page, "/lottery/search", 3500)
        assert "historial-numero" in page.url
        shot(page, "11_redirect_search.png")

        # 12 mobile single nav
        context2 = browser.new_context(viewport={"width": 390, "height": 844})
        page2 = context2.new_page()
        inject_auth(page2, tokens)
        goto(page2, "/lottery", 3500)
        body = page2.inner_text("body")
        assert "Metodología" not in body
        shot(page2, "12_mobile_single_nav.png")
        context2.close()

        browser.close()
    print("J-10X capture OK")


if __name__ == "__main__":
    main()
