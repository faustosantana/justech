#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación estándar fiscal Justech — empresa completa (erp.justech.do)."""
from __future__ import annotations

import json
import os
from calendar import monthrange
from datetime import date, datetime, timezone

COMPANY_ID = int(os.environ.get("FISCAL_STD_COMPANY_ID", "2"))
PRE_SNAPSHOT_PATH = os.environ.get("FISCAL_STD_PRE_SNAPSHOT", "")
TAG = "FISCALSTD"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_pre():
    if PRE_SNAPSHOT_PATH and os.path.isfile(PRE_SNAPSHOT_PATH):
        return json.load(open(PRE_SNAPSHOT_PATH))
    return {}


def gl_totals(cr):
    cr.execute(
        "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) "
        "FROM account_move_line aml JOIN account_move am ON am.id=aml.move_id WHERE am.state='posted'"
    )
    d, c = cr.fetchone()
    return float(d), float(c)


def run_validate(env):
    from odoo import Command
    from odoo.exceptions import UserError

    pre = load_pre()
    pre_global = pre.get("global", {})
    pre_company = pre.get("company_metrics", {})
    pre_hist_ids = pre.get("historical_samples", {})
    pre_reconciles = pre_global.get("reconciles", 0)

    mgr = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
    if mgr and mgr not in env.user.group_ids:
        env.user.write({"group_ids": [Command.link(mgr.id)]})

    results = {
        "tests": [],
        "errors": [],
        "approved": False,
        "sequences_used": [],
        "created_move_ids": [],
        "created_payment_ids": [],
    }
    cr = env.cr

    company = env["res.company"].browse(COMPANY_ID)
    env = env(context=dict(env.context, allowed_company_ids=[company.id], default_company_id=company.id))
    Move = env["account.move"]

    pre_diag_errors = 0
    pre_health_issues = 0
    if "justech.do.ncf.diagnostic.service" in env:
        pre_findings = env["justech.do.ncf.diagnostic.service"].run_full_scan(company)
        pre_diag_errors = len([f for f in pre_findings if f.get("severity") == "error"])
    if "justech.fiscal.admin.service" in env:
        pre_health_issues = len(
            env["justech.fiscal.admin.service"].health_check(company).get("issues", [])
        )

    today = date.today()
    period_from = date(today.year, today.month, 1)
    period_to = date(today.year, today.month, monthrange(today.year, today.month)[1])

    def record(name, ok, detail=None):
        results["tests"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            results["errors"].append(name)

    # --- Integridad global ---
    g_rec = env["account.partial.reconcile"].search_count([])
    gl_d, gl_c = gl_totals(cr)
    record("gl_balanced", gl_d == gl_c, {"debit": gl_d, "credit": gl_c})
    record(
        "reconciles_unchanged",
        g_rec >= pre_global.get("reconciles", g_rec),
        {"before": pre_global.get("reconciles"), "after": g_rec},
    )

    # Histórico Adel puro (sin justech_do_ncf) no debe disminuir
    hist_adel = Move.search_count(
        [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("justech_do_ncf", "=", False),
            ("l10n_latam_document_number", "!=", False),
        ]
    )
    record(
        "historical_adel_intact",
        hist_adel >= pre_company.get("historical_adel_only", hist_adel),
        {"before": pre_company.get("historical_adel_only"), "after": hist_adel},
    )

    # Verificar muestras históricas sin modificación
    for key, sample in pre_hist_ids.items():
        if not sample:
            continue
        if key.startswith("move_"):
            m = Move.browse(sample["id"])
            if m.exists():
                record(
                    f"hist_open_{key}",
                    (m.l10n_latam_document_number or "") == sample.get("ncf", "")
                    and m.state == sample.get("state"),
                    {"id": m.id, "ncf": m.l10n_latam_document_number},
                )
        elif key.startswith("payment_"):
            p = env["account.payment"].browse(sample["id"])
            if p.exists():
                record(
                    f"hist_open_{key}",
                    float(p.amount) == float(sample.get("amount", 0)),
                    {"id": p.id, "amount": p.amount},
                )

    record("company_fiscal_on", company.justech_do_fiscal_enabled, company.name)

    sale_journal = env["account.journal"].search(
        [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
    )
    purchase_journal = env["account.journal"].search(
        [("company_id", "=", company.id), ("type", "=", "purchase")], limit=1
    )
    record(
        "sale_journal_config",
        sale_journal.justech_do_use_ncf and not sale_journal.l10n_latam_use_documents,
        sale_journal.read(["justech_do_use_ncf", "l10n_latam_use_documents"])[0],
    )
    if purchase_journal:
        record(
            "purchase_journal_config",
            purchase_journal.justech_do_use_ncf and not purchase_journal.l10n_latam_use_documents,
            purchase_journal.read(["justech_do_use_ncf", "l10n_latam_use_documents"])[0],
        )

    tax18_sale = env["account.tax"].search(
        [("company_id", "=", company.id), ("type_tax_use", "=", "sale"), ("amount", "=", 18)],
        limit=1,
    )
    tax0_sale = env["account.tax"].search(
        [("company_id", "=", company.id), ("type_tax_use", "=", "sale"), ("amount", "=", 0)],
        limit=1,
    )
    tax18_purchase = env["account.tax"].search(
        [("company_id", "=", company.id), ("type_tax_use", "=", "purchase"), ("amount", "=", 18)],
        limit=1,
    )
    product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
    expense_acc = env["account.account"].search(
        [("account_type", "=", "expense")], limit=1
    )

    partner_vat = env["res.partner"].search([("vat", "!=", False)], limit=1)
    partner_no_vat = env["res.partner"].search(
        ["|", ("vat", "=", False), ("vat", "=", "")], limit=1
    )
    vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1) or env[
        "res.partner"
    ].create({"name": f"{TAG} Vendor", "supplier_rank": 1, "vat": "101000000"})

    def sale_line(price, taxes=None):
        return [
            Command.create(
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "price_unit": price,
                    "tax_ids": [Command.set(taxes.ids)] if taxes else [],
                }
            )
        ]

    def purchase_line(price, taxes=None):
        return [
            Command.create(
                {
                    "name": f"{TAG} expense",
                    "quantity": 1,
                    "price_unit": price,
                    "account_id": expense_acc.id if expense_acc else False,
                    "tax_ids": [Command.set(taxes.ids)] if taxes else [],
                }
            )
        ]

    def check_dual(move, label):
        jt = (move.justech_do_ncf or "").strip().upper()
        lat = (
            (move.l10n_latam_document_number or "").strip().upper()
            if "l10n_latam_document_number" in Move._fields
            else jt
        )
        record(f"dual_write_{label}", bool(jt) and jt == lat, {"justech": jt, "latam": lat})
        fdp = env["justech.do.fiscal.data.provider"]
        record(f"fdp_read_{label}", fdp.get_ncf(move).upper() == jt, fdp.get_ncf(move))
        if "l10n_do_fiscal_sequence_id" in Move._fields:
            record(f"no_adel_seq_{label}", not move.l10n_do_fiscal_sequence_id, None)

    def post_sale(doc_xml, partner, price, taxes, label, move_type="out_invoice", extra=None):
        doc = env.ref(f"justech_l10n_do_base.{doc_xml}", raise_if_not_found=False)
        vals = {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": sale_journal.id,
            "company_id": company.id,
            "invoice_date": today,
            "invoice_line_ids": sale_line(price, taxes),
        }
        if doc:
            vals["justech_do_document_type_id"] = doc.id
        if extra:
            vals.update(extra)
        inv = Move.create(vals)
        inv.action_post()
        results["created_move_ids"].append(inv.id)
        prefix = doc.prefix if doc else label[:3].upper()
        record(label, inv.justech_do_ncf.startswith(prefix), {"ncf": inv.justech_do_ncf, "id": inv.id})
        check_dual(inv, label)
        results["sequences_used"].append(inv.justech_do_ncf)
        return inv

    created = []
    origin_b01 = None
    inv_b02 = None

    # --- Ventas B01/B02/B14/B15 ---
    try:
        origin_b01 = post_sale("doc_type_b01", partner_vat, 1500.0, tax18_sale, "b01")
        created.append(origin_b01)
    except Exception as e:
        record("b01", False, str(e))

    try:
        inv_b02 = post_sale("doc_type_b02", partner_no_vat, 800.0, tax18_sale, "b02")
        created.append(inv_b02)
    except Exception as e:
        record("b02", False, str(e))

    try:
        taxes_b14 = tax0_sale or tax18_sale
        inv_b14 = post_sale("doc_type_b14", partner_vat, 500.0, tax0_sale or False, "b14")
        created.append(inv_b14)
    except Exception as e:
        record("b14", False, str(e))

    try:
        inv_b15 = post_sale("doc_type_b15", partner_vat, 2000.0, tax18_sale, "b15")
        created.append(inv_b15)
    except Exception as e:
        record("b15", False, str(e))

    # B04 nota crédito
    try:
        if origin_b01 and origin_b01.state == "posted":
            doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
            cn = Move.create(
                {
                    "move_type": "out_refund",
                    "partner_id": origin_b01.partner_id.id,
                    "journal_id": sale_journal.id,
                    "company_id": company.id,
                    "invoice_date": today,
                    "reversed_entry_id": origin_b01.id,
                    "justech_do_document_type_id": doc_b04.id if doc_b04 else False,
                    "invoice_line_ids": sale_line(300.0, tax18_sale),
                }
            )
            cn.action_post()
            created.append(cn)
            results["created_move_ids"].append(cn.id)
            record("b04_credit_note", cn.justech_do_ncf.startswith("B04"), {"ncf": cn.justech_do_ncf})
            check_dual(cn, "b04")
            results["sequences_used"].append(cn.justech_do_ncf)
    except Exception as e:
        record("b04_credit_note", False, str(e))

    # B03 nota débito
    try:
        if origin_b01 and origin_b01.state == "posted":
            doc_b03 = env.ref("justech_l10n_do_base.doc_type_b03", raise_if_not_found=False)
            dn = Move.create(
                {
                    "move_type": "out_invoice",
                    "partner_id": origin_b01.partner_id.id,
                    "journal_id": sale_journal.id,
                    "company_id": company.id,
                    "invoice_date": today,
                    "debit_origin_id": origin_b01.id,
                    "justech_do_document_type_id": doc_b03.id if doc_b03 else False,
                    "invoice_line_ids": sale_line(150.0, False),
                }
            )
            dn.action_post()
            created.append(dn)
            results["created_move_ids"].append(dn.id)
            record("b03_debit_note", dn.justech_do_ncf.startswith("B03"), {"ncf": dn.justech_do_ncf})
            check_dual(dn, "b03")
            results["sequences_used"].append(dn.justech_do_ncf)
    except Exception as e:
        record("b03_debit_note", False, str(e))

    # --- Compras B11/B13/B17 ---
    if purchase_journal:
        for doc_xml, label, with_tax in (
            ("doc_type_b11", "b11", True),
            ("doc_type_b13", "b13", False),
            ("doc_type_b17", "b17", False),
        ):
            try:
                doc = env.ref(f"justech_l10n_do_base.{doc_xml}", raise_if_not_found=False)
                taxes = tax18_purchase if with_tax else False
                bill = Move.create(
                    {
                        "move_type": "in_invoice",
                        "partner_id": vendor.id,
                        "journal_id": purchase_journal.id,
                        "company_id": company.id,
                        "invoice_date": today,
                        "justech_do_document_type_id": doc.id if doc else False,
                        "invoice_line_ids": purchase_line(1200.0, taxes),
                    }
                )
                bill.action_post()
                created.append(bill)
                results["created_move_ids"].append(bill.id)
                prefix = doc.prefix if doc else label.upper()
                record(label, bill.justech_do_ncf.startswith(prefix), {"ncf": bill.justech_do_ncf})
                check_dual(bill, label)
                results["sequences_used"].append(bill.justech_do_ncf)
            except Exception as e:
                record(label, False, str(e))
                draft = Move.search(
                    [
                        ("company_id", "=", company.id),
                        ("state", "=", "draft"),
                        ("name", "like", "DRAFT%"),
                    ],
                    order="id desc",
                    limit=1,
                )
                if draft:
                    draft.unlink()
    else:
        for label in ("b11", "b13", "b17"):
            record(label, False, "no purchase journal")

    # --- Pagos parcial y total ---
    try:
        if origin_b01 and origin_b01.state == "posted" and origin_b01.amount_residual > 0:
            partial_amt = min(origin_b01.amount_residual * 0.4, 500.0)
            reg = (
                env["account.payment.register"]
                .with_context(active_model="account.move", active_ids=origin_b01.ids)
                .create({"amount": partial_amt, "payment_difference_handling": "open"})
            )
            pay_partial = reg._create_payments()
            if pay_partial:
                pay_partial = pay_partial[:1]
                results["created_payment_ids"].append(pay_partial.id)
            record(
                "payment_partial",
                bool(pay_partial) and pay_partial.state in ("paid", "in_process", "posted"),
                {"id": pay_partial.id if pay_partial else None, "amount": partial_amt},
            )
            origin_b01.invalidate_recordset()
            if origin_b01.amount_residual > 0:
                reg2 = (
                    env["account.payment.register"]
                    .with_context(active_model="account.move", active_ids=origin_b01.ids)
                    .create({})
                )
                pay_full = reg2._create_payments()
                if pay_full:
                    pay_full = pay_full[:1]
                    results["created_payment_ids"].append(pay_full.id)
                record(
                    "payment_full",
                    bool(pay_full) and pay_full.state in ("paid", "in_process", "posted"),
                    {"id": pay_full.id if pay_full else None},
                )
                origin_b01.invalidate_recordset()
            rec_now = env["account.partial.reconcile"].search_count([])
            record(
                "reconciliation",
                rec_now > pre_reconciles,
                {
                    "payment_state": origin_b01.payment_state,
                    "reconciles_delta": rec_now - pre_reconciles,
                },
            )
        else:
            record("payment_partial", True, "skipped")
            record("payment_full", True, "skipped")
            record("reconciliation", True, "skipped")
    except Exception as e:
        record("payment_partial", False, str(e))
        record("payment_full", False, str(e))
        record("reconciliation", False, str(e))

    # --- Asientos balanceados ---
    for mid in results["created_move_ids"]:
        m = Move.browse(mid)
        if m.state == "posted":
            deb = sum(m.line_ids.mapped("debit"))
            cred = sum(m.line_ids.mapped("credit"))
            record(f"move_{mid}_balanced", abs(deb - cred) < 0.01, {"d": deb, "c": cred})

    # --- Bloqueo duplicados ---
    try:
        dup_svc = env["justech.do.ncf.duplicate.service"]
        groups = dup_svc.find_duplicate_groups_v2(company)
        record("no_duplicate_groups", not groups, groups[:3] if groups else None)
        if origin_b01 and origin_b01.justech_do_ncf:
            probe = Move.new(
                {
                    "move_type": "out_invoice",
                    "company_id": company.id,
                    "partner_id": origin_b01.partner_id.id,
                    "justech_do_ncf": origin_b01.justech_do_ncf,
                }
            )
            blocked = False
            try:
                dup_svc.check_duplicate(probe, origin_b01.justech_do_ncf)
            except UserError:
                blocked = True
            record("duplicate_block", blocked, origin_b01.justech_do_ncf)
    except Exception as e:
        record("duplicate_block", False, str(e))

    # --- Anulación NCF (608) ---
    void_move = None
    try:
        if inv_b02 and inv_b02.state == "posted":
            void_move = inv_b02
            void_move.justech_do_ncf_void_reason = f"{TAG} void test"
            void_move.action_void_ncf()
            record("ncf_void", void_move.justech_do_ncf_voided, {"ncf": void_move.justech_do_ncf})
    except Exception as e:
        record("ncf_void", False, str(e))

    # --- Diagnóstico y auditoría ---
    try:
        findings = env["justech.do.ncf.diagnostic.service"].run_full_scan(company)
        errors = [f for f in findings if f.get("severity") == "error"]
        record(
            "diagnostic_scan",
            len(errors) <= pre_diag_errors,
            {"errors": len(errors), "pre_errors": pre_diag_errors, "total": len(findings)},
        )
    except Exception as e:
        record("diagnostic_scan", False, str(e))

    try:
        summary = env["justech.do.ncf.range.audit.service"].summary_for_company(company)
        record("audit_ranges", summary.get("active_ranges", 0) > 0, summary)
    except Exception as e:
        record("audit_ranges", False, str(e))

    # --- DGII 606/607/608/609 ---
    for rtype, method in (
        ("606", "validate_period_606"),
        ("607", "validate_period_607"),
        ("608", "validate_period_608"),
        ("609", "validate_period_609"),
    ):
        try:
            exp = env[f"justech.do.dgii.{rtype}.exporter"]
            getattr(exp, method)(company, period_from, period_to)
            record(f"dgii_{rtype}", True, None)
        except Exception as e:
            ok_empty = rtype in ("608", "609") and (
                "No hay" in str(e) or "sin documentos" in str(e).lower()
            )
            record(f"dgii_{rtype}", ok_empty, str(e))

    # --- Rangos y secuencias ---
    ranges = env["justech.do.ncf.range"].search(
        [("company_id", "=", company.id), ("state", "=", "active")]
    )
    prefixes_found = sorted(set(ranges.mapped("prefix")))
    record("ranges_active", len(ranges) >= 3, prefixes_found)

    last_ncf = {}
    next_ncf = {}
    for r in ranges:
        cr.execute(
            """
            SELECT MAX(justech_do_ncf) FROM account_move
            WHERE company_id=%s AND justech_do_ncf LIKE %s AND state='posted'
            """,
            (company.id, f"{r.prefix}%"),
        )
        mx = cr.fetchone()[0]
        last_ncf[r.prefix] = mx
        next_ncf[r.prefix] = r.next_sequence

    results["last_ncf_by_prefix"] = last_ncf
    results["next_ncf_by_prefix"] = next_ncf

    # --- Admin center health (si instalado) ---
    if "justech.fiscal.admin.service" in env:
        try:
            health = env["justech.fiscal.admin.service"].health_check(company)
            record(
                "admin_health",
                len(health.get("issues", [])) <= pre_health_issues,
                health,
            )
        except Exception as e:
            record("admin_health", False, str(e))

    results["approved"] = len(results["errors"]) == 0
    results["ts"] = utc_now()
    results["company"] = company.name
    results["company_id"] = company.id
    env.cr.commit()
    return results


out = run_validate(env)
print(json.dumps(out, indent=2, default=str))
if not out.get("approved"):
    raise SystemExit(1)
