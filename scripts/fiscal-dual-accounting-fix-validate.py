#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación: un solo icono Contabilidad en launcher erp.justech.do."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence/fiscal-dual-accounting-fix"
SESSION_FILE = Path("/tmp/fiscal_stabilize_session.json")

report = {"ts": datetime.now(timezone.utc).isoformat(), "passed": False, "tests": {}, "js_errors": []}


def check(key, ok, detail=""):
    report["tests"][key] = {"ok": bool(ok), "detail": str(detail)[:800]}


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

            page.goto(f"{base}/odoo", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(8000)

            # load_menus: root apps = parent_id false / children of root
            menus = rpc(page, "ir.ui.menu", "load_menus", args=[False])
            root_apps = []
            for mid, meta in menus.items():
                if not isinstance(meta, dict):
                    continue
                if meta.get("xmlid") in ("account.menu_finance", "accountant.menu_accounting"):
                    root_apps.append(
                        {
                            "id": meta.get("id") or mid,
                            "name": meta.get("name"),
                            "xmlid": meta.get("xmlid"),
                            "children": len(meta.get("children") or []),
                        }
                    )
            # Contabilidad visible: only accountant with children, or finance if it has children
            visible = [a for a in root_apps if a["children"] > 0]
            check(f"single_accounting_icon_{scheme}", len(visible) == 1, visible)
            check(
                f"accounting_is_enterprise_{scheme}",
                len(visible) == 1 and visible[0].get("xmlid") == "accountant.menu_accounting",
                visible,
            )

            # Pagos / Audit under accountant
            acct_id = None
            for mid, meta in menus.items():
                if isinstance(meta, dict) and meta.get("xmlid") == "accountant.menu_accounting":
                    acct_id = int(meta.get("id") or mid)
                    break
            children = rpc(
                page,
                "ir.ui.menu",
                "search_read",
                args=[[["parent_id", "=", acct_id], ["active", "=", True]]],
                kwargs={"fields": ["name", "sequence"], "order": "sequence"},
            )
            names = [c["name"] for c in children]
            check(f"pagos_in_accounting_{scheme}", "Pagos" in names, names)
            check(f"audit_in_accounting_{scheme}", "Auditoría Fiscal" in names, names)

            page.screenshot(path=str(EVIDENCE / f"01_home_{scheme}.png"), full_page=True)

            # Open Contabilidad via action path
            page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            content = page.content()
            check(f"accounting_loads_{scheme}", "RPC_ERROR" not in content and page.locator(".o_main_navbar, nav.o_navbar, .o_action_manager").count() > 0)
            page.screenshot(path=str(EVIDENCE / f"02_accounting_{scheme}.png"), full_page=True)
            ctx.close()
        browser.close()

    check("no_js_errors", len(report["js_errors"]) == 0, report["js_errors"][:3])
    report["passed"] = all(t["ok"] for t in report["tests"].values())
    (EVIDENCE / "visual_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
