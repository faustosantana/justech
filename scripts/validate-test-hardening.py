#!/usr/bin/env python3
"""TEST promotion — validaciones Sprint 0 hardening (odoo shell)."""
from __future__ import annotations

import json

result = {"ok": True, "checks": {}, "errors": []}


def ok(name, detail=""):
    result["checks"][name] = {"status": "PASS", "detail": detail}


def fail(name, msg):
    result["ok"] = False
    result["errors"].append(f"{name}: {msg}")
    result["checks"][name] = {"status": "FAIL", "detail": msg}


# Módulos instalados
for mod in ("justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports"):
    rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    if rec.state != "installed":
        fail(f"module_{mod}", rec.state)
    else:
        ok(f"module_{mod}", "installed")

# Record rules multiempresa
rule_models = {
    "justech.do.fiscal.document.type": "company_ids",
    "justech.do.ncf.range": "company_ids",
    "justech.do.ncf.consumption": "company_ids",
    "justech.do.fiscal.report": "company_ids",
    "justech.do.fiscal.report.line": "company",
    "justech.do.fiscal.report.wizard": "company_ids",
}
for model_name, token in rule_models.items():
    rules = env["ir.rule"].search([("model_id.model", "=", model_name)])
    if not rules.filtered(lambda r: token in (r.domain_force or "")):
        fail(f"rule_{model_name}", "missing company rule")
    else:
        ok(f"rule_{model_name}", token)

# Índice único NCF
env.cr.execute(
    """
    SELECT indexname FROM pg_indexes
    WHERE indexname = 'account_move_justech_do_ncf_company_uniq'
    """
)
if env.cr.fetchone():
    ok("ncf_unique_index", "account_move_justech_do_ncf_company_uniq")
else:
    fail("ncf_unique_index", "missing")

# Void sin permisos de manager
from odoo.exceptions import AccessError

move = env["account.move"].search(
    [("justech_do_ncf", "!=", False), ("state", "=", "posted")], limit=1
)
if move:
    fiscal_user = env.ref("justech_l10n_do_base.group_justech_do_fiscal_user")
    users = env["res.users"].search([("group_ids", "in", fiscal_user.id)], limit=1)
    if users and users != env.ref("base.user_admin"):
        test_user = users
    else:
        test_user = env["res.users"].create(
            {
                "name": "TEST Fiscal User",
                "login": f"test_fiscal_{env.cr.dbname}@hellenia.test",
                "group_ids": [
                    (6, 0, [env.ref("base.group_user").id, fiscal_user.id])
                ],
            }
        )
    move.justech_do_ncf_void_reason = "Should fail permission test"
    try:
        move.with_user(test_user).action_void_ncf()
        fail("void_permission", "AccessError expected")
    except AccessError:
        ok("void_permission", "blocked for fiscal user")
else:
    fail("void_permission", "no posted move with NCF found")

print("TEST_HARDENING ok:", json.dumps(result["ok"]))
print(json.dumps(result, indent=2, default=str))
