#!/usr/bin/env python3
"""Ejecutor de pruebas funcionales l10n_do — Fase 2 Hellenia.

Uso remoto (XML-RPC):
  python3 scripts/run-l10n-do-functional-tests.py --url https://dev.hellenia.cloud \\
    --db hellenia_dev --user admin --password admin --tc 001

Requiere backup previo (TC-000) ejecutado en VPS:
  /opt/odoo-projects/hellenia/scripts/backup-dev.sh
"""
from __future__ import annotations

import argparse
import json
import sys
import xmlrpc.client
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE_ROOT = Path(__file__).resolve().parents[1] / "evidence" / "l10n-do-tests"


class OdooRPC:
    def __init__(self, url: str, db: str, user: str, password: str) -> None:
        self.url = url.rstrip("/")
        self.db = db
        self.password = password
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self.version = common.version()
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            raise SystemExit(f"Auth failed for {user}@{db}")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)

    def call(self, model: str, method: str, *args, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, list(args), kwargs)


def snapshot_baseline(odoo: OdooRPC) -> dict:
    mods = ["web_enterprise", "account", "account_accountant", "account_reports",
            "l10n_do", "l10n_do_reports", "l10n_do_edi"]
    module_states = {}
    for name in mods:
        rows = odoo.call("ir.module.module", "search_read", [("name", "=", name)],
                         fields=["name", "state", "shortdesc"])
        module_states[name] = rows[0] if rows else {"name": name, "state": "absent"}
    companies = odoo.call("res.company", "search_read", [("id", "!=", 0)],
                          fields=["name", "country_id", "currency_id", "vat"], limit=5)
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "odoo_version": odoo.version,
        "uid": odoo.uid,
        "modules": module_states,
        "companies": companies,
    }


def install_module(odoo: OdooRPC, name: str) -> str:
    ids = odoo.call("ir.module.module", "search", [("name", "=", name)])
    if not ids:
        return "absent"
    state = odoo.call("ir.module.module", "read", ids, fields=["state"])[0]["state"]
    if state == "installed":
        return "installed"
    odoo.call("ir.module.module", "button_immediate_install", ids)
    state = odoo.call("ir.module.module", "read", ids, fields=["state"])[0]["state"]
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://dev.hellenia.cloud")
    parser.add_argument("--db", default="hellenia_dev")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--tc", default="baseline", help="TC id or 'baseline'")
    parser.add_argument("--install", help="module to install (e.g. l10n_do)")
    args = parser.parse_args()

    odoo = OdooRPC(args.url, args.db, args.user, args.password)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = EVIDENCE_ROOT / day / args.tc.upper()
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {"tc": args.tc, "baseline": snapshot_baseline(odoo)}
    if args.install:
        result["install"] = {args.install: install_module(odoo, args.install)}
        result["post_install"] = snapshot_baseline(odoo)

    out_file = out_dir / "result.json"
    out_file.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result, indent=2, default=str))
    print(f"Wrote {out_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
