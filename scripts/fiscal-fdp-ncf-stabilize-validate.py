#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación visual: NCF vía FDP en wizard + menú Contabilidad ordenado."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence/fiscal-fdp-ncf-stabilize"
SESSION_FILE = Path("/tmp/fiscal_stabilize_session.json")
EXPECTED_TOP = (
    "Tablero",
    "Clientes",
    "Proveedores",
    "Contabilidad",
    "Pagos",
    "Revisión",
    "Reportes",
    "Auditoría Fiscal",
    "Configuración",
)

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

            page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(6000)

            menus = rpc(page, "ir.ui.menu", "load_menus", args=[False])
            acct_id = None
            for mid, meta in menus.items():
                if isinstance(meta, dict) and meta.get("xmlid") == "accountant.menu_accounting":
                    acct_id = int(meta.get("id") or mid)
                    break
            top = rpc(
                page,
                "ir.ui.menu",
                "search_read",
                args=[[["parent_id", "=", acct_id], ["active", "=", True]]],
                kwargs={"fields": ["name", "sequence"], "order": "sequence"},
            )
            names = [t["name"] for t in top]
            # Accept EN or ES labels for standard Odoo menus
            check(f"config_last_{scheme}", names and names[-1] in ("Configuración", "Configuration"), names)
            check(f"pagos_in_top_{scheme}", "Pagos" in names, names)
            check(f"audit_in_top_{scheme}", "Auditoría Fiscal" in names, names)
            check(
                f"single_acct_{scheme}",
                not any(
                    isinstance(m, dict) and m.get("xmlid") == "account.menu_finance" and (m.get("children") or [])
                    for m in menus.values()
                ),
            )

            # Wizard UI loads without RPC error; NCF via FDP already validated in shell.
            page.goto(f"{base}/odoo/action-1508", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            content = page.content()
            check(f"wizard_cobro_ui_{scheme}", "RPC_ERROR" not in content and "KeyError" not in content, page.url)
            page.screenshot(path=str(EVIDENCE / f"01_wizard_cobro_{scheme}.png"), full_page=True)

            page.goto(f"{base}/odoo/action-1509", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            content = page.content()
            check(f"wizard_pago_ui_{scheme}", "RPC_ERROR" not in content and "KeyError" not in content, page.url)
            page.screenshot(path=str(EVIDENCE / f"02_wizard_pago_{scheme}.png"), full_page=True)

            # FDP NCF sample via call_kw on account.move
            hist = rpc(
                page,
                "account.move",
                "search_read",
                args=[
                    [
                        ["state", "=", "posted"],
                        ["l10n_latam_document_number", "!=", False],
                        ["justech_do_ncf", "=", False],
                        ["move_type", "in", ["out_invoice", "in_invoice"]],
                    ]
                ],
                kwargs={"fields": ["name", "justech_fiscal_ncf", "l10n_latam_document_number"], "limit": 3},
            )
            check(
                f"hist_ncf_fdp_{scheme}",
                bool(hist) and all(h.get("justech_fiscal_ncf") for h in hist),
                hist,
            )

            page.goto(f"{base}/odoo/accounting", wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(3000)
            check(f"accounting_ok_{scheme}", page.locator(".o_main_navbar, nav.o_navbar, .o_action_manager").count() > 0)
            page.screenshot(path=str(EVIDENCE / f"03_accounting_{scheme}.png"), full_page=True)
            ctx.close()
        browser.close()

    check("no_js_errors", len(report["js_errors"]) == 0, report["js_errors"][:3])
    report["passed"] = all(t["ok"] for t in report["tests"].values())
    (EVIDENCE / "visual_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
