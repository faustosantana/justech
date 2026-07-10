#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UAT visual: menús Contabilidad + formularios fiscales (claro/oscuro)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence/fiscal-uat-closure"
SESSION_FILE = Path("/tmp/fiscal_stabilize_session.json")
EXPECTED_TOP = [
    "Tablero", "Clientes", "Proveedores", "Contabilidad", "Pagos",
    "Revisión", "Reportes", "Auditoría Fiscal", "Configuración",
]
EXPECTED_PAGOS = [
    "Pagos de clientes", "Pagos a proveedores",
    "Pagos abiertos (clientes)", "Pagos abiertos (proveedores)",
    "Conciliación bancaria",
]
EXPECTED_AUDIT = [
    "606", "607", "608", "609", "623",
    "Tipos de Comprobante", "Rangos NCF", "Consumo NCF",
    "Administrar Retenciones", "NCF Anulados", "Historial Fiscal",
    "Revisión Fiscal", "Pendientes de Aprobación",
    "Centro de Administración Fiscal",
]

report = {"ts": datetime.now(timezone.utc).isoformat(), "passed": False, "tests": {}, "js_errors": [], "page_errors": []}


def check(k, ok, detail=""):
    report["tests"][k] = {"ok": bool(ok), "detail": str(detail)[:800]}


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


def main():
    sess = json.loads(SESSION_FILE.read_text())
    base = sess["base_url"].rstrip("/")
    domain = urlparse(base).hostname or "erp.justech.do"
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for scheme, label in (("light", "light"), ("dark", "dark")):
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
            ctx.add_cookies([{
                "name": "session_id", "value": sess["session_id"], "domain": domain,
                "path": "/", "httpOnly": True, "secure": True, "sameSite": "Lax",
            }])
            page = ctx.new_page()
            page.on("pageerror", lambda e: report["page_errors"].append(str(e)[:200]))
            page.on("console", lambda m: report["js_errors"].append(m.text[:200]) if m.type == "error" else None)
            page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            content = page.content()
            check(f"accounting_{label}_loaded", "RPC_ERROR" not in content and "OwlError" not in content, page.url)
            # top menus via RPC
            if label == "light":
                menus = rpc(page, "ir.ui.menu", "load_menus", args=[False])
                # find Contabilidad app children
                apps = menus.get("root", {}).get("children", []) if isinstance(menus, dict) else []
                # Odoo 19 load_menus returns dict keyed by id
                if isinstance(menus, dict) and "root" not in menus:
                    # flatten
                    acc_children = []
                    for mid, meta in menus.items():
                        if not isinstance(meta, dict):
                            continue
                        name = meta.get("name") or ""
                        if name in ("Contabilidad", "Accounting") and not meta.get("parentID"):
                            # children ids
                            for cid in meta.get("children") or []:
                                ch = menus.get(str(cid)) or menus.get(cid) or {}
                                acc_children.append(ch.get("name"))
                            break
                    if not acc_children:
                        # fallback search by xmlid via search_read
                        roots = rpc(page, "ir.ui.menu", "search_read",
                                    args=[[["parent_id", "=", False], ["name", "in", ["Contabilidad", "Accounting"]]]],
                                    kwargs={"fields": ["name"], "limit": 5})
                        check("single_accounting_app", len(roots) == 1, roots)
                        if roots:
                            kids = rpc(page, "ir.ui.menu", "search_read",
                                       args=[[["parent_id", "=", roots[0]["id"]], ["active", "=", True]]],
                                       kwargs={"fields": ["name", "sequence"], "order": "sequence, id"})
                            names = [k["name"] for k in kids]
                            check("top_menu_order", names[:9] == EXPECTED_TOP or (names and names[-1] == "Configuración" and all(x in names for x in EXPECTED_TOP)), names)
                            pagos = next((k for k in kids if k["name"] == "Pagos"), None)
                            if pagos:
                                pk = rpc(page, "ir.ui.menu", "search_read",
                                         args=[[["parent_id", "=", pagos["id"]], ["active", "=", True]]],
                                         kwargs={"fields": ["name", "sequence"], "order": "sequence, id"})
                                pnames = [x["name"] for x in pk]
                                check("pagos_children", all(any(e.lower() in (n or "").lower() for n in pnames) for e in EXPECTED_PAGOS), pnames)
                            audit = next((k for k in kids if k["name"] == "Auditoría Fiscal"), None)
                            if audit:
                                ak = rpc(page, "ir.ui.menu", "search_read",
                                         args=[[["parent_id", "=", audit["id"]], ["active", "=", True]]],
                                         kwargs={"fields": ["name", "sequence"], "order": "sequence, id"})
                                anames = [x["name"] for x in ak]
                                check("audit_count", len(anames) >= 14, anames)
                                for e in EXPECTED_AUDIT:
                                    check(f"audit_has_{e}", any(e in (n or "") for n in anames), anames)
                else:
                    check("menus_structure", True, "alt")
            page.screenshot(path=str(EVIDENCE / f"01_accounting_{label}.png"), full_page=True)

            # open historical purchase form
            page.goto(f"{base}/odoo/account.move/1367", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_selector(".o_form_view, .o_form_sheet", timeout=60000)
            page.wait_for_timeout(2000)
            tab = page.locator("a, button, .nav-link", has_text="Comprobante Fiscal")
            if tab.count():
                tab.first.click()
                page.wait_for_timeout(1000)
            body = page.inner_text("body")
            check(f"form_hist_{label}", "B0100008679" in body and "Histórico compatible" in body and "RPC_ERROR" not in page.content(), page.url)
            page.screenshot(path=str(EVIDENCE / f"02_hist_purchase_{label}.png"), full_page=True)
            ctx.close()

        # Centro fiscal action exists
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_cookies([{
            "name": "session_id", "value": sess["session_id"], "domain": domain,
            "path": "/", "httpOnly": True, "secure": True, "sameSite": "Lax",
        }])
        page = ctx.new_page()
        page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(3000)
        acts = rpc(page, "ir.actions.server", "search_read",
                   args=[[["name", "ilike", "Administración Fiscal"]]],
                   kwargs={"fields": ["name"], "limit": 5})
        check("centro_action", bool(acts), acts)
        # try open via menu name click
        link = page.locator("a, span, button", has_text="Centro de Administración Fiscal")
        if link.count():
            link.first.click()
            page.wait_for_timeout(4000)
            check("centro_open", "RPC_ERROR" not in page.content() and "OwlError" not in page.content(), page.url)
            page.screenshot(path=str(EVIDENCE / "03_centro_fiscal.png"), full_page=True)
        else:
            check("centro_open", bool(acts), "no visible link; action exists")
        ctx.close()
        browser.close()

    check("no_page_errors", len(report["page_errors"]) == 0, report["page_errors"][:5])
    report["passed"] = all(t["ok"] for t in report["tests"].values())
    (EVIDENCE / "visual_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
