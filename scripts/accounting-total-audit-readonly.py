#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auditoría contable total — SOLO LECTURA (P1/P2).

Garantías:
- No create / write / unlink
- No -u / -i módulos
- Solo search, read, SQL SELECT vía ORM/cr.execute SELECT

Salida: ACCOUNTING_TOTAL_AUDIT:{json}
"""
from __future__ import annotations

import json
import traceback
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

DB = env.cr.dbname
ENV_MAP = {"hellenia_dev": "dev", "hellenia_test": "test", "hellenia_prod": "prod"}
if DB not in ENV_MAP:
    raise SystemExit(f"ABORT: DB no reconocida: {DB}")

ENV = ENV_MAP[DB]
TOL = 0.05
YEAR = date.today().year

report = {
    "phase": "accounting-total-audit-readonly",
    "version": "1.0",
    "mode": "read_only",
    "environment": ENV,
    "database": DB,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "company": {},
    "modules": {},
    "areas": {},
    "integrity": {},
    "findings": {"critical": [], "high": [], "medium": [], "low": [], "info": []},
    "summary": {},
    "errors": [],
    "ok": True,
    "pass": False,
}

KEY_ACCOUNTS = {
    "receivable": "11030201",
    "payable": "21010200",
    "inventory": "11050100",
    "cogs": "51010100",
    "cash": "11010100",
    "bank": "11010201",
    "itbis_paid": "11080101",
}

EXPECTED_JOURNALS = {
    "INV": "sale",
    "FACTU": "purchase",
    "BNK1": "bank",
    "CSH1": "cash",
    "MISCE": "general",
    "STJ": "general",
    "CAMBI": "general",
    "TAX": "general",
    "CABA": "general",
}


def finding(severity, area, code, message, detail=None):
    entry = {"area": area, "code": code, "message": message}
    if detail is not None:
        entry["detail"] = detail
    report["findings"][severity].append(entry)
    if severity in ("critical", "high"):
        report["ok"] = False


def area_ok(name, checks):
    report["areas"][name] = checks
    fails = [k for k, v in checks.items() if isinstance(v, dict) and v.get("ok") is False]
    if fails:
        report["ok"] = False


def check_result(ok, detail=""):
    return {"ok": bool(ok), "detail": str(detail)[:2000]}


def safe(fn, default=None, label=""):
    try:
        return fn()
    except Exception as exc:
        msg = f"{label}: {exc}" if label else str(exc)
        report["errors"].append(msg[:500])
        return default


env.cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
_company_row = env.cr.fetchone()
COMPANY_ID = _company_row[0] if _company_row else 1

partner_col_ok = True
try:
    env.cr.execute("SELECT justech_do_partner_id_type FROM res_partner LIMIT 0")
except Exception:
    partner_col_ok = False
report["schema"] = {"partner_id_type_column": partner_col_ok}
SKIP_FULL_AUDIT = ENV == "dev" and not partner_col_ok
if SKIP_FULL_AUDIT:
    finding("high", "environment", "ENV-01", "DEV desincronizado: falta columna res_partner.justech_do_partner_id_type")
    report["summary"] = {
        "dev_health": "schema_desync",
        "audit_completed": False,
        "reason": "ORM partner fields unavailable — ejecutar -u módulos fiscales en DEV antes de re-auditar",
    }
    report["ok"] = False
    report["pass"] = False
else:
    env.cr.execute("""
        SELECT c.id, c.name, p.vat, co.code, cur.name
        FROM res_company c
        JOIN res_partner p ON p.id = c.partner_id
        LEFT JOIN res_country co ON co.id = p.country_id
        LEFT JOIN res_currency cur ON cur.id = c.currency_id
        WHERE c.id = %s
    """, (COMPANY_ID,))
    co_row = env.cr.fetchone()
    report["company"] = {
        "id": co_row[0] if co_row else COMPANY_ID,
        "name": co_row[1] if co_row else None,
        "vat": co_row[2] if co_row else None,
        "country": co_row[3] if co_row else None,
        "currency": co_row[4] if co_row else None,
        "fiscal_enabled": None,
    }
    env.cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'res_company' AND column_name = 'justech_do_fiscal_enabled'
    """)
    if env.cr.fetchone():
        env.cr.execute("SELECT justech_do_fiscal_enabled FROM res_company WHERE id = %s", (COMPANY_ID,))
        row = env.cr.fetchone()
        report["company"]["fiscal_enabled"] = row[0] if row else None

    company = env["res.company"].browse(COMPANY_ID)

    mod_names = [
        "account", "account_reports", "stock", "sale", "purchase", "point_of_sale",
        "hellenia_account", "hellenia_pos", "hellenia_reports", "hellenia_base",
        "justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports",
        "justech_report_design",
]
    for m in env["ir.module.module"].search([("name", "in", mod_names)]):
        report["modules"][m.name] = {"state": m.state, "version": m.latest_version}

    Move = env["account.move"]
    Payment = env["account.payment"]
    AML = env["account.move.line"]
    Account = env["account.account"]
    Journal = env["account.journal"]
    Product = env["product.product"]
    Category = env["product.category"]

    # =============================================================================
    # 1. Plan de cuentas
    # =============================================================================
    accounts_data = safe(
        lambda: Account.search_read(
            [("company_ids", "in", company.id)],
            ["code", "name", "account_type", "active"],
        ),
        [],
        "accounts.search_read",
    )
    type_counts = Counter(a.get("account_type") for a in accounts_data)
    by_code = {a["code"]: a for a in accounts_data if a.get("code")}

    key_accounts = {}
    for role, code in KEY_ACCOUNTS.items():
        acc = by_code.get(code)
        key_accounts[role] = {
            "code": code,
            "found": bool(acc),
            "name": acc.get("name") if acc else None,
            "type": acc.get("account_type") if acc else None,
            "active": acc.get("active") if acc else None,
        }

    env.cr.execute("""
        SELECT COUNT(DISTINCT am.id)
        FROM account_move am
        JOIN account_move_line aml ON aml.move_id = am.id
        JOIN account_account aa ON aa.id = aml.account_id
        WHERE am.state = 'posted'
          AND am.company_id = %s
          AND aa.active IS FALSE
    """, (company.id,))
    deprecated_used = env.cr.fetchone()[0]

    english_names = sum(
        1 for a in accounts_data
        if a.get("name") and any(
            w in a["name"].lower()
            for w in ("inventory", "accounts receivable", "accounts payable", "cost of goods")
        )
    )

    area_ok("chart_of_accounts", {
        "total_accounts": check_result(True, len(accounts_data)),
        "type_distribution": check_result(True, dict(type_counts)),
        "key_accounts": check_result(all(v["found"] for v in key_accounts.values()), key_accounts),
        "deprecated_used_in_posted": check_result(deprecated_used == 0, f"count={deprecated_used}"),
        "english_name_sample": check_result(True, f"sample_english_names={english_names}"),
    })

    if not all(v["found"] for v in key_accounts.values()):
        missing = [k for k, v in key_accounts.items() if not v["found"]]
        finding("high", "chart_of_accounts", "ACC-01", f"Cuentas clave faltantes: {missing}", key_accounts)
    if deprecated_used:
        finding("medium", "chart_of_accounts", "ACC-02", f"Asientos posted usan cuentas deprecated: {deprecated_used}")
    if english_names > 50:
        finding("info", "chart_of_accounts", "ACC-03", "Nombres en inglés en plan — validar traducción es_DO UI")

    # =============================================================================
    # 2. Diarios contables
    # =============================================================================
    journals = Journal.search([("company_id", "=", company.id)])
    journal_map = {j.code: j for j in journals if j.code}
    journal_detail = {}
    journal_checks = {}
    for code, jtype in EXPECTED_JOURNALS.items():
        j = journal_map.get(code)
        journal_detail[code] = {
            "found": bool(j),
            "name": j.name if j else None,
            "type": j.type if j else None,
            "expected_type": jtype,
            "type_match": (j.type == jtype) if j else False,
        }
        journal_checks[f"journal_{code}"] = check_result(
            j and (j.type == jtype or code in ("STJ", "MISCE", "CAMBI", "TAX", "CABA")),
            journal_detail[code],
        )

    pos_journal_linked = safe(
        lambda: [
            {"config": c.name, "journal": c.journal_id.code if c.journal_id else None}
            for c in env["pos.config"].search([])
        ] if "pos.config" in env else [],
        [],
    )

    area_ok("journals", {
        **journal_checks,
        "total_journals": check_result(True, len(journals)),
        "journal_list": check_result(True, [{"code": j.code, "name": j.name, "type": j.type} for j in journals]),
        "pos_linked_journals": check_result(True, pos_journal_linked),
    })

    missing_journals = [c for c, d in journal_detail.items() if not d["found"]]
    if missing_journals:
        finding("medium", "journals", "JRN-01", f"Diarios esperados no encontrados: {missing_journals}")

    # =============================================================================
    # 3. Productos
    # =============================================================================
    cats_total = safe(lambda: Category.search_count([]), 0, "categories.total")
    cats_no_income_count = safe(
        lambda: Category.search_count([("property_account_income_categ_id", "=", False), ("id", "!=", 1)]),
        -1,
        "categories.income",
    )
    cats_no_expense_count = safe(
        lambda: Category.search_count([("property_account_expense_categ_id", "=", False), ("id", "!=", 1)]),
        -1,
        "categories.expense",
    )
    products_sale = safe(lambda: Product.search_count([("sale_ok", "=", True)]), 0, "products.sale")
    products_pos = safe(
        lambda: Product.search_count([("available_in_pos", "=", True)]) if "available_in_pos" in Product._fields else 0,
        0,
        "products.pos",
    )
    products_no_sale_tax = safe(lambda: Product.search_count([("sale_ok", "=", True), ("taxes_id", "=", False)]), 0, "products.no_sale_tax")
    products_no_purchase_tax = safe(lambda: Product.search_count([("purchase_ok", "=", True), ("supplier_taxes_id", "=", False)]), 0, "products.no_purchase_tax")

    area_ok("products", {
        "categories_total": check_result(cats_total >= 0, cats_total),
        "categories_without_income_account": check_result(cats_no_income_count == 0, cats_no_income_count),
        "categories_without_expense_account": check_result(cats_no_expense_count == 0, cats_no_expense_count),
        "products_sale_ok": check_result(True, products_sale),
        "products_pos_available": check_result(True, products_pos),
        "products_sale_without_tax": check_result(products_no_sale_tax == 0, products_no_sale_tax),
        "products_purchase_without_tax": check_result(products_no_purchase_tax == 0, products_no_purchase_tax),
    })

    if cats_no_income_count > 0:
        finding("high", "products", "PRD-01", f"Categorías sin cuenta ingreso: {cats_no_income_count}")
    elif cats_no_income_count < 0:
        finding("medium", "products", "PRD-01E", "No se pudo evaluar categorías ingreso (error ORM)")
    if cats_no_expense_count > 0:
        finding("high", "products", "PRD-02", f"Categorías sin cuenta gasto/costo: {cats_no_expense_count}")
    elif cats_no_expense_count < 0:
        finding("medium", "products", "PRD-02E", "No se pudo evaluar categorías gasto (error ORM)")
    if products_no_sale_tax:
        finding("medium", "products", "PRD-03", f"Productos venta sin impuesto: {products_no_sale_tax}")

    # =============================================================================
    # 4–5. Compras y Ventas (posted moves)
    # =============================================================================
    posted = Move.search([("state", "=", "posted"), ("company_id", "=", company.id)])
    unbalanced = []
    for m in posted:
        d = sum(m.line_ids.mapped("debit"))
        c = sum(m.line_ids.mapped("credit"))
        if abs(d - c) > TOL:
            unbalanced.append({"name": m.name, "debit": d, "credit": c, "diff": d - c})

    ytd_aml = AML.search([
        ("parent_state", "=", "posted"),
        ("date", ">=", f"{YEAR}-01-01"),
        ("date", "<=", f"{YEAR}-12-31"),
        ("company_id", "=", company.id),
    ])
    td = sum(ytd_aml.mapped("debit"))
    tc = sum(ytd_aml.mapped("credit"))

    out_inv = Move.search([("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("company_id", "=", company.id)])
    in_inv = Move.search([("move_type", "=", "in_invoice"), ("state", "=", "posted"), ("company_id", "=", company.id)])
    out_refund = Move.search([("move_type", "=", "out_refund"), ("state", "=", "posted"), ("company_id", "=", company.id)])
    in_refund = Move.search([("move_type", "=", "in_refund"), ("state", "=", "posted"), ("company_id", "=", company.id)])

    paid_with_residual = []
    open_no_residual = []
    partners_no_vat_invoices = []
    for inv in out_inv:
        residual = abs(inv.amount_residual)
        if inv.payment_state == "paid" and residual > TOL:
            paid_with_residual.append(inv.name)
        if inv.payment_state in ("not_paid", "partial", "in_payment") and residual < TOL:
            open_no_residual.append(inv.name)

    env.cr.execute("""
        SELECT am.name FROM account_move am
        JOIN res_partner rp ON rp.id = am.partner_id
        WHERE am.state = 'posted'
          AND am.move_type = 'out_invoice'
          AND am.company_id = %s
          AND COALESCE(NULLIF(TRIM(rp.vat), ''), '') = ''
    """, (company.id,))
    partners_no_vat_invoices = [row[0] for row in env.cr.fetchall()]

    report["integrity"] = {
        "posted_moves": len(posted),
        "unbalanced_count": len(unbalanced),
        "ytd_debit": td,
        "ytd_credit": tc,
        "ytd_balanced": abs(td - tc) < TOL,
    }

    area_ok("purchases", {
        "posted_vendor_bills": check_result(True, len(in_inv)),
        "posted_vendor_refunds": check_result(True, len(in_refund)),
        "vendor_paid_with_residual": check_result(
            not any(i.payment_state == "paid" and abs(i.amount_residual) > TOL for i in in_inv),
            len(in_inv),
        ),
    })

    area_ok("sales", {
        "posted_customer_invoices": check_result(True, len(out_inv)),
        "posted_credit_notes": check_result(True, len(out_refund)),
        "paid_with_residual": check_result(not paid_with_residual, paid_with_residual[:10]),
        "open_without_residual": check_result(not open_no_residual, open_no_residual[:10]),
        "invoices_partner_without_vat": check_result(not partners_no_vat_invoices, len(partners_no_vat_invoices)),
    })

    if unbalanced:
        finding("critical", "integrity", "INT-01", f"Asientos descuadrados: {[u['name'] for u in unbalanced[:10]]}", unbalanced[:5])
    if abs(td - tc) >= TOL:
        finding("critical", "integrity", "INT-02", f"YTD no cuadra: debit={td:.2f} credit={tc:.2f}")
    if paid_with_residual:
        finding("medium", "sales", "SAL-01", f"Facturas pagadas con residual: {paid_with_residual[:5]}")
    if partners_no_vat_invoices:
        finding("high", "sales", "FISC-01", f"Facturas posted sin RNC partner: {len(partners_no_vat_invoices)}", partners_no_vat_invoices[:10])
    if len(in_inv) == 0:
        finding("info", "purchases", "PUR-01", "Sin facturas proveedor posted — área no ejercitada")

    # =============================================================================
    # 6. Inventario
    # =============================================================================
    inv_data = {}
    if "stock.warehouse" in env:
        wh = env["stock.warehouse"].search([])
        inv_data["warehouses"] = [{"name": w.name, "code": w.code} for w in wh]
        inv_data["warehouse_count"] = len(wh)
    if "stock.valuation.layer" in env:
        layers = env["stock.valuation.layer"].search([], limit=1000)
        inv_data["valuation_layers_sampled"] = len(layers)
        inv_data["total_value_sampled"] = sum(layers.mapped("value"))
    if "stock.quant" in env:
        inv_data["quants_with_stock"] = env["stock.quant"].search_count([("quantity", ">", 0)])

    inv_account = by_code.get(KEY_ACCOUNTS["inventory"])
    cogs_account = by_code.get(KEY_ACCOUNTS["cogs"])
    area_ok("inventory", {
        "inventory_account": check_result(bool(inv_account), KEY_ACCOUNTS["inventory"]),
        "cogs_account": check_result(bool(cogs_account), KEY_ACCOUNTS["cogs"]),
        "stock_module": check_result(report["modules"].get("stock", {}).get("state") == "installed", report["modules"].get("stock")),
        "details": check_result(True, inv_data),
    })

    if report["modules"].get("stock", {}).get("state") != "installed":
        finding("medium", "inventory", "INV-01", "Módulo stock no instalado")

    # =============================================================================
    # 7. POS
    # =============================================================================
    pos_data = {"installed": report["modules"].get("point_of_sale", {}).get("state") == "installed"}
    if "pos.config" in env:
        configs = env["pos.config"].search([])
        pos_data["config_count"] = len(configs)
        pos_data["configs"] = [
            {
                "name": c.name,
                "journal": c.journal_id.code if c.journal_id else None,
                "invoice_journal": c.invoice_journal_id.code if c.invoice_journal_id else None,
                "warehouse": c.warehouse_id.name if c.warehouse_id else None,
                "payment_methods": [pm.name for pm in c.payment_method_ids],
            }
            for c in configs
        ]
    if "pos.session" in env:
        pos_data["open_sessions"] = env["pos.session"].search_count([("state", "!=", "closed")])
        pos_data["total_sessions"] = env["pos.session"].search_count([])
    if "pos.order" in env:
        pos_data["total_orders"] = env["pos.order"].search_count([])
        pos_data["invoiced_orders"] = env["pos.order"].search_count([("account_move", "!=", False)])

    area_ok("pos", {
        "pos_installed": check_result(pos_data["installed"], pos_data.get("config_count", 0)),
        "details": check_result(True, pos_data),
    })

    if pos_data["installed"] and pos_data.get("config_count", 0) == 0:
        finding("high", "pos", "POS-01", "POS instalado sin pos.config")
    if not pos_data["installed"]:
        finding("info", "pos", "POS-02", "point_of_sale no instalado")

    # =============================================================================
    # 8. Impuestos y DGII (solo lectura)
    # =============================================================================
    sale_tax = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=5)
    purchase_tax = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)], limit=5)

    ncf_field = "justech_do_ncf" in Move._fields
    no_ncf = out_inv.filtered(lambda m: ncf_field and not m.justech_do_ncf) if ncf_field else Move
    env.cr.execute("""
        SELECT justech_do_ncf, COUNT(*) c FROM account_move
        WHERE state='posted' AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
        AND company_id = %s
        GROUP BY justech_do_ncf HAVING COUNT(*) > 1
    """, (company.id,))
    dup_ncf = env.cr.fetchall()

    ncf_ranges = safe(
        lambda: [
            {
                "name": r.name,
                "prefix": r.document_type_id.prefix if r.document_type_id else None,
                "next": r.next_sequence,
                "end": r.sequence_end,
                "remaining": (r.sequence_end - r.next_sequence + 1) if r.sequence_end and r.next_sequence else None,
            }
            for r in env["justech.do.ncf.range"].search([("state", "=", "active"), ("company_id", "=", company.id)])
        ] if "justech.do.ncf.range" in env else [],
        [],
    )

    wh_summary = {"model_exists": "hellenia.payment.withholding.line" in env}
    if wh_summary["model_exists"]:
        WhLine = env["hellenia.payment.withholding.line"]
        wh_lines = WhLine.search([("company_id", "=", company.id)])
        wh_summary["lines"] = len(wh_lines)
        wh_summary["no_account"] = len(wh_lines.filtered(lambda w: w.amount and not w.account_id))
        wh_summary["no_gl"] = len(wh_lines.filtered(lambda w: w.amount and w.payment_id.state in ("paid", "in_process") and not w.move_line_id))

    period_code = date.today().strftime("%Y%m")
    dgii_counts = {}
    if "justech.do.dgii.period" in env:
        period_util = env["justech.do.dgii.period"]
        df, dt = period_util.period_bounds_from_code(period_code)
        dgii_counts["period"] = period_code
        dgii_counts["date_from"] = str(df)
        dgii_counts["date_to"] = str(dt)
        for rtype, move_types in (
            ("607_out", ("out_invoice", "out_refund")),
            ("606_in", ("in_invoice", "in_refund")),
            ("608_refund", ("out_refund", "in_refund")),
        ):
            dgii_counts[rtype] = Move.search_count([
                ("state", "=", "posted"),
                ("move_type", "in", move_types),
                ("date", ">=", df),
                ("date", "<=", dt),
                ("company_id", "=", company.id),
            ])

    area_ok("taxes_dgii", {
        "sale_itbis_18": check_result(bool(sale_tax), [t.name for t in sale_tax]),
        "purchase_itbis_18": check_result(bool(purchase_tax), [t.name for t in purchase_tax]),
        "ncf_duplicates": check_result(not dup_ncf, dup_ncf[:5]),
        "posted_out_invoices_without_ncf": check_result(len(no_ncf) == 0, len(no_ncf)),
        "active_ncf_ranges": check_result(True, ncf_ranges),
        "withholding_summary": check_result(wh_summary.get("no_account", 0) == 0, wh_summary),
        "dgii_move_counts_current_period": check_result(True, dgii_counts),
    })

    if dup_ncf:
        finding("critical", "taxes_dgii", "FISC-02", f"NCF duplicados: {dup_ncf[:5]}")
    if ncf_field and no_ncf:
        finding("medium", "taxes_dgii", "FISC-03", f"Facturas cliente posted sin NCF: {len(no_ncf)}")
    for r in ncf_ranges:
        rem = r.get("remaining")
        if rem is not None and rem < 100:
            finding("high", "taxes_dgii", "FISC-04", f"Rango NCF {r.get('prefix')} bajo: {rem} restantes", r)
    if wh_summary.get("no_account"):
        finding("critical", "taxes_dgii", "FISC-05", f"Retenciones sin cuenta: {wh_summary['no_account']}")

    # =============================================================================
    # 9. Bancos y caja
    # =============================================================================
    payments = Payment.search([
        ("state", "in", ("paid", "in_process", "posted")),
        ("company_id", "=", company.id),
    ])
    no_move = payments.filtered(lambda p: not p.move_id)
    bank_journals = journals.filtered(lambda j: j.type == "bank")
    cash_journals = journals.filtered(lambda j: j.type == "cash")

    env.cr.execute("""
        SELECT bk.name, b.acc_number
        FROM res_partner_bank b
        LEFT JOIN res_bank bk ON bk.id = b.bank_id
        WHERE b.partner_id = (SELECT partner_id FROM res_company WHERE id = %s)
    """, (company.id,))
    bank_accounts = [{"bank": r[0], "acc": r[1]} for r in env.cr.fetchall()]

    area_ok("banks_cash", {
        "posted_payments": check_result(True, len(payments)),
        "payments_without_move": check_result(not no_move, no_move.mapped("name")[:10] if no_move else []),
        "bank_journals": check_result(bool(bank_journals), [{"code": j.code, "name": j.name} for j in bank_journals]),
        "cash_journals": check_result(bool(cash_journals), [{"code": j.code, "name": j.name} for j in cash_journals]),
        "company_bank_accounts": check_result(True, bank_accounts),
    })

    if no_move:
        finding("critical", "banks_cash", "BNK-01", f"Pagos sin asiento: {no_move.mapped('name')[:5]}")
    if not cash_journals:
        finding("medium", "banks_cash", "BNK-02", "Sin diario tipo cash (CSH1 esperado)")

    # =============================================================================
    # 10. Reportes financieros (acceso modelos — no UI)
    # =============================================================================
    fin_reports = {}
    if "account.report" in env:
        fin_reports["account_report_count"] = env["account.report"].search_count([])
        fin_reports["sample_reports"] = [r.name for r in env["account.report"].search([], limit=10)]

    # Balance sheet equation
    bs_types = {
        "assets": ["asset_receivable", "asset_cash", "asset_current", "asset_non_current", "asset_prepayments", "asset_fixed"],
        "liabilities": ["liability_payable", "liability_credit_card", "liability_current", "liability_non_current"],
        "equity": ["equity", "equity_unaffected"],
    }
    balances = {}
    for label, types in bs_types.items():
        lines = AML.search([
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "in", types),
            ("company_id", "=", company.id),
        ])
        balances[label] = sum(lines.mapped("balance"))

    assets = balances.get("assets", 0)
    liab_eq = balances.get("liabilities", 0) + balances.get("equity", 0)

    area_ok("financial_reports", {
        "account_reports_module": check_result(report["modules"].get("account_reports", {}).get("state") == "installed", report["modules"].get("account_reports")),
        "reports_accessible": check_result(True, fin_reports),
        "balance_sheet_equation": check_result(abs(assets - liab_eq) < 1.0, f"A={assets:.2f} L+E={liab_eq:.2f}"),
    })

    if report["modules"].get("account_reports", {}).get("state") != "installed":
        finding("medium", "financial_reports", "RPT-01", "account_reports no instalado")

    # --- Reconciliation orphans (read-only) ---
    env.cr.execute("""
        SELECT COUNT(*) FROM account_partial_reconcile pr
        WHERE NOT EXISTS (SELECT 1 FROM account_move_line WHERE id = pr.debit_move_id)
           OR NOT EXISTS (SELECT 1 FROM account_move_line WHERE id = pr.credit_move_id)
    """)
    orphan_partial = env.cr.fetchone()[0]
    report["integrity"]["orphan_partials"] = orphan_partial
    if orphan_partial:
        finding("critical", "integrity", "INT-03", f"Conciliaciones huérfanas: {orphan_partial}")

    # --- Summary ---
    sev_counts = {k: len(v) for k, v in report["findings"].items()}
    report["summary"] = {
        "posted_moves": len(posted),
        "customer_invoices": len(out_inv),
        "vendor_bills": len(in_inv),
        "payments": len(payments),
        "finding_counts": sev_counts,
        "critical_count": sev_counts.get("critical", 0),
        "high_count": sev_counts.get("high", 0),
        "errors_count": len(report["errors"]),
        "dev_health": "error" if report["errors"] else "ok",
    }
    report["pass"] = report["ok"] and sev_counts.get("critical", 0) == 0

print("ACCOUNTING_TOTAL_AUDIT:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
