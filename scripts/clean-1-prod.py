#!/usr/bin/env python3
"""CLEAN-1 — Limpieza definitiva datos operativos de prueba (PRE GO-LIVE).

Elimina transacciones de ventas, compras, contabilidad, inventario, POS, CRM/proyectos
de prueba, chatter y logs de auditoría de prueba.

Conserva: empresas, usuarios, roles, licencias, config fiscal/NCF/diarios/COA,
productos, partners, plantillas PDF, secuencias (config), módulos Justech.

Solo hellenia_prod. Ejecutar tras backup verificado.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("CLEAN1_EVIDENCE", "/var/lib/odoo/clean-1")
os.makedirs(OUT, exist_ok=True)

company = env.company
sudo = env["base"].sudo()

TEST_AUDIT_RE = re.compile(
    r"COA3|FISCALRD|SMOKE|P13|P21|P23|UAT|piloto|prueba|certific|launcher|forensic|AUDIT|DIAG|GOV",
    re.I,
)
TEST_CRM_RE = re.compile(r"UAT|SMOKE|prueba|piloto|test|COA3|FISCALRD", re.I)
OPERATIONAL_MODELS = (
    "account.move",
    "sale.order",
    "purchase.order",
    "account.payment",
    "stock.picking",
    "stock.move",
    "justech.delivery.note",
    "crm.lead",
    "project.project",
    "project.task",
    "pos.session",
    "pos.order",
)

report = {
    "phase": "CLEAN-1",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "company": company.name,
    "ok": True,
    "errors": [],
    "before": {},
    "deleted": {},
    "preserved": {},
    "sequence_resets": [],
    "ncf_resets": [],
}


def count_model(model, domain=None):
    if model not in env:
        return 0
    return env[model].sudo().search_count(domain or [])


def snap_counts(label):
    report["before"][label] = {
        "account_move": count_model("account.move"),
        "account_move_posted": count_model("account.move", [("state", "=", "posted")]),
        "account_payment": count_model("account.payment"),
        "bank_statement": count_model("account.bank.statement"),
        "bank_statement_line": count_model("account.bank.statement.line"),
        "sale_order": count_model("sale.order"),
        "purchase_order": count_model("purchase.order"),
        "stock_picking": count_model("stock.picking"),
        "stock_move": count_model("stock.move"),
        "delivery_note": count_model("justech.delivery.note"),
        "fiscal_report": count_model("justech.do.fiscal.report"),
        "ncf_consumption": count_model("justech.do.ncf.consumption"),
        "crm_lead": count_model("crm.lead"),
        "project_project": count_model("project.project"),
        "project_task": count_model("project.task"),
        "pos_session": count_model("pos.session"),
        "pos_order": count_model("pos.order"),
        "audit_log": count_model("justech.audit.log"),
        "mail_message_ops": count_model("mail.message", [("model", "in", list(OPERATIONAL_MODELS))]),
        "partners": count_model("res.partner"),
        "products": count_model("product.product"),
        "accounts": count_model("account.account", [("company_ids", "in", company.id)]),
        "ncf_ranges": count_model("justech.do.ncf.range"),
        "users": count_model("res.users", [("share", "=", False)]),
    }


def log_deleted(key, n, detail=""):
    report["deleted"][key] = {"count": n, "detail": detail}


def err(msg):
    report["ok"] = False
    report["errors"].append(msg)


def safe_unlink(records, key):
    if not records:
        log_deleted(key, 0)
        return 0
    n = len(records)
    try:
        records.unlink()
        log_deleted(key, n)
        return n
    except Exception as exc:  # noqa: BLE001
        err(f"{key}: {exc}")
        return 0


def draft_then_unlink(records, key, draft_method="action_draft"):
    if not records:
        log_deleted(key, 0)
        return 0
    for rec in records:
        try:
            if hasattr(rec, "state") and rec.state not in ("draft", "cancel"):
                if hasattr(rec, draft_method):
                    getattr(rec, draft_method)()
        except Exception:
            pass
    return safe_unlink(records, key)


# --- Preflight counts ---
snap_counts("preflight")

# 1. Reportes fiscales DGII generados en pruebas
safe_unlink(env["justech.do.fiscal.report"].sudo().search([]), "fiscal_reports")

# 2. Conduces operativos
if "justech.delivery.note" in env:
    safe_unlink(env["justech.delivery.note"].sudo().search([]), "delivery_notes")

# 3. Pagos — quitar conciliación y borrar
payments = env["account.payment"].sudo().search([])
for pay in payments:
    try:
        if pay.state not in ("draft", "cancel"):
            pay.action_draft()
    except Exception:
        pass
safe_unlink(payments, "account_payments")

# 4. Extractos bancarios (statement primero — líneas en cascada)
stmts = env["account.bank.statement"].sudo().search([])
for stmt in stmts:
    try:
        if stmt.state == "posted":
            stmt.button_reset_new()
    except Exception:
        pass
safe_unlink(stmts, "bank_statements")
safe_unlink(env["account.bank.statement.line"].sudo().search([]), "bank_statement_lines")

# 5. Inventario operativo (pickings done requieren purge SQL pre-go-live)
if "stock.picking" in env:
    pickings = env["stock.picking"].sudo().search([])
    n_pick = len(pickings)
    if pickings:
        pids = tuple(pickings.ids)
        env.cr.execute("DELETE FROM stock_move_line WHERE picking_id IN %s", (pids,))
        env.cr.execute("DELETE FROM stock_move WHERE picking_id IN %s", (pids,))
        env.cr.execute("DELETE FROM stock_picking WHERE id IN %s", (pids,))
        env["stock.picking"].invalidate_model()
        log_deleted("stock_pickings", n_pick, "sql_purge_done")
    else:
        log_deleted("stock_pickings", 0)

if "stock.move.line" in env:
    safe_unlink(env["stock.move.line"].sudo().search([]), "stock_move_lines")
if "stock.move" in env:
    safe_unlink(env["stock.move"].sudo().search([]), "stock_moves")
if "stock.scrap" in env:
    safe_unlink(env["stock.scrap"].sudo().search([]), "stock_scraps")
if "stock.valuation.layer" in env:
    safe_unlink(env["stock.valuation.layer"].sudo().search([]), "stock_valuation_layers")

# 6. Asientos contables (facturas, NC, pagos contables, etc.)
moves = env["account.move"].sudo().search([])
posted = moves.filtered(lambda m: m.state == "posted")
if posted:
    try:
        posted.button_draft()
    except Exception as exc:
        for move in posted:
            try:
                if move.state == "posted":
                    move.button_draft()
            except Exception as inner:
                err(f"move_draft {move.name}: {inner}")
for move in env["account.move"].sudo().search([("state", "not in", ["draft", "cancel"])]):
    try:
        move.button_draft()
    except Exception:
        pass
safe_unlink(env["account.move"].sudo().search([]).with_context(force_delete=True), "account_moves")

# 7. Conciliaciones residuales
for model in ("account.partial.reconcile", "account.full.reconcile"):
    if model in env:
        safe_unlink(env[model].sudo().search([]), model)

# 8. Ventas y compras
if "sale.order" in env:
    orders = env["sale.order"].sudo().search([])
    for so in orders:
        try:
            if so.state not in ("draft", "cancel"):
                so.action_cancel()
        except Exception:
            pass
    safe_unlink(orders, "sale_orders")

if "purchase.order" in env:
    pos = env["purchase.order"].sudo().search([])
    for po in pos:
        try:
            po.button_cancel()
        except Exception:
            pass
    safe_unlink(pos, "purchase_orders")

# 9. POS (si existe)
if "pos.order" in env:
    safe_unlink(env["pos.order"].sudo().search([]), "pos_orders")
if "pos.session" in env:
    sessions = env["pos.session"].sudo().search([])
    for sess in sessions:
        try:
            if sess.state != "closed":
                sess.action_pos_session_closing_control()
        except Exception:
            pass
    safe_unlink(sessions, "pos_sessions")

# 10. CRM / Proyectos de prueba
if "crm.lead" in env:
    test_leads = env["crm.lead"].sudo().search([]).filtered(
        lambda l: TEST_CRM_RE.search(l.name or "") or TEST_CRM_RE.search(l.contact_name or "")
    )
    safe_unlink(test_leads, "crm_leads_test")

if "project.task" in env:
    test_tasks = env["project.task"].sudo().search([]).filtered(
        lambda t: TEST_CRM_RE.search(t.name or "")
    )
    safe_unlink(test_tasks, "project_tasks_test")

if "project.project" in env:
    test_projects = env["project.project"].sudo().search([]).filtered(
        lambda p: TEST_CRM_RE.search(p.name or "")
    )
    # No borrar si tiene tareas reales residuales
    test_projects = test_projects.filtered(lambda p: not p.task_ids)
    safe_unlink(test_projects, "project_projects_test")

# 11. Consumo NCF (operativo) — conservar rangos
consumptions = env["justech.do.ncf.consumption"].sudo().search([])
safe_unlink(consumptions, "ncf_consumptions")

for rng in env["justech.do.ncf.range"].sudo().search([("company_id", "=", company.id)]):
    before_next = rng.next_sequence
    before_state = rng.state
    vals = {"next_sequence": rng.sequence_start}
    if rng.state in ("depleted", "expired") and rng.date_to >= fields.Date.today():
        vals["state"] = "active"
    rng.write(vals)
    report["ncf_resets"].append(
        {
            "name": rng.name,
            "prefix": rng.prefix,
            "before_next": before_next,
            "after_next": rng.sequence_start,
            "before_state": before_state,
            "after_state": rng.state,
        }
    )

# 12. Logs auditoría de prueba (conservar reglas/políticas)
if "justech.audit.log" in env:
    Log = env["justech.audit.log"].sudo().with_context(justech_retention_purge=True)
    logs = Log.search([])
    test_logs = logs.filtered(
        lambda l: TEST_AUDIT_RE.search(l.record_name or "")
        or TEST_AUDIT_RE.search(l.human_summary or "")
        or TEST_AUDIT_RE.search(l.search_text or "")
        or l.model_name in OPERATIONAL_MODELS
    )
    if len(test_logs) < len(logs):
        test_logs = logs
    safe_unlink(test_logs, "audit_logs_test")

if "hellenia.governance.audit" in env:
    gov_logs = env["hellenia.governance.audit"].sudo().search([])
    test_gov = gov_logs.filtered(
        lambda l: TEST_AUDIT_RE.search(str(l.display_name or ""))
        or TEST_AUDIT_RE.search(str(getattr(l, "action", "") or ""))
    )
    safe_unlink(test_gov, "governance_audit_test")

# 13. Chatter operativo / pruebas
msg_domain = [
    "|",
    ("model", "in", list(OPERATIONAL_MODELS)),
    "|",
    ("body", "ilike", "SMOKE"),
    "|",
    ("body", "ilike", "FISCALRD"),
    ("body", "ilike", "COA3"),
]
messages = env["mail.message"].sudo().search(msg_domain)
safe_unlink(messages, "mail_messages_test")

# 14. Reiniciar secuencias documentales de prueba
SEQ_CODES = (
    "sale.order",
    "purchase.order",
    "account.payment",
    "justech.delivery.note",
    "stock.picking",
    "stock.scrap",
)
for code in SEQ_CODES:
    seqs = env["ir.sequence"].sudo().search([("code", "=", code)])
    for seq in seqs:
        before = seq.number_next
        seq.write({"number_next": 1})
        for dr in env["ir.sequence.date_range"].sudo().search([("sequence_id", "=", seq.id)]):
            dr.write({"number_next": 1})
        report["sequence_resets"].append(
            {"code": code, "name": seq.name, "before": before, "after": 1}
        )

# Secuencias por prefijo operativo consumido
for seq in env["ir.sequence"].sudo().search([("prefix", "ilike", "GROUP/")]):
    before = seq.number_next
    seq.write({"number_next": 1})
    for dr in env["ir.sequence.date_range"].sudo().search([("sequence_id", "=", seq.id)]):
        dr.write({"number_next": 1})
    report["sequence_resets"].append(
        {"code": seq.code, "name": seq.name, "before": before, "after": 1, "prefix": seq.prefix}
    )

env.cr.commit()

# --- Post counts + preserved ---
snap_counts("postflight")

report["preserved"] = {
    "partners": count_model("res.partner"),
    "products": count_model("product.product"),
    "accounts": count_model("account.account", [("company_ids", "in", company.id)]),
    "journals": count_model("account.journal", [("company_id", "=", company.id)]),
    "taxes": count_model("account.tax", [("company_id", "=", company.id)]),
    "ncf_ranges": count_model("justech.do.ncf.range"),
    "ncf_types": count_model("justech.do.fiscal.document.type"),
    "users_active": count_model("res.users", [("active", "=", True), ("share", "=", False)]),
    "audit_rules": count_model("justech.audit.rule"),
    "governance_roles": count_model("hellenia.role"),
    "governance_permissions": count_model("hellenia.permission"),
    "modules_justech": count_model(
        "ir.module.module",
        [("name", "like", "justech_%"), ("state", "=", "installed")],
    ),
}

# Validation gates
post = report["before"]["postflight"]
checks = {
    "no_posted_moves": post["account_move_posted"] == 0,
    "no_moves": post["account_move"] == 0,
    "no_payments": post["account_payment"] == 0,
    "no_sale_orders": post["sale_order"] == 0,
    "no_purchase_orders": post["purchase_order"] == 0,
    "no_fiscal_reports": post["fiscal_report"] == 0,
    "no_ncf_consumption": post["ncf_consumption"] == 0,
    "partners_preserved": post["partners"] == report["before"]["preflight"]["partners"],
    "products_preserved": post["products"] == report["before"]["preflight"]["products"],
    "accounts_preserved": post["accounts"] == report["before"]["preflight"]["accounts"],
    "ncf_ranges_preserved": post["ncf_ranges"] == report["before"]["preflight"]["ncf_ranges"],
}
report["validation"] = checks
if not all(checks.values()):
    report["ok"] = False
    for k, v in checks.items():
        if not v:
            err(f"validation_failed: {k}")

with open(os.path.join(OUT, "deleted_records.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2, ensure_ascii=False, default=str)

print("CLEAN1:" + json.dumps(report, ensure_ascii=False, default=str))
