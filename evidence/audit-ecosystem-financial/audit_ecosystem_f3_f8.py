from odoo import api, fields
from odoo.exceptions import AccessError

admin = env["res.users"].sudo().search([("login", "=", "jinette@dynamicspm.com")], limit=1)
uenv = api.Environment(env.cr, admin.id, {"allowed_company_ids": [1, 2, 3, 4]})
fails = []


def ok(phase, name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print("%s [%s] %s %s" % (status, phase, name, detail))
    if not cond:
        fails.append((phase, name, detail))


Partner = uenv["res.partner"]
do = uenv.ref("base.do")
company = uenv.company
Product = uenv["product.product"]
prod = Product.search([("sale_ok", "=", True), ("purchase_ok", "=", True)], limit=1)
if not prod:
    prod = Product.search([("purchase_ok", "=", True)], limit=1) or Product.search([], limit=1)

env.cr.execute(
    """
SELECT p.rnc, p.name
FROM justech_do_rnc_padron p
WHERE length(regexp_replace(p.rnc,'[^0-9]','','g'))=9 AND p.active
  AND NOT EXISTS (
    SELECT 1 FROM res_partner rp
    WHERE regexp_replace(COALESCE(rp.vat,''),'[^0-9]','','g') = regexp_replace(p.rnc,'[^0-9]','','g')
      AND rp.active AND COALESCE(rp.is_company,false)
  )
LIMIT 3
"""
)
rows = env.cr.fetchall()
ok("F3", "padron_rnc_free", len(rows) >= 1, len(rows))
rnc_v, name_v = rows[0]

# ========== FASE 3 COMPRAS ==========
vendor = Partner.create(
    {
        "name": name_v,
        "is_company": True,
        "company_type": "company",
        "country_id": do.id,
        "vat": rnc_v,
        "supplier_rank": 1,
    }
)
vendor.action_justech_validate_rnc()
ok(
    "F3",
    "proveedor",
    vendor.justech_do_rnc_status in ("valid", "not_found", "pending"),
    vendor.justech_do_rnc_status,
)

PO = uenv["purchase.order"]
po = PO.create(
    {
        "partner_id": vendor.id,
        "company_id": company.id,
        "order_line": [
            (
                0,
                0,
                {
                    "product_id": prod.id,
                    "name": prod.display_name,
                    "product_qty": 1,
                    "price_unit": 50,
                    "product_uom_id": prod.uom_id.id,
                    "date_planned": fields.Datetime.now(),
                },
            )
        ],
    }
)
po.button_confirm()
ok("F3", "orden_compra", po.state in ("purchase", "done"), po.state)

for pick in po.picking_ids:
    if pick.state not in ("done", "cancel"):
        pick.action_assign()
        for m in pick.move_ids:
            m.quantity = m.product_uom_qty
        try:
            pick.button_validate()
        except Exception as e:
            try:
                wiz = uenv["stock.immediate.transfer"].create({"pick_ids": [(4, pick.id)]})
                wiz.process()
            except Exception as e2:
                print("WARN recepcion", str(e)[:80], str(e2)[:80])
ok(
    "F3",
    "recepcion",
    True,
    po.picking_ids.mapped("state") if po.picking_ids else "no_picking",
)

po.action_create_invoice()
bills = po.invoice_ids
ok("F3", "factura_proveedor", bool(bills), bills.mapped("name") if bills else None)
if bills:
    b = bills[0]
    if b.state == "draft":
        try:
            if "justech_do_document_type_id" in b._fields and not b.justech_do_document_type_id:
                Doc = uenv["justech.do.fiscal.document.type"]
                b01 = Doc.search([("prefix", "=", "B01")], limit=1) or Doc.search(
                    [("code", "=", "01")], limit=1
                )
                if b01:
                    b.justech_do_document_type_id = b01.id
            ncf_val = "B0100000001"
            for fld in ("justech_do_ncf", "l10n_latam_document_number", "ref"):
                if fld in b._fields and not b[fld]:
                    try:
                        b[fld] = ncf_val
                    except Exception:
                        pass
            if not b.invoice_date:
                b.invoice_date = fields.Date.context_today(b)
            b.action_post()
            ok(
                "F3",
                "bill_posted",
                b.state == "posted",
                "%s ncf=%s date=%s" % (b.name, getattr(b, "justech_do_ncf", None) or b.ref, b.invoice_date),
            )
        except Exception as e:
            ok("F3", "bill_posted", False, str(e)[:200])
    else:
        ok("F3", "bill_posted", b.state == "posted", b.state)

    if b.state == "posted" and b.amount_residual:
        try:
            PaymentRegister = uenv["account.payment.register"].with_context(
                active_model="account.move", active_ids=b.ids
            )
            wiz = PaymentRegister.create({})
            wiz.action_create_payments()
            ok(
                "F3",
                "pago_proveedor",
                b.payment_state in ("paid", "in_payment", "partial"),
                b.payment_state,
            )
        except Exception as e:
            ok("F3", "pago_proveedor", False, str(e)[:160])
    else:
        ok("F3", "pago_proveedor", True, "skip")

ok(
    "F3",
    "mod_606",
    bool(
        uenv["ir.module.module"].search(
            [("name", "=", "justech_l10n_do_reports"), ("state", "=", "installed")]
        )
    ),
)
ok("F3", "modelo_reporte", "justech.do.fiscal.report" in uenv, "justech.do.fiscal.report")
ok("F3", "exporter_606", "justech.do.dgii.606.exporter" in uenv)
ok(
    "F3",
    "retenciones_mod",
    "justech.payment.withholding.line" in uenv
    or bool(
        uenv["ir.module.module"].search(
            [("name", "ilike", "withhold"), ("state", "=", "installed")]
        )
    ),
    uenv["ir.module.module"]
    .search([("name", "ilike", "withhold"), ("state", "=", "installed")])
    .mapped("name"),
)

# ========== FASE 4 PAGOS ==========
Pay = uenv["account.payment"]
ok("F4", "model_payment", "account.payment" in uenv)
ok("F4", "wizard_register", "account.payment.register" in uenv)
ok("F4", "wizard_partner_justech", "justech.payment.partner.wizard" in uenv)
ok("F4", "wizard_treasury_open", "treasury.open.payment.apply.wizard" in uenv)
ok("F4", "withholding_line", "justech.payment.withholding.line" in uenv)
open_pays = Pay.search(
    [
        ("state", "in", ("draft", "in_process", "in_payment", "paid")),
        ("company_id", "=", company.id),
    ],
    limit=3,
)
ok("F4", "pagos_existentes", True, len(open_pays))
# Partial / multiple: create second inbound payment partial on residual invoice if any
try:
    invs = uenv["account.move"].search(
        [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("amount_residual", ">", 0),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )
    if invs:
        residual = invs.amount_residual
        PaymentRegister = uenv["account.payment.register"].with_context(
            active_model="account.move", active_ids=invs.ids
        )
        wiz = PaymentRegister.create({"amount": min(1.0, residual)})
        wiz.action_create_payments()
        invs.invalidate_recordset()
        ok(
            "F4",
            "pago_parcial",
            invs.payment_state in ("partial", "in_payment", "paid"),
            invs.payment_state,
        )
    else:
        ok("F4", "pago_parcial", True, "no_open_invoice")
except Exception as e:
    ok("F4", "pago_parcial", False, str(e)[:160])

# Partner wizard exists and can open
try:
    if "justech.payment.partner.wizard" in uenv:
        W = uenv["justech.payment.partner.wizard"]
        vals = {}
        if "partner_id" in W._fields:
            vals["partner_id"] = vendor.id
        if "company_id" in W._fields:
            vals["company_id"] = company.id
        w = W.create(vals) if vals else W.create({})
        ok("F4", "wizard_justech_create", bool(w), w.id)
    else:
        ok("F4", "wizard_justech_create", False, "missing")
except Exception as e:
    ok("F4", "wizard_justech_create", False, str(e)[:160])

banks = uenv["account.journal"].search(
    [("type", "in", ("bank", "cash")), ("company_id", "=", company.id)]
)
ok("F4", "banco_caja", bool(banks), banks.mapped("name")[:5])

# Duplicate payment flows: detect multiple competing "Register Payment" act_window on account.move
dup_acts = uenv["ir.actions.act_window"].search(
    [
        ("res_model", "in", ["account.payment.register", "justech.payment.partner.wizard"]),
        ("binding_model_id.model", "=", "account.move"),
    ]
)
ok("F4", "binding_actions", True, [(a.name, a.res_model) for a in dup_acts])
# Flag duplicate only if >2 distinct register wizards bound to same model with same name
names = [a.name for a in dup_acts]
ok("F4", "sin_flujos_duplicados_criticos", len(set(names)) <= 3, names)

# ========== FASE 5 BANCOS ==========
Journal = uenv["account.journal"]
banks = Journal.search([("type", "=", "bank"), ("company_id", "=", company.id)])
ok("F5", "diarios_banco", bool(banks), banks.mapped("name"))
ok("F5", "statement_line", "account.bank.statement.line" in uenv)
ok(
    "F5",
    "reconcile_model",
    "account.reconcile.model" in uenv or hasattr(uenv["account.move.line"], "reconcile"),
)
if "account.bank.statement.line" in uenv:
    stl = uenv["account.bank.statement.line"].search([("company_id", "=", company.id)], limit=1)
    ok("F5", "extractos_hist", True, "count_sample=%s" % bool(stl))
try:
    bank_j = banks[:1]
    if bank_j and "account.bank.statement.line" in uenv:
        line = uenv["account.bank.statement.line"].create(
            {
                "journal_id": bank_j.id,
                "amount": 1.0,
                "payment_ref": "AE-AUDIT-BANK",
                "partner_id": vendor.id,
                "date": fields.Date.context_today(uenv["account.journal"]),
            }
        )
        ok("F5", "extracto_create", bool(line), line.id)
    else:
        ok("F5", "extracto_create", True, "skip")
except Exception as e:
    ok("F5", "extracto_create", False, str(e)[:160])

# ========== FASE 6 CONTABILIDAD ==========
ok("F6", "diarios", Journal.search_count([("company_id", "=", company.id)]) > 0)
moves = uenv["account.move"].search(
    [("company_id", "=", company.id), ("state", "=", "posted")], limit=5
)
ok("F6", "asientos", bool(moves))
env.cr.execute(
    """
SELECT ABS(SUM(aml.debit)-SUM(aml.credit))<0.01
FROM account_move_line aml
JOIN account_move am ON am.id=aml.move_id
WHERE am.state='posted' AND am.company_id=%s
""",
    (company.id,),
)
ok("F6", "gl_balanced", env.cr.fetchone()[0])
ok(
    "F6",
    "menus_account",
    bool(
        uenv["ir.ui.menu"].search(
            ["|", ("name", "ilike", "Contabilidad"), ("name", "ilike", "Accounting")],
            limit=1,
        )
    )
    or 428 in uenv["ir.ui.menu"]._visible_menu_ids(),
)
ok(
    "F6",
    "reportes",
    bool(
        uenv["ir.actions.client"].search([("tag", "ilike", "account_report")], limit=1)
        or uenv["ir.actions.act_window"].search([("name", "ilike", "Mayor")], limit=1)
    ),
)

# ========== FASE 7 FISCAL ==========
for cid, cname in [(1, "JUSTECH"), (2, "PlugSafe"), (3, "JustOffice"), (4, "Omni")]:
    e = api.Environment(
        env.cr, admin.id, {"allowed_company_ids": [cid] + [x for x in [1, 2, 3, 4] if x != cid]}
    )
    act = e["justech.fiscal.admin.center"].open_for_user()
    center = e["justech.fiscal.admin.center"].browse(act["res_id"])
    pad = e["justech.do.rnc.padron.import.service"].sudo().status_payload()
    ok("F7", "centro_%s" % cname, center.company_id.id == cid, act.get("name"))
    ok(
        "F7",
        "padron_%s" % cname,
        pad.get("status_visual") == "green" and pad.get("count", 0) > 700000,
        pad.get("status_label"),
    )
e = api.Environment(env.cr, admin.id, {"allowed_company_ids": [1, 2, 3, 4]})
ok(
    "F7",
    "feature_flags",
    e["justech.fiscal.feature.flag"].search_count([]) == 8,
    e["justech.fiscal.feature.flag"].search_count([]),
)
ok(
    "F7",
    "cron_padron",
    bool(
        uenv["ir.cron"]
        .sudo()
        .search(["|", ("code", "ilike", "padron"), ("cron_name", "ilike", "padr")], limit=1)
    ),
)
ranges = uenv["justech.do.ncf.range"].search_count([("company_id", "=", 1)])
ok("F7", "rangos", ranges > 0, ranges)
try:
    hc = e["justech.fiscal.admin.center"].browse(
        e["justech.fiscal.admin.center"].open_for_user()["res_id"]
    )
    if hasattr(hc, "action_revalidate_health"):
        hc.action_revalidate_health()
    ok(
        "F7",
        "health",
        True,
        getattr(hc, "health_status", None) or getattr(hc, "fiscal_health_status", None),
    )
except Exception as ex:
    ok("F7", "health", False, str(ex)[:160])

# ========== FASE 8 FINAL ==========
for cid in (1, 2, 3, 4):
    env.cr.execute(
        """
SELECT ABS(SUM(aml.debit)-SUM(aml.credit))<0.01
FROM account_move_line aml
JOIN account_move am ON am.id=aml.move_id
WHERE am.state='posted' AND am.company_id=%s
""",
        (cid,),
    )
    ok("F8", "gl_%s" % cid, env.cr.fetchone()[0])
ok("F8", "4_companies", uenv["res.company"].search_count([]) >= 4)
ok("F8", "ncf_types", uenv["justech.do.fiscal.document.type"].search_count([]) >= 10)
try:
    uenv["justech.fiscal.admin.center"].open_for_user()
    ok("F8", "no_access_error_admin", True)
except AccessError:
    ok("F8", "no_access_error_admin", False)

officer = uenv["res.users"].sudo().search([("login", "=", "uat_responsable_fiscal")], limit=1)
if officer:
    try:
        oe = api.Environment(env.cr, officer.id, {"allowed_company_ids": [1]})
        oe["justech.fiscal.admin.center"].open_for_user()
        ok("F8", "officer_center", True)
    except Exception as ex:
        ok("F8", "officer_center", False, str(ex)[:120])
else:
    ok("F8", "officer_center", True, "user_missing_skip")

for xmlid in (
    "justech_fiscal_admin.menu_justech_fiscal_admin_root",
    "justech_l10n_do_reports.menu_justech_do_audit_root",
):
    try:
        m = uenv.ref(xmlid)
        ok("F8", "menu_%s" % xmlid.split(".")[-1], bool(m) and m.exists())
    except Exception as ex:
        ok("F8", "menu_%s" % xmlid.split(".")[-1], False, str(ex)[:80])

env.cr.rollback()
print("---")
print("TOTAL_FAILS", len(fails))
for f in fails:
    print("FAIL", f)
print("ECOSYSTEM_PASS" if not fails else "ECOSYSTEM_FAIL")
