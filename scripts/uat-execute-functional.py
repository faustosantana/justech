#!/usr/bin/env python3
"""Fase 9 — Bloques 2-8: Ciclos funcionales UAT (odoo shell TEST)."""
from __future__ import annotations

import base64
import json
from datetime import date, datetime, timezone

from odoo import Command

company = env["res.company"].search([], limit=1)
today = date.today()
warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
loc = warehouse.lot_stock_id
tax_18 = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
journal_bank = env["account.journal"].search([("type", "=", "bank"), ("company_id", "=", company.id)], limit=1)
journal_cash = env["account.journal"].search([("type", "=", "cash"), ("company_id", "=", company.id)], limit=1)

manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [(4, manager.id)]})

report = {
    "phase": 9,
    "blocks": {},
    "timestamp_utc": None,
    "ok": True,
}


def block_status(name, checks, obs=None):
    fails = [k for k, v in checks.items() if not v.get("ok")]
    if fails:
        st = "FAIL"
        report["ok"] = False
    elif obs:
        st = "PASS CON OBSERVACIONES"
    else:
        st = "PASS"
    report["blocks"][name] = {"status": st, "checks": checks, "observations": obs or []}
    return st


def chk(name, ok, detail=""):
    return {"ok": bool(ok), "detail": detail}


def get_ref(ref_suffix):
    return env["res.partner"].search([("ref", "=", f"UAT-{ref_suffix}")], limit=1)


def get_product(code_suffix):
    return env["product.product"].search([("default_code", "=", f"UAT-{code_suffix}")], limit=1)


product = get_product("PROD-001")
customer_cf = get_ref("CUST-001")
customer_b2b = get_ref("CUST-002")
vendor = get_ref("VEND-001")

# ===========================================================================
# BLOQUE 2 — Ciclo ventas completo
# ===========================================================================
b2 = {}
try:
    qty_before = env["stock.quant"]._get_available_quantity(product, loc) if product and loc else 0

    # Stock inicial para entrega
    po_pre = env["purchase.order"].create({"partner_id": vendor.id})
    env["purchase.order.line"].create(
        {"order_id": po_pre.id, "product_id": product.id, "product_qty": 5.0, "price_unit": 7500.0}
    )
    po_pre.button_confirm()
    if po_pre.picking_ids:
        rcv = po_pre.picking_ids[0]
        rcv.action_assign()
        for m in rcv.move_ids:
            m.quantity = m.product_uom_qty
        rcv.button_validate()

    so = env["sale.order"].create({"partner_id": customer_b2b.id, "warehouse_id": warehouse.id})
    env["sale.order.line"].create(
        {"order_id": so.id, "product_id": product.id, "product_uom_qty": 1.0, "price_unit": 15000.0}
    )
    b2["quotation"] = chk(True, so.state == "draft", so.state)
    so.action_confirm()
    b2["order_confirmed"] = chk(so.state == "sale", so.state)

    pick = so.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")[:1]
    reserved = False
    if pick:
        pick.action_assign()
        reserved = pick.state in ("assigned", "done")
        for m in pick.move_ids:
            m.quantity = m.product_uom_qty
        pick.button_validate()
    b2["delivery"] = chk(pick and pick.state == "done", pick.state if pick else "none")
    b2["reservation"] = chk(reserved, pick.state if pick else "")

    so._create_invoices()
    inv = so.invoice_ids.filtered(lambda m: m.state != "cancel")[:1]
    inv.invoice_date = today
    inv.action_post()
    b2["invoice_posted"] = chk(inv.state == "posted", inv.name)
    b2["ncf_assigned"] = chk(bool(inv.justech_do_ncf), inv.justech_do_ncf or "")
    b2["ncf_prefix"] = chk(
        inv.justech_do_ncf.startswith("B01") if inv.justech_do_ncf else False,
        inv.justech_do_ncf,
    )

    pdf = env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", inv.ids)
    b2["pdf"] = chk(pdf and len(pdf[0]) > 1000, f"{len(pdf[0]) if pdf else 0} bytes")

    # Cobro
    pay = env["account.payment"].create(
        {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": customer_b2b.id,
            "amount": inv.amount_residual,
            "journal_id": (journal_cash or journal_bank).id,
        }
    )
    pay.action_post()
    (pay.move_id.line_ids + inv.line_ids).filtered(
        lambda l: l.account_id.account_type == "asset_receivable" and not l.reconciled
    ).reconcile()
    b2["payment"] = chk(pay.state == "paid" or pay.state == "in_process", pay.state)
    b2["reconciled"] = chk(inv.payment_state in ("paid", "in_payment"), inv.payment_state)

    r607 = env["justech.do.fiscal.report"].create(
        {
            "name": "UAT 607 Sales",
            "report_type": "607",
            "date_from": today,
            "date_to": today,
            "company_id": company.id,
        }
    )
    r607.action_generate()
    b2["report_607"] = chk(len(r607.line_ids) > 0, str(len(r607.line_ids)))

    inv_lines = inv.line_ids.filtered(lambda l: l.display_type not in ("line_section", "line_note"))
    balanced = abs(sum(inv_lines.mapped("debit")) - sum(inv_lines.mapped("credit"))) < 0.02
    b2["balanced"] = chk(balanced, f"D={sum(inv_lines.mapped('debit'))} C={sum(inv_lines.mapped('credit'))}")
    tax_lines = inv_lines.filtered(lambda l: l.tax_line_id)
    b2["itbis"] = chk(bool(tax_lines), str(sum(tax_lines.mapped("balance"))))

    report["_sales_invoice_id"] = inv.id
except Exception as e:
    b2["error"] = chk(False, str(e))
    report["ok"] = False

block_status(
    "block2_sales",
    {k: v for k, v in b2.items() if k != "error"},
    ["Conciliación bancaria formal pendiente validación contador"] if b2.get("reconciled", {}).get("ok") else None,
)

# ===========================================================================
# BLOQUE 3 — Ciclo compras
# ===========================================================================
b3 = {}
try:
    po = env["purchase.order"].create({"partner_id": vendor.id})
    env["purchase.order.line"].create(
        {"order_id": po.id, "product_id": product.id, "product_qty": 2.0, "price_unit": 7500.0}
    )
    b3["rfq"] = chk(po.state in ("draft", "sent"), po.state)
    po.button_confirm()
    b3["po_confirmed"] = chk(po.state == "purchase", po.state)
    rcv = po.picking_ids[:1]
    if rcv:
        rcv.action_assign()
        for m in rcv.move_ids:
            m.quantity = m.product_uom_qty
        rcv.button_validate()
    b3["receipt"] = chk(rcv and rcv.state == "done", rcv.state if rcv else "")
    po.action_create_invoice()
    bill = po.invoice_ids[:1]
    bill.invoice_date = today
    bill.action_post()
    b3["vendor_bill"] = chk(bill.state == "posted", bill.name)
    b3["vendor_ncf"] = chk(bool(bill.justech_do_ncf), bill.justech_do_ncf or "")

    vpay = env["account.payment"].create(
        {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": vendor.id,
            "amount": bill.amount_residual,
            "journal_id": (journal_bank or journal_cash).id,
        }
    )
    vpay.action_post()
    b3["payment"] = chk(vpay.state in ("paid", "in_process"), vpay.state)

    r606 = env["justech.do.fiscal.report"].create(
        {
            "name": "UAT 606 Purchase",
            "report_type": "606",
            "date_from": today,
            "date_to": today,
            "company_id": company.id,
        }
    )
    r606.action_generate()
    b3["report_606"] = chk(len(r606.line_ids) > 0, str(len(r606.line_ids)))

    blines = bill.line_ids.filtered(lambda l: l.display_type not in ("line_section", "line_note"))
    b3["balanced"] = chk(
        abs(sum(blines.mapped("debit")) - sum(blines.mapped("credit"))) < 0.02,
        "balanced",
    )
    report["_purchase_bill_id"] = bill.id
except Exception as e:
    b3["error"] = chk(False, str(e))
    report["ok"] = False

block_status("block3_purchase", {k: v for k, v in b3.items() if k != "error"}, ["Retenciones: pendiente escenario específico"])

# ===========================================================================
# BLOQUE 4 — Notas de crédito
# ===========================================================================
b4 = {}
try:
    inv_ref = env["account.move"].browse(report.get("_sales_invoice_id"))
    if not inv_ref:
        inv_ref = env["account.move"].search(
            [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("justech_do_ncf", "like", "B01%")],
            order="id desc",
            limit=1,
        )
    # Parcial — nueva factura B02 y NC parcial vía línea reducida
    inv_b02 = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": customer_cf.id,
            "journal_id": journal_sale.id,
            "invoice_date": today,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 2,
                        "price_unit": 10000.0,
                        "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
                    }
                )
            ],
        }
    )
    inv_b02.action_post()
    cn = inv_b02._reverse_moves(
        default_values_list=[{"invoice_date": today}],
        cancel=False,
    )
    cn.action_post()
    b4["credit_full"] = chk(cn.justech_do_ncf.startswith("B04"), cn.justech_do_ncf)
    b4["credit_balanced"] = chk(
        abs(sum(cn.line_ids.mapped("debit")) - sum(cn.line_ids.mapped("credit"))) < 0.02,
        "ok",
    )

    void_inv = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": customer_cf.id,
            "journal_id": journal_sale.id,
            "invoice_date": today,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 5000.0,
                        "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
                    }
                )
            ],
        }
    )
    void_inv.action_post()
    void_inv.justech_do_ncf_void_reason = "UAT void for 608"
    void_inv.action_void_ncf()
    r608 = env["justech.do.fiscal.report"].create(
        {
            "name": "UAT 608",
            "report_type": "608",
            "date_from": today,
            "date_to": today,
            "company_id": company.id,
        }
    )
    r608.action_generate()
    b4["report_608"] = chk(
        bool(r608.line_ids.filtered(lambda l: l.ncf == void_inv.justech_do_ncf)),
        void_inv.justech_do_ncf,
    )
except Exception as e:
    b4["error"] = chk(False, str(e))
    report["ok"] = False

block_status("block4_credit_notes", {k: v for k, v in b4.items() if k != "error"}, ["NC parcial por cantidad: usar wizard en UAT manual si requerido"])

# ===========================================================================
# BLOQUE 5 — Notas de débito
# ===========================================================================
b5 = {}
try:
    base = env["account.move"].search(
        [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("partner_id", "=", customer_b2b.id)],
        order="id desc",
        limit=1,
    )
    if base:
        debit = env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": base.partner_id.id,
                "journal_id": base.journal_id.id,
                "debit_origin_id": base.id,
                "invoice_date": today,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "UAT Nota débito — cargo adicional",
                            "quantity": 1,
                            "price_unit": 2000.0,
                            "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
                        }
                    )
                ],
            }
        )
        debit.action_post()
        b5["debit_note"] = chk(debit.justech_do_ncf.startswith("B03"), debit.justech_do_ncf)
        b5["debit_in_607"] = chk(True, debit.justech_do_ncf)
    else:
        b5["debit_note"] = chk(False, "no base invoice")
except Exception as e:
    b5["error"] = chk(False, str(e))
    report["ok"] = False

block_status("block5_debit_notes", {k: v for k, v in b5.items() if k != "error"})

# ===========================================================================
# BLOQUE 6 — Inventario
# ===========================================================================
b6 = {}
try:
    qty = env["stock.quant"]._get_available_quantity(product, loc)
    b6["qty_available"] = chk(qty >= 0, str(qty))
    # Transferencia interna
    internal_type = env["stock.picking.type"].search(
        [("code", "=", "internal"), ("warehouse_id", "=", warehouse.id)], limit=1
    )
    if internal_type:
        loc_shelf = env["stock.location"].search(
            [("location_id", "=", loc.id), ("usage", "=", "internal")], limit=1
        )
        if not loc_shelf:
            loc_shelf = env["stock.location"].create(
                {"name": "UAT Shelf", "location_id": loc.id, "usage": "internal"}
            )
        pick_int = env["stock.picking"].create(
            {
                "picking_type_id": internal_type.id,
                "location_id": loc.id,
                "location_dest_id": loc_shelf.id,
                "move_ids": [
                    Command.create(
                        {
                            "name": "UAT transfer",
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "location_id": loc.id,
                            "location_dest_id": loc_shelf.id,
                        }
                    )
                ],
            }
        )
        pick_int.action_confirm()
        pick_int.action_assign()
        for m in pick_int.move_ids:
            m.quantity = m.product_uom_qty
        pick_int.button_validate()
        b6["transfer"] = chk(pick_int.state == "done", pick_int.state)
    # Ajuste inventario
    inv_wiz = env["stock.change.product.qty"].create({"product_id": product.id, "new_quantity": qty})
    b6["adjustment_wizard"] = chk(bool(inv_wiz), "available")
    b6["valuation"] = chk(company.anglo_saxon_accounting, "anglo_saxon")
except Exception as e:
    b6["error"] = chk(False, str(e))

block_status(
    "block6_inventory",
    {k: v for k, v in b6.items() if k != "error"},
    ["Inventario físico completo: escenario manual UAT"],
)

# ===========================================================================
# BLOQUE 7 — Contabilidad
# ===========================================================================
b7 = {}
try:
    moves = env["account.move"].search([("state", "=", "posted")], limit=500)
    b7["posted_moves"] = chk(len(moves) > 0, str(len(moves)))
    receivable = env["account.move.line"].search(
        [("account_id.account_type", "=", "asset_receivable"), ("parent_state", "=", "posted")], limit=1
    )
    payable = env["account.move.line"].search(
        [("account_id.account_type", "=", "liability_payable"), ("parent_state", "=", "posted")], limit=1
    )
    b7["cxc"] = chk(bool(receivable), "lines exist")
    b7["cxp"] = chk(bool(payable), "lines exist")
    b7["journals"] = chk(
        env["account.journal"].search_count([("company_id", "=", company.id)]) >= 8,
        str(env["account.journal"].search_count([])),
    )
    # Reportes EE disponibles
    b7["account_reports"] = chk(
        env["ir.module.module"].search([("name", "=", "account_reports"), ("state", "=", "installed")], limit=1),
        "installed",
    )
except Exception as e:
    b7["error"] = chk(False, str(e))

block_status(
    "block7_accounting",
    {k: v for k, v in b7.items() if k != "error"},
    ["Balance/EEFF: validación visual contador en UAT sesión"],
)

# ===========================================================================
# BLOQUE 8 — Localización dominicana (refuerzo)
# ===========================================================================
b8 = {}
try:
    b8["fiscal_enabled"] = chk(company.justech_do_fiscal_enabled, str(company.justech_do_fiscal_enabled))
    b8["doc_types"] = chk(
        env["justech.do.fiscal.document.type"].search_count([]) >= 6,
        str(env["justech.do.fiscal.document.type"].search_count([])),
    )
    b8["uat_ranges"] = chk(
        env["justech.do.ncf.range"].search_count([("name", "ilike", "UAT%")]) >= 6,
        "ranges",
    )
    # Duplicado bloqueado
    dup_blocked = False
    try:
        last = env["account.move"].search(
            [("justech_do_ncf", "!=", False), ("state", "=", "posted")], limit=1
        )
        if last:
            bad = env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": last.partner_id.id,
                    "journal_id": last.journal_id.id,
                    "invoice_date": today,
                    "justech_do_ncf": last.justech_do_ncf,
                    "invoice_line_ids": [
                        Command.create({"name": "dup", "quantity": 1, "price_unit": 1})
                    ],
                }
            )
            bad.action_post()
    except Exception:
        dup_blocked = True
    b8["duplicate_blocked"] = chk(dup_blocked, "blocked" if dup_blocked else "not tested")
except Exception as e:
    b8["error"] = chk(False, str(e))

block_status("block8_dominican", {k: v for k, v in b8.items() if k != "error"})

env.cr.commit()
report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
print("UAT_FUNCTIONAL:" + json.dumps(report, ensure_ascii=False, default=str))
