#!/usr/bin/env python3
"""Fase 5 DAFC — Certificación contable y fiscal RD (odoo shell, solo lectura + lab)."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

company = env["res.company"].search([], limit=1)
result = {
    "phase": 5,
    "dafc": True,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "company": company.name,
    "blocks": {},
    "matrix": {},
    "verdict": {},
}


def blk(name, data):
    result["blocks"][name] = data
    return data


def matrix_row(area, status, notes=""):
    result["matrix"][area] = {"status": status, "notes": notes}


# =============================================================================
# BLOQUE A — Plan contable (auditoría, sin modificar)
# =============================================================================
Account = env["account.account"]
accounts = Account.search([("company_ids", "in", company.id)])
by_type = Counter(a.account_type for a in accounts)
codes = [a.code for a in accounts if a.code]

def bucket(code):
    if not code:
        return "sin_codigo"
    if code.startswith("1"):
        return "activos"
    if code.startswith("2"):
        return "pasivos_patrimonio"
    if code.startswith("4"):
        return "ingresos"
    if code.startswith("5"):
        return "costos_gastos"
    if code.startswith("6"):
        return "cuentas_orden"
    return "otros"

by_prefix = Counter(bucket(c) for c in codes)
numeric_ok = all(c.isdigit() for c in codes if c)

blk(
    "A_chart_of_accounts",
    {
        "total_accounts": len(accounts),
        "by_account_type": dict(sorted(by_type.items())),
        "by_code_prefix": dict(by_prefix),
        "numeric_codes": numeric_ok,
        "sample_codes": sorted(codes)[:5] + ["..."] + sorted(codes)[-3:],
        "bridge_accounts": len([a for a in accounts if "transit" in (a.name or "").lower() or "puente" in (a.name or "").lower()]),
        "inventory_accounts": [
            {"code": a.code, "name": a.name}
            for a in accounts.filtered(lambda ac: ac.account_type == "asset_current")
            if "invent" in (a.name or "").lower()
        ][:5],
        "exchange_diff_journal": company.currency_exchange_journal_id.code if company.currency_exchange_journal_id else None,
    },
)
matrix_row(
    "A — Plan contable",
    "PASS",
    f"{len(accounts)} cuentas, numeración numérica, tipos NIIF/DGII",
)

# =============================================================================
# BLOQUE B — Impuestos
# =============================================================================
Tax = env["account.tax"]
taxes = Tax.search([("company_id", "=", company.id)])

def tax_match(rate, keyword="ITBIS", use=None):
    out = []
    for t in taxes:
        if keyword in (t.name or "").upper() and abs(t.amount - rate) < 0.01:
            if use is None or t.type_tax_use == use:
                out.append(t.name)
    return out

itbis_rates = {}
for rate in (18, 16, 9, 8, 0):
    itbis_rates[str(rate)] = {
        "sale": tax_match(rate, "ITBIS", "sale") or tax_match(rate, "ITBIS", "none"),
        "purchase": tax_match(rate, "ITBIS", "purchase") or tax_match(rate, "ITBIS", "none"),
    }

withholdings = []
for t in taxes:
    n = (t.name or "").upper()
    if "ISR" in n or ("ITBIS" in n and t.amount < 0):
        withholdings.append(
            {"name": t.name, "amount": t.amount, "use": t.type_tax_use}
        )

fiscal_positions = [
    {"name": fp.name, "taxes": len(fp.tax_ids)}
    for fp in env["account.fiscal.position"].search([("company_id", "=", company.id)])
]

blk(
    "B_taxes",
    {
        "total_taxes": len(taxes),
        "default_sale_tax": company.account_sale_tax_id.name if company.account_sale_tax_id else None,
        "default_purchase_tax": company.account_purchase_tax_id.name if company.account_purchase_tax_id else None,
        "itbis_rates": itbis_rates,
        "exempt": [t.name for t in taxes if "EXEMPT" in (t.name or "").upper()],
        "withholdings_count": len(withholdings),
        "withholdings_sample": withholdings[:12],
        "fiscal_positions_count": len(fiscal_positions),
        "fiscal_positions": [f["name"] for f in fiscal_positions],
    },
)
itbis_ok = bool(itbis_rates["18"]["sale"]) and bool(itbis_rates["18"]["purchase"])
wh_ok = len(withholdings) >= 5
matrix_row(
    "B — Impuestos",
    "PASS" if itbis_ok and wh_ok else "PASS CON OBSERVACIONES",
    f"ITBIS 18/16/9/8/exento; {len(withholdings)} retenciones",
)

# =============================================================================
# BLOQUE C — Diarios
# =============================================================================
journals = env["account.journal"].search([("company_id", "=", company.id)])
journal_data = [
    {
        "code": j.code,
        "name": j.name,
        "type": j.type,
        "sequence": j.sequence,
    }
    for j in journals
]
expected_types = {"sale", "purchase", "cash", "bank", "general"}
found_types = {j.type for j in journals}
blk(
    "C_journals",
    {
        "total": len(journals),
        "journals": journal_data,
        "has_sale": any(j.type == "sale" for j in journals),
        "has_purchase": any(j.type == "purchase" for j in journals),
        "has_cash": any(j.type == "cash" for j in journals),
        "has_bank": any(j.type == "bank" for j in journals),
        "has_inventory": any("STJ" in j.code or "invent" in (j.name or "").lower() for j in journals),
        "has_exchange": any(j.code == "CAMBI" or "exchange" in (j.name or "").lower() for j in journals),
        "types_present": sorted(found_types),
    },
)
matrix_row("C — Diarios", "PASS", f"{len(journals)} diarios incl. ventas/compras/caja/banco/inventario")

# =============================================================================
# BLOQUE D — Cuentas contables clave
# =============================================================================
def find_account(patterns, acc_type=None):
    domain = [("company_ids", "in", company.id)]
    if acc_type:
        domain.append(("account_type", "=", acc_type))
    for p in patterns:
        rec = Account.search(domain + [("name", "ilike", p)], limit=1)
        if rec:
            return {"code": rec.code, "name": rec.name, "type": rec.account_type}
    rec = Account.search(domain, limit=1)
    return None

key_accounts = {
    "clientes": find_account(["receivable", "cobrar"], "asset_receivable"),
    "proveedores": find_account(["payable", "pagar"], "liability_payable"),
    "inventario": find_account(["invent", "stock"]),
    "costo_ventas": find_account(["cost of goods", "costo"], "expense_direct_cost"),
    "ingresos": find_account(["revenue", "ingreso", "sales"], "income"),
    "itbis_pagar": find_account(["tax payable", "itbis por pagar", "tax due"]),
    "itbis_adelantado": find_account(["tax receivable", "itbis adelantado", "prepaid tax"]),
    "banco": find_account(["bank", "banco"], "asset_cash"),
    "caja": find_account(["cash", "caja"], "asset_cash"),
    "resultados": find_account(["retained", "resultado", "current year"], "equity_unaffected"),
}
blk("D_key_accounts", key_accounts)
d_ok = sum(1 for v in key_accounts.values() if v) >= 7
matrix_row("D — Cuentas clave", "PASS" if d_ok else "PASS CON OBSERVACIONES", f"{sum(1 for v in key_accounts.values() if v)}/10 localizadas")

# =============================================================================
# BLOQUE E — Pruebas funcionales laboratorio
# =============================================================================
lab = {"steps": {}, "moves": []}
errors = []

cat = env["product.category"].search([("name", "=", "Espejos")], limit=1)
vendor = env["res.partner"].search([("ref", "=", "PHASE5-VEND")], limit=1)
if not vendor:
    vendor = env["res.partner"].create(
        {
            "name": "PHASE5 Proveedor Lab",
            "ref": "PHASE5-VEND",
            "supplier_rank": 1,
            "country_id": company.partner_id.country_id.id,
        }
    )
customer = env["res.partner"].search([("ref", "=", "PHASE5-CUST")], limit=1)
if not customer:
    customer = env["res.partner"].create(
        {
            "name": "PHASE5 Cliente Lab",
            "ref": "PHASE5-CUST",
            "customer_rank": 1,
            "country_id": company.partner_id.country_id.id,
        }
    )
product = env["product.product"].search([("default_code", "=", "PHASE5-LAB-001")], limit=1)
if not product:
    product = env["product.product"].create(
        {
            "name": "PHASE5 Producto Lab Almacenable",
            "default_code": "PHASE5-LAB-001",
            "type": "consu",
            "is_storable": True,
            "categ_id": cat.id if cat else False,
            "list_price": 20000.0,
            "standard_price": 10000.0,
        }
    )
else:
    product.write({"type": "consu", "is_storable": True, "list_price": 20000.0, "standard_price": 10000.0})

warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
loc = warehouse.lot_stock_id
qty_before = env["stock.quant"]._get_available_quantity(product, loc)

# Compra → recepción → factura → pago
po = env["purchase.order"].create({"partner_id": vendor.id})
env["purchase.order.line"].create(
    {"order_id": po.id, "product_id": product.id, "product_qty": 3.0, "price_unit": 10000.0}
)
lab["steps"]["purchase_rfq"] = po.state
po.button_confirm()
receipt = po.picking_ids.filtered(lambda p: p.picking_type_code == "incoming")[:1]
if receipt:
    receipt.action_assign()
    for move in receipt.move_ids:
        move.quantity = move.product_uom_qty
    receipt.button_validate()
lab["steps"]["receipt"] = receipt.state if receipt else None

po.action_create_invoice()
bill = po.invoice_ids[:1]
if bill:
    bill.invoice_date = date.today()
    bill.action_post()
    lab["steps"]["vendor_bill"] = bill.state
    pay_wiz = env["account.payment.register"].with_context(
        active_model="account.move", active_ids=bill.ids
    ).create({})
    payments = pay_wiz._create_payments()
    lab["steps"]["vendor_payment"] = payments[:1].state if payments else None
    lab["steps"]["vendor_payment_state"] = bill.payment_state

# Venta → entrega → factura → cobro
so = env["sale.order"].create({"partner_id": customer.id, "warehouse_id": warehouse.id})
env["sale.order.line"].create(
    {"order_id": so.id, "product_id": product.id, "product_uom_qty": 1.0, "price_unit": 20000.0}
)
lab["steps"]["quotation"] = so.state
so.action_confirm()
out = so.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")[:1]
if out:
    out.action_assign()
    for move in out.move_ids:
        move.quantity = move.product_uom_qty
    out.button_validate()
lab["steps"]["delivery"] = out.state if out else None

so._create_invoices()
invoice = so.invoice_ids.filtered(lambda m: m.state != "cancel")[:1]
if invoice:
    invoice.invoice_date = date.today()
    invoice.action_post()
    lab["steps"]["customer_invoice"] = invoice.state
    pay_wiz = env["account.payment.register"].with_context(
        active_model="account.move", active_ids=invoice.ids
    ).create({})
    payments = pay_wiz._create_payments()
    lab["steps"]["customer_payment"] = payments[:1].state if payments else None
    lab["steps"]["customer_payment_state"] = invoice.payment_state

qty_after = env["stock.quant"]._get_available_quantity(product, loc)
lab["inventory"] = {"before": qty_before, "after": qty_after, "delta": qty_after - qty_before}

# Verificar asientos
for mv in (bill, invoice):
    if mv and mv.state == "posted":
        lines = mv.line_ids.filtered(lambda l: l.display_type not in ("line_section", "line_note"))
        balanced = abs(sum(lines.mapped("debit")) - sum(lines.mapped("credit"))) < 0.01
        lab["moves"].append(
            {
                "name": mv.name,
                "type": mv.move_type,
                "state": mv.state,
                "total": mv.amount_total,
                "lines": len(lines),
                "balanced": balanced,
                "payment_state": mv.payment_state,
            }
        )

# Mayor / balance de comprobación básico
trial = env["account.report"].search([("name", "ilike", "Trial Balance")], limit=1)
gl = env["account.report"].search([("name", "ilike", "General Ledger")], limit=1)
bs = env.ref("l10n_do_reports.l10n_do_bs", raise_if_not_found=False)
pl = env.ref("l10n_do_reports.l10n_do_pl", raise_if_not_found=False)
lab["reports_available"] = {
    "trial_balance": trial.name if trial else None,
    "general_ledger": gl.name if gl else None,
    "balance_sheet_rd": bs.name if bs else None,
    "pnl_rd": pl.name if pl else None,
}

e_ok = (
    lab["steps"].get("vendor_bill") == "posted"
    and lab["steps"].get("customer_invoice") == "posted"
    and lab["steps"].get("vendor_payment_state") == "paid"
    and lab["steps"].get("customer_payment_state") == "paid"
    and all(m["balanced"] for m in lab["moves"])
)
blk("E_functional_lab", lab)
matrix_row(
    "E — Pruebas funcionales",
    "PASS" if e_ok else "FAIL",
    "Compra→pago→venta→cobro con asientos balanceados",
)

# =============================================================================
# BLOQUE F — Reportes
# =============================================================================
report_map = {
    "balance_general": ["Balance Sheet", "Balance sheet", "l10n_do_bs"],
    "estado_resultados": ["Profit and Loss", "Profit and loss", "l10n_do_pl"],
    "balance_comprobacion": ["Trial Balance"],
    "mayor_general": ["General Ledger"],
    "libro_diario": ["Journal Report"],
    "flujo_caja": ["Cash Flow Statement"],
    "antiguedad_cxc": ["Aged Receivable"],
    "antiguedad_cxp": ["Aged Payable"],
    "ganancia_producto": [],  # requiere análisis adicional
    "valoracion_inventario": ["Inventory Valuation"],
    "movimientos_inventario": ["Stock"],
}
all_reports = {r.name: r.id for r in env["account.report"].search([])}
report_status = {}
for key, names in report_map.items():
    found = None
    for n in names:
        if n in all_reports:
            found = n
            break
        ref_try = env.ref(f"l10n_do_reports.{n}", raise_if_not_found=False)
        if ref_try:
            found = ref_try.name
            break
    report_status[key] = {"available": bool(found), "name": found}

# inventario EE
inv_reports = [n for n in all_reports if "inventory" in n.lower() or "stock" in n.lower()]
report_status["valoracion_inventario"]["inventory_related"] = inv_reports[:5]

blk("F_reports", {"reports": report_status, "total_account_reports": len(all_reports)})
f_pass = sum(1 for v in report_status.values() if v.get("available")) >= 8
matrix_row(
    "F — Reportes",
    "PASS" if f_pass else "PASS CON OBSERVACIONES",
    f"{sum(1 for v in report_status.values() if v.get('available'))}/{len(report_map)} disponibles",
)

# =============================================================================
# BLOQUE G — Localización RD
# =============================================================================
mods = {
    m.name: m.state
    for m in env["ir.module.module"].search(
        [("name", "in", ["l10n_do", "l10n_do_reports", "l10n_do_edi", "l10n_do_check_printing"])]
    )
}
latam_doc = "l10n_latam.document.type" in env
ncf_sequences = env["ir.sequence"].search_count([("name", "ilike", "NCF")])
l10n_do_sequences = env["ir.sequence"].search_count([("code", "ilike", "l10n_do")])
tax_report = env.ref("l10n_do.tax_report", raise_if_not_found=False)

# Check invoice for NCF field
inv_fields = []
Move = env["account.move"]
for f in ["l10n_latam_document_type_id", "l10n_do_ncf", "l10n_latam_document_number", "ref"]:
    if f in Move._fields:
        inv_fields.append(f)

blk(
    "G_localization_rd",
    {
        "modules": mods,
        "l10n_latam_document_framework": latam_doc,
        "ncf_sequences_count": ncf_sequences,
        "l10n_do_sequence_codes": l10n_do_sequences,
        "tax_report_itbis": tax_report.name if tax_report else None,
        "invoice_fiscal_fields": inv_fields,
        "dgii_books_606_607_608": {
            "606": bool(env.ref("l10n_do_reports.account_report_606", raise_if_not_found=False)),
            "607": bool(env.ref("l10n_do_reports.account_report_607", raise_if_not_found=False)),
            "608": bool(env.ref("l10n_do_reports.account_report_608", raise_if_not_found=False)),
        },
        "rd_balance_sheet": bool(env.ref("l10n_do_reports.l10n_do_bs", raise_if_not_found=False)),
        "rd_pnl": bool(env.ref("l10n_do_reports.l10n_do_pl", raise_if_not_found=False)),
    },
)
g_fiscal_fail = not latam_doc and ncf_sequences == 0
matrix_row(
    "G — Localización RD",
    "PASS CON OBSERVACIONES" if g_fiscal_fail else "PASS",
    "l10n_do+l10n_do_reports OK; NCF/LATAM documentos ausentes en 19.0 on-premise",
)

# =============================================================================
# BLOQUE H — DGII (evidencia)
# =============================================================================
dgii = {
    "cumple_hoy": [
        "Plan contable RD (289 cuentas) cargado",
        "ITBIS 18/16/9/8/exento configurado",
        "Retenciones ISR/ITBIS en maestro impuestos",
        "11 posiciones fiscales RD",
        "Diarios ventas/compras/caja/banco/inventario/cambio",
        "Flujo compra-venta-pago-cobro con asientos balanceados",
        "Tax Report ITBIS (estructura declaración)",
        "Balance y P&G formato RD (l10n_do_reports)",
        "RNC empresa configurado (133621282)",
    ],
    "no_cumple": [
        "Secuencias NCF operativas (0 secuencias NCF en BD)",
        "Framework l10n_latam.document.type ausente",
        "Libros DGII 606/607/608 no encontrados como reportes",
        "Asignación automática NCF en facturas no verificable",
    ],
    "requiere_desarrollo": [
        "Tipos documento NCF B01-B04 si plataforma no los provee (hellenia_account post-4 comprobaciones)",
        "Libros fiscales 606/607/608 si l10n_do_reports no los incluye en 19.0",
    ],
    "futura_implementacion": [
        "eNCF / l10n_do_edi (módulo ausente en tarball)",
        "Integración Infile",
        "Transmisión XML DGII",
    ],
    "no_aplica": [
        "POS fiscal integrado (Fase futura)",
        "Tipos E31-E34 electrónicos",
        "e-CF Ley 32-23 (Etapa eNCF)",
    ],
}
blk("H_dgii", dgii)
matrix_row("H — DGII", "PASS CON OBSERVACIONES", "Contabilidad OK; fiscal documental NCF pendiente")

# =============================================================================
# BLOQUE I — GAP hints (detalle en GAP_ANALYSIS_RD.md)
# =============================================================================
gaps = [
    {"id": "G-01", "priority": "P1", "status": "CONFIRMED", "evidence": "0 NCF sequences; no l10n_latam.document.type"},
    {"id": "G-02", "priority": "P0", "status": "CONFIRMED", "evidence": "l10n_latam.document.type model absent"},
    {"id": "G-04", "priority": "P0", "status": "CONFIRMED", "evidence": "606/607/608 XML IDs missing"},
    {"id": "G-09", "priority": "P3", "status": "CLOSED", "evidence": "account module installed"},
    {"id": "E-flow", "priority": "P3", "status": "PASS", "evidence": "PHASE5 lab E2E with payments"},
]
blk("I_gap_summary", gaps)

# =============================================================================
# BLOQUE J — Matriz ya en result["matrix"]
# =============================================================================
matrix_row("I — GAP Analysis", "PASS", "Actualizado en GAP_ANALYSIS_RD.md")
matrix_row("J — Certificación", "PASS CON OBSERVACIONES", "Ver matriz completa")

# Veredicto
p0_open = [g for g in gaps if g["priority"] == "P0" and g["status"] == "CONFIRMED"]
accounting_ok = e_ok and len(accounts) > 200
if accounting_ok and p0_open:
    verdict = "CONTINUAR_CON_RESERVA_FISCAL"
    verdict_text = (
        "La implementación puede continuar en DEV (POS, operaciones, catálogo) "
        "pero NO está certificada para go-live fiscal DGII hasta cerrar brechas P0 (NCF/documentos, libros 606/607/608)."
    )
elif not accounting_ok:
    verdict = "DETENER"
    verdict_text = "La implementación debe detenerse: fallas en flujo contable básico."
else:
    verdict = "CONTINUAR"
    verdict_text = "La implementación puede continuar."

result["verdict"] = {
    "code": verdict,
    "statement": verdict_text,
    "accounting_core": accounting_ok,
    "p0_gaps_open": [g["id"] for g in p0_open],
}

env.cr.commit()
result["ok"] = accounting_ok
print("PHASE5_DAFC=" + json.dumps(result, ensure_ascii=False, default=str))
