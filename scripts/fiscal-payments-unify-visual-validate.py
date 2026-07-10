#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación visual Pagos + Auditoría Fiscal — erp.justech.do."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence/fiscal-payments-unify-visual"
SESSION_FILE = Path("/tmp/fiscal_stabilize_session.json")

EXPECTED_PAGOS = (
    "Pagos de clientes",
    "Pagos a proveedores",
    "Pagos abiertos (clientes)",
    "Pagos abiertos (proveedores",
    "Conciliación bancaria",
)
EXPECTED_AUDIT = (
    "606 — Compras",
    "607 — Ventas",
    "608 — Comprobantes Anulados",
    "609 — Pagos al Exterior",
    "623 — Retenciones del Estado",
    "Tipos de Comprobante",
    "Rangos NCF",
    "Consumo NCF",
    "Administrar Retenciones",
    "Consumo NCF (Auditoría)",
    "NCF Anulados",
    "Historial Fiscal",
    "Revisión Fiscal",
    "Pendientes de Aprobación",
    "Centro de Administración Fiscal",
)

report = {"ts": datetime.now(timezone.utc).isoformat(), "passed": False, "tests": {}, "js_errors": []}


def check(key, ok, detail=""):
    report["tests"][key] = {"ok": bool(ok), "detail": str(detail)[:800]}
    if not ok:
        report["passed"] = False


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


def menu_children(page, root_xmlid):
    menus = rpc(page, "ir.ui.menu", "load_menus", args=[False])
    root_id = None
    for mid, meta in menus.items():
        if isinstance(meta, dict) and meta.get("xmlid") == root_xmlid:
            root_id = int(meta.get("id") or mid)
            break
    if not root_id:
        return []
    rows = rpc(
        page,
        "ir.ui.menu",
        "search_read",
        args=[[["parent_id", "=", root_id], ["active", "=", True]]],
        kwargs={"fields": ["name", "sequence"], "order": "sequence"},
    )
    return [r["name"] for r in rows]


def main():
    sess = json.loads(SESSION_FILE.read_text())
    base = sess["base_url"].rstrip("/")
    domain = urlparse(base).hostname or "erp.justech.do"
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for scheme in ("light", "dark"):
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
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
            page.on("console", lambda m: report["js_errors"].append(m.text[:200]) if m.type == "error" else None)

            page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(8000 if scheme == "light" else 5000)
            check(
                f"contabilidad_{scheme}",
                page.locator(".o_main_navbar, nav.o_navbar, .o_action_manager").count() > 0,
            )
            page.screenshot(path=str(EVIDENCE / f"01_contabilidad_{scheme}.png"), full_page=True)

            pagos = menu_children(page, "justech_l10n_do_treasury.menu_finance_payments_root")
            check(f"pagos_5_{scheme}", len(pagos) == 5, pagos)
            check(f"legacy_hidden_{scheme}", not any("ltipl" in n for n in pagos), pagos)

            audit = menu_children(page, "justech_l10n_do_reports.menu_justech_do_audit_root")
            check(f"audit_15_{scheme}", len(audit) == 15 and audit == list(EXPECTED_AUDIT), audit)
            page.screenshot(path=str(EVIDENCE / f"02_menus_{scheme}.png"), full_page=True)

            for key, path in (("wizard_cobro", "/odoo/action-1508"), ("wizard_pago", "/odoo/action-1509")):
                page.goto(f"{base}{path}", wait_until="domcontentloaded", timeout=120000)
                page.wait_for_timeout(7000)
                content = page.content()
                check(
                    f"{key}_{scheme}",
                    "RPC_ERROR" not in content
                    and "KeyError" not in content
                    and (
                        page.locator('[name="journal_id"]').count() > 0
                        or page.locator('[name="treasury_operation_type"]').count() > 0
                        or page.locator("form.o_form_view, .o_dialog").count() > 0
                    ),
                    page.url,
                )
                page.screenshot(path=str(EVIDENCE / f"03_{key}_{scheme}.png"), full_page=True)

            page.goto(f"{base}/odoo/action-1502", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            content = page.content()
            check(f"centro_fiscal_{scheme}", "RPC_ERROR" not in content and "404" not in content, page.url)
            page.screenshot(path=str(EVIDENCE / f"04_centro_{scheme}.png"), full_page=True)
            ctx.close()
        browser.close()

    check("no_js_errors", len(report["js_errors"]) == 0, report["js_errors"][:3])
    if all(t["ok"] for t in report["tests"].values()):
        report["passed"] = True
    (EVIDENCE / "visual_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
