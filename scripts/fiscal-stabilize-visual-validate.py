#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación visual automatizada — erp.justech.do (Playwright)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence/fiscal-stabilize-visual"
SESSION_FILE = Path("/tmp/fiscal_stabilize_session.json")

EXPECTED_MENUS = (
    "606 — Compras",
    "607 — Ventas",
    "608 — Comprobantes Anulados",
    "609 — Pagos al Exterior",
    "623 — Retenciones del Estado",
    "Tipos de Comprobante",
    "Rangos NCF",
    "Consumo NCF",
    "NCF Anulados",
    "Historial Fiscal",
    "Revisión Fiscal",
    "Pendientes de Aprobación",
    "Administrar Retenciones",
    "Centro de Administración Fiscal",
)

ACTIONS = {
    "centro_fiscal": 1502,
    "wizard_cobro": 1508,
    "wizard_pago": 1509,
}

report = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "passed": False,
    "tests": {},
    "js_errors": [],
    "http_errors": [],
}


def check(key, ok, detail=""):
    report["tests"][key] = {"ok": bool(ok), "detail": str(detail)[:800]}
    if not ok:
        report["passed"] = False


def shot(page, name):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


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


def audit_menu_labels(page):
    menus = rpc(page, "ir.ui.menu", "load_menus", args=[False])
    root_id = None
    for mid, meta in menus.items():
        if isinstance(meta, dict) and meta.get("xmlid") == "justech_l10n_do_reports.menu_justech_do_audit_root":
            root_id = int(meta.get("id") or mid)
            break
    if not root_id:
        return [], None
    children = rpc(
        page,
        "ir.ui.menu",
        "search_read",
        args=[[["parent_id", "=", root_id], ["active", "=", True]]],
        kwargs={"fields": ["name", "sequence"], "order": "sequence"},
    )
    labels = [c.get("name", "") for c in children]
    return labels, root_id


def main():
    sess = json.loads(SESSION_FILE.read_text())
    base = sess["base_url"].rstrip("/")
    domain = urlparse(base).hostname or "erp.justech.do"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

        def ctx_page(color_scheme="light"):
            ctx = browser.new_context(
                locale="es-DO",
                viewport={"width": 1440, "height": 900},
                color_scheme=color_scheme,
            )
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

            def on_console(msg):
                if msg.type == "error":
                    report["js_errors"].append(msg.text[:300])

            def on_response(resp):
                url = resp.url
                if resp.status >= 400 and any(x in url for x in ("/web/dataset", "/web/action", "/odoo/action")):
                    report["http_errors"].append({"url": url[:200], "status": resp.status})

            page.on("console", on_console)
            page.on("response", on_response)
            return ctx, page

        ctx, page = ctx_page("light")
        page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(8000)
        content = page.content()
        navbar = page.locator(".o_main_navbar, nav.o_navbar").count()
        check("contabilidad_loads", navbar > 0 or "Contabilidad" in content or "Accounting" in content, page.url)
        shot(page, "01_contabilidad_light")

        labels, root_id = audit_menu_labels(page)
        check("auditoria_root_rpc", root_id is not None, f"root={root_id}")
        missing = [m for m in EXPECTED_MENUS if m not in labels]
        check("audit_14_options", len(labels) == 14 and not missing, f"labels={labels} missing={missing}")
        shot(page, "02_menus_rpc_light")

        page.goto(f"{base}/odoo/action-{ACTIONS['centro_fiscal']}", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(6000)
        content = page.content()
        check("centro_no_rpc", "RPC_ERROR" not in content and "404 Not Found" not in content and "KeyError" not in content, page.url)
        check(
            "centro_content",
            any(
                t in content
                for t in (
                    "Administración Fiscal",
                    "Centro Fiscal",
                    "Feature Flags",
                    "justech.fiscal.admin.center",
                    "Indicadores",
                )
            ),
        )
        shot(page, "03_centro_fiscal_light")
        ctx.close()

        for key, aid in (("wizard_cobro", ACTIONS["wizard_cobro"]), ("wizard_pago", ACTIONS["wizard_pago"])):
            ctx, page = ctx_page("light")
            page.goto(f"{base}/odoo/action-{aid}", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            content = page.content()
            check(f"{key}_no_rpc", "RPC_ERROR" not in content and "KeyError" not in content, page.url)
            has_form = page.locator("form.o_form_view, .o_dialog").count() > 0
            fields = (
                page.locator('[name="journal_id"]').count() > 0
                or page.locator('[name="payment_method_line_id"]').count() > 0
                or "Método" in content
            )
            check(f"{key}_fields", has_form and fields, f"form={has_form}")
            shot(page, f"04_{key}_light")
            ctx.close()

        ctx, page = ctx_page("light")
        page.goto(f"{base}/odoo/customer-invoices", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(4000)
        content = page.content()
        check("invoices_standard", "RPC_ERROR" not in content and ("Factura" in content or "Invoice" in content))
        shot(page, "05_facturas_light")
        ctx.close()

        ctx, page = ctx_page("dark")
        page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(4000)
        check("contabilidad_dark", page.locator(".o_main_navbar").count() > 0)
        shot(page, "06_contabilidad_dark")
        ctx.close()

        browser.close()

    check("no_js_errors", len(report["js_errors"]) == 0, report["js_errors"][:3])

    if all(t["ok"] for t in report["tests"].values()):
        report["passed"] = True

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "visual_validation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        report["fatal"] = str(exc)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise SystemExit(1)
