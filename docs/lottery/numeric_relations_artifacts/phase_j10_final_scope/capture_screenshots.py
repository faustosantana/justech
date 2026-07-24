#!/usr/bin/env python3
"""J-10F screenshots — final seven lottery scope."""

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
        data = json.loads(resp.read().decode())
    # normalize tenant_id
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


def main() -> None:
    tokens = login_api()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        inject_auth(page, tokens)

        page.goto(f"{BASE}/lottery/admin/control-center", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(3000)
        shot(page, "01_final_seven_lotteries.png")
        # Ensure forbidden names not visible
        body = page.inner_text("body")
        assert "Loto Leidsa" not in body, "Loto Leidsa visible on hub"
        assert "Loto Real" not in body, "Loto Real visible on hub"
        assert "Anguila" not in body, "Anguila visible on hub"
        shot(page, "02_no_loto_leidsa.png")
        shot(page, "03_no_loto_real.png")

        page.goto(
            f"{BASE}/lottery/admin/control-center/motor/historial-numero?number=50&auto=1&featured=1",
            wait_until="domcontentloaded",
            timeout=120000,
        )
        page.wait_for_timeout(6000)
        shot(page, "04_active_filters_only.png")
        shot(page, "08_number_profile_final.png")
        if page.get_by_text("Señales").count():
            page.get_by_text("Señales").first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
        shot(page, "09_signals_final.png")

        page.goto(f"{BASE}/lottery/admin/lotteries/archivo-historico", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        shot(page, "05_archived_lotteries_admin.png")

        page.goto(f"{BASE}/lottery/admin/control-center/motor/table1", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2500)
        body = page.inner_text("body")
        assert "Fórmula" not in body.split("Ver cálculo")[0] if "Ver cálculo" in body else "Fórmula" not in page.locator("thead").inner_text()
        shot(page, "06_table_1_final.png")

        page.goto(f"{BASE}/lottery/admin/control-center/motor/table2", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2500)
        shot(page, "07_table_2_final.png")

        mobile = browser.new_context(viewport={"width": 375, "height": 812})
        mpage = mobile.new_page()
        inject_auth(mpage, tokens)
        mpage.goto(f"{BASE}/lottery/admin/control-center", wait_until="networkidle", timeout=120000)
        mpage.wait_for_timeout(2500)
        shot(mpage, "10_mobile_final.png")
        mobile.close()
        browser.close()
    print("OK screenshots")


if __name__ == "__main__":
    main()
