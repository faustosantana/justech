# -*- coding: utf-8 -*-
"""Fase 29D — Validación hook NCF en account.move._post() (solo hellenia_test)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from odoo import Command, fields

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE = Path("/tmp/phase29d-pos-ncf-post-hook-test")
if Path("/workspace/evidence").exists():
    EVIDENCE = Path("/workspace/evidence/phase29d-pos-ncf-post-hook-test")
EVIDENCE.mkdir(parents=True, exist_ok=True)

POS_CONFIG_NAME = "Punto de Venta Hellenia"
PRODUCT_CODE = "P29B-POS-ITEM"
PARTNER_CF_REF = "P29B-CF"
PARTNER_RNC_REF = "P29B-RNC"
RUN_ID = datetime.now(timezone.utc).strftime("%H%M%S")

report = {
    "phase": "29D-ncf-post-hook-validation",
    "database": DB,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "module_version": env["ir.module.module"].search(
        [("name", "=", "justech_l10n_do_ncf")], limit=1
    ).latest_version,
    "ok": True,
    "tests": [],
    "errors": [],
}


def record(name, passed, **detail):
    report["tests"].append({"name": name, "pass": passed, **detail})
    if not passed:
        report["ok"] = False


def fail(msg):
    report["errors"].append(msg)
    _save()
    raise SystemExit(msg)


def _save():
    (EVIDENCE / "validation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )


company = env.company
admin = env.ref("base.user_admin")
fiscal_mgr = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager")
if fiscal_mgr not in admin.group_ids:
    admin.write({"group_ids": [Command.link(fiscal_mgr.id)]})
env.cr.commit()

e = env(user=admin)
tax = e["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)],
    limit=1,
)
journal_inv = e["account.journal"].search(
    [("code", "=", "INV"), ("company_id", "=", company.id)], limit=1
)
product = e["product.product"].search([("default_code", "=", PRODUCT_CODE)], limit=1)
partner_cf = e["res.partner"].search([("ref", "=", PARTNER_CF_REF)], limit=1)
partner_rnc = e["res.partner"].search([("ref", "=", PARTNER_RNC_REF)], limit=1)
doc_b02 = e.ref("justech_l10n_do_base.doc_type_b02")
doc_b01 = e.ref("justech_l10n_do_base.doc_type_b01")

if not all([tax, journal_inv, product, partner_cf, partner_rnc]):
    fail("Faltan datos base (producto, partners, diario INV). Ejecutar 29B setup primero.")


def sync_ncf_range_next(doc_type, journal):
    """Alinea next_sequence con consumos/NCF dentro del rango (solo TEST)."""
    rng = e["justech.do.ncf.range"].search(
        [
            ("state", "in", ("active", "depleted")),
            ("document_type_id", "=", doc_type.id),
            ("journal_ids", "in", journal.id),
        ],
        order="date_to desc",
        limit=1,
    )
    if not rng:
        return rng
    lo, hi = rng.sequence_start, rng.sequence_end
    max_seq = lo - 1
    for c in rng.consumption_ids:
        if lo <= c.sequence_number <= hi:
            max_seq = max(max_seq, c.sequence_number)
    moves = e["account.move"].search(
        [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("journal_id", "=", journal.id),
            ("justech_do_ncf", "like", f"{doc_type.prefix}%"),
        ]
    )
    for move in moves:
        try:
            p, seq = doc_type.parse_ncf(move.justech_do_ncf)
        except Exception:
            continue
        if p == doc_type.prefix and lo <= seq <= hi:
            max_seq = max(max_seq, seq)
    new_next = min(max(max_seq + 1, lo), hi + 1)
    updates = {}
    if new_next != rng.next_sequence:
        updates["next_sequence"] = new_next
    if new_next <= hi and rng.state == "depleted":
        updates["state"] = "active"
    if updates:
        rng.sudo().write(updates)
        env.cr.commit()
    return rng


sync_ncf_range_next(doc_b02, journal_inv)
sync_ncf_range_next(doc_b01, journal_inv)


def invoice_vals(partner, doc_type=None, ncf_manual=None):
    vals = {
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "journal_id": journal_inv.id,
        "invoice_date": date.today(),
        "invoice_line_ids": [
            Command.create(
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "price_unit": 1000.0,
                    "tax_ids": [Command.set(tax.ids)],
                }
            )
        ],
    }
    if doc_type:
        vals["justech_do_document_type_id"] = doc_type.id
    if ncf_manual:
        vals["justech_do_ncf"] = ncf_manual
    return vals


# 1 — Factura manual B02
try:
    m = e["account.move"].create(invoice_vals(partner_cf, doc_b02))
    assert m.state == "draft" and not m.justech_do_ncf, "NCF no debe existir en borrador pre-post"
    m.action_post()
    record(
        "factura_manual_b02_ncf",
        m.state == "posted" and m.justech_do_ncf and m.justech_do_ncf.startswith("B02"),
        invoice=m.name,
        ncf=m.justech_do_ncf,
        via="action_post",
    )
    env.cr.commit()
except Exception as exc:
    env.cr.rollback()
    record("factura_manual_b02_ncf", False, error=str(exc))

# 2 — Factura manual B01 vía _post directo (simula camino POS)
try:
    m = e["account.move"].create(invoice_vals(partner_rnc, doc_b01))
    m._post(soft=False)
    record(
        "factura_manual_b01_ncf_via_post",
        m.state == "posted" and m.justech_do_ncf and m.justech_do_ncf.startswith("B01"),
        invoice=m.name,
        ncf=m.justech_do_ncf,
        via="_post",
    )
    env.cr.commit()
except Exception as exc:
    env.cr.rollback()
    record("factura_manual_b01_ncf_via_post", False, error=str(exc))

# 3 — Cotización → factura
try:
    so = e["sale.order"].create(
        {
            "partner_id": partner_cf.id,
            "justech_do_document_type_id": doc_b02.id,
            "order_line": [
                Command.create(
                    {
                        "product_id": product.id,
                        "product_uom_qty": 1,
                        "price_unit": 1000.0,
                        "tax_ids": [Command.set(tax.ids)],
                    }
                )
            ],
        }
    )
    so.action_confirm()
    inv = so._create_invoices()
    inv.action_post()
    record(
        "cotizacion_factura_ncf",
        inv.justech_do_ncf and inv.justech_do_ncf.startswith("B02"),
        order=so.name,
        invoice=inv.name,
        ncf=inv.justech_do_ncf,
    )
    env.cr.commit()
except Exception as exc:
    env.cr.rollback()
    record("cotizacion_factura_ncf", False, error=str(exc))

# 14 — No NCF en borrador (soft future)
try:
    future = e["account.move"].create(
        {
            **invoice_vals(partner_cf, doc_b02),
            "date": date.today() + timedelta(days=30),
            "invoice_date": date.today() + timedelta(days=30),
        }
    )
    future._post(soft=True)
    record(
        "no_ncf_borrador_autopost_futuro",
        future.state == "draft" and not future.justech_do_ncf,
        state=future.state,
        auto_post=future.auto_post,
        ncf=future.justech_do_ncf or None,
    )
    env.cr.commit()
except Exception as exc:
    env.cr.rollback()
    record("no_ncf_borrador_autopost_futuro", False, error=str(exc))

# 13 — No doble NCF / consumo único
try:
    m = e["account.move"].create(invoice_vals(partner_cf, doc_b02))
    m.action_post()
    ncf1 = m.justech_do_ncf
    consumptions = e["justech.do.ncf.consumption"].search_count(
        [("move_id", "=", m.id), ("state", "=", "consumed")]
    )
    record(
        "no_doble_ncf",
        bool(ncf1) and consumptions == 1,
        ncf=ncf1,
        consumption_records=consumptions,
    )
    env.cr.commit()
except Exception as exc:
    env.cr.rollback()
    record("no_doble_ncf", False, error=str(exc))

# --- POS block (4-11) ---
pm_cash = e["pos.payment.method"].search([("name", "=", "Efectivo")], limit=1)
pm_card = e["pos.payment.method"].search([("name", "=", "Tarjeta")], limit=1)
cfg = e["pos.config"].search([("name", "=", POS_CONFIG_NAME)], limit=1)


def close_sessions():
    for s in e["pos.session"].search([("config_id", "=", cfg.id), ("state", "!=", "closed")]):
        try:
            if s.state == "opened":
                s.action_pos_session_closing_control()
            if s.state != "closed":
                s.action_pos_session_close()
        except Exception:
            pass


def open_session():
    close_sessions()
    cfg.open_ui()
    session = cfg.current_session_id
    session.set_opening_control(0, None)
    return cfg, session


def build_order(session, partner, payments, uuid):
    pricelist = cfg.pricelist_id
    currency = session.currency_id
    fpos = cfg.default_fiscal_position_id
    qty = 1
    price = pricelist._get_product_price(product, qty)
    taxes = fpos.map_tax(product.taxes_id) if fpos else product.taxes_id
    tv = taxes.compute_all(price, currency, qty) if taxes else {"total_excluded": price, "total_included": price}
    line = (
        0,
        0,
        {
            "product_id": product.id,
            "qty": qty,
            "price_unit": price,
            "price_subtotal": tv["total_excluded"],
            "price_subtotal_incl": tv["total_included"],
            "tax_ids": [(6, 0, taxes.ids)],
            "discount": 0,
        },
    )
    pay_lines = [(0, 0, {"amount": amt, "payment_method_id": pm.id}) for pm, amt in payments]
    total_incl = tv["total_included"]
    return {
        "name": f"Order {uuid}",
        "uuid": uuid,
        "session_id": session.id,
        "partner_id": partner.id,
        "pricelist_id": pricelist.id,
        "fiscal_position_id": fpos.id if fpos else False,
        "lines": [line],
        "amount_total": total_incl,
        "amount_tax": total_incl - tv["total_excluded"],
        "amount_paid": sum(a for _, a in payments),
        "amount_return": 0,
        "payment_ids": pay_lines,
        "to_invoice": False,
        "user_id": e.uid,
        "date_order": fields.Datetime.to_string(fields.Datetime.now()),
        "last_order_preparation_change": "{}",
    }


def pos_sale(partner, payments, uuid):
    order_data = build_order(session, partner, payments, uuid)
    res = e["pos.order"].sync_from_ui([order_data])
    order = e["pos.order"].browse(res["pos.order"][0]["id"])
    order.action_pos_order_invoice()
    inv = order.account_move
    return order, inv


pos_order_ids = []
try:
    cfg, session = open_session()
    price_incl = cfg.pricelist_id._get_product_price(product, 1)
    tv = tax.compute_all(price_incl, session.currency_id, 1)
    total_incl = tv["total_included"]
    half = round(total_incl / 2, 2)
    rest = round(total_incl - half, 2)
    qty_before = product.qty_available

    o1, i1 = pos_sale(partner_cf, [(pm_cash, total_incl)], f"p29d-{RUN_ID}-cf")
    record(
        "pos_consumidor_final_b02_efectivo",
        i1.state == "posted" and i1.justech_do_ncf and i1.justech_do_ncf.startswith("B02"),
        order=o1.name,
        invoice=i1.name,
        ncf=i1.justech_do_ncf,
        doc=i1.justech_do_document_type_id.prefix,
    )
    pos_order_ids.append(o1.id)

    o2, i2 = pos_sale(partner_rnc, [(pm_card, total_incl)], f"p29d-{RUN_ID}-rnc")
    record(
        "pos_cliente_rnc_b01_tarjeta",
        i2.justech_do_ncf and i2.justech_do_ncf.startswith("B01"),
        invoice=i2.name,
        ncf=i2.justech_do_ncf,
    )
    pos_order_ids.append(o2.id)

    o3, i3 = pos_sale(partner_cf, [(pm_cash, half), (pm_card, rest)], f"p29d-{RUN_ID}-mix")
    record("pos_pago_mixto", i3.justech_do_ncf and i3.state == "posted", ncf=i3.justech_do_ncf)
    pos_order_ids.append(o3.id)

    pos_invoices = e["account.move"].browse(
        e["pos.order"].browse(pos_order_ids).mapped("account_move").ids
    )
    record(
        "pos_asientos_contables",
        len(pos_invoices.filtered(lambda m: m.state == "posted")) >= 3,
        invoices=pos_invoices.mapped("name"),
    )

    record(
        "pos_movimiento_inventario",
        product.qty_available < qty_before,
        qty_before=qty_before,
        qty_after=product.qty_available,
    )

    cash_pm = session.payment_method_ids.filtered("is_cash_count")[:1]
    total_cash = sum(
        session.order_ids.payment_ids.filtered(
            lambda p: p.payment_method_id.id == cash_pm.id
        ).mapped("amount")
    )
    session.post_closing_cash_details(total_cash)
    session.close_session_from_ui()
    record(
        "pos_cierre_sesion",
        session.state == "closed",
        move=session.move_id.name if session.move_id else None,
    )
    env.cr.commit()
except Exception as exc:
    env.cr.rollback()
    record("pos_block", False, error=str(exc))

# 15 — Override manual NCF (al final; no consume rango automáticamente)
try:
    rng = sync_ncf_range_next(doc_b02, journal_inv)
    manual_ncf = doc_b02.format_ncf(rng.next_sequence) if rng else None
    m = e["account.move"].create(invoice_vals(partner_cf, doc_b02, ncf_manual=manual_ncf))
    pre = m.justech_do_ncf
    m.action_post()
    record(
        "override_manual_ncf",
        manual_ncf and pre == manual_ncf and m.justech_do_ncf == manual_ncf and m.state == "posted",
        ncf=m.justech_do_ncf,
        invoice=m.name,
    )
    env.cr.commit()
except Exception as exc:
    env.cr.rollback()
    record("override_manual_ncf", False, error=str(exc))

# 12 — Reporte 607 probe
try:
    Exporter = e["justech.do.dgii.607.exporter"]
    period_start = date.today().replace(day=1)
    period_end = date.today()
    posted = e["account.move"].search(
        [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", period_start),
            ("justech_do_ncf", "!=", False),
        ],
        order="id desc",
        limit=20,
    )
    sample = posted[:5]
    errors = []
    for move in sample:
        errors.extend(Exporter._dgii_validate_single_move(move, period_start, period_end))
    record(
        "reporte_fiscal_607_no_rompe",
        len(sample) >= 3 and not errors,
        sample_ncf=sample.mapped("justech_do_ncf"),
        validation_errors=errors[:5],
    )
    env.cr.commit()
except Exception as exc:
    env.cr.rollback()
    record("reporte_fiscal_607_no_rompe", False, error=str(exc))

passed = sum(1 for t in report["tests"] if t["pass"])
report["summary"] = {
    "passed": passed,
    "total": len(report["tests"]),
    "all_pass": report["ok"],
}

env.cr.commit()
_save()
print(json.dumps(report["summary"], ensure_ascii=False))
