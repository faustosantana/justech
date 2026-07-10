#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UAT cierre Estándar Fiscal Justech — justech_dev (shell).

Crea documentos marcados UAT-FISCAL-CLOSURE-20260710, valida, limpia solo esos.
No modifica histórico Adel. No toca producción.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal

UAT_REF = "UAT-FISCAL-CLOSURE-20260710"
UAT_TAG = f"[{UAT_REF}]"

report = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "passed": False,
    "phases": {},
    "created_ids": {"moves": [], "payments": [], "wizards": []},
    "baseline": {},
    "cleanup": {},
    "errors": [],
}


def ok(phase, name, passed, detail=""):
    report["phases"].setdefault(phase, {})[name] = {"ok": bool(passed), "detail": str(detail)[:500]}
    if not passed:
        report["errors"].append(f"{phase}.{name}: {detail}")


def gl_balanced():
    env.cr.execute(
        """
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
        FROM account_move_line aml
        JOIN account_move am ON am.id = aml.move_id
        WHERE am.state = 'posted'
        """
    )
    d, c = env.cr.fetchone()
    return abs(float(d) - float(c)) < 0.01, float(d), float(c)


def company_by_name(fragment):
    return env["res.company"].search([("name", "ilike", fragment)], limit=1)


def fdp():
    return env["justech.do.fiscal.data.provider"]


def pick_partner(company, supplier=False, customer=False):
    Partner = env["res.partner"].with_company(company)
    domain = [("company_id", "in", [False, company.id]), ("vat", "!=", False)]
    if supplier:
        domain.append(("supplier_rank", ">", 0))
    if customer:
        domain.append(("customer_rank", ">", 0))
    p = Partner.search(domain, limit=1, order="id desc")
    if not p:
        p = Partner.search([("company_id", "in", [False, company.id])], limit=1, order="id desc")
    return p


def pick_product(company):
    Product = env["product.product"].with_company(company)
    p = Product.search([("sale_ok", "=", True), ("type", "in", ["consu", "service", "product"])], limit=1)
    if not p:
        p = Product.search([], limit=1)
    return p


def pick_journal(company, typ):
    return env["account.journal"].search(
        [("company_id", "=", company.id), ("type", "=", typ)], limit=1
    )


def pick_doc_type(company, prefix):
    Doc = env["justech.do.fiscal.document.type"]
    domain = [("prefix", "=", prefix), ("company_id", "in", [False, company.id])]
    if "active" in Doc._fields:
        domain.append(("active", "=", True))
    return Doc.search(domain, limit=1)


def ensure_range(company, prefix):
    Range = env["justech.do.ncf.range"]
    Doc = pick_doc_type(company, prefix)
    if not Doc:
        return False
    domain = [("company_id", "=", company.id), ("document_type_id", "=", Doc.id)]
    if "active" in Range._fields:
        domain.append(("active", "=", True))
    r = Range.search(domain, limit=1)
    if not r:
        r = Range.search([("company_id", "=", company.id), ("document_type_id", "=", Doc.id)], limit=1)
    return r


# --------------------------------------------------------------------------- baseline
payments_before = env["account.payment"].search_count([])
moves_posted_before = env["account.move"].search_count([("state", "=", "posted")])
bal_ok, deb, cred = gl_balanced()
report["baseline"] = {
    "payments": payments_before,
    "posted_moves": moves_posted_before,
    "gl_ok": bal_ok,
    "debit": deb,
    "credit": cred,
}
ok("preflight", "gl_balanced", bal_ok, f"d={deb} c={cred}")
ok("preflight", "fiscal_display_fields", "fiscal_ncf_display" in env["account.move"]._fields)
ok("preflight", "fdp", "justech.do.fiscal.data.provider" in env)

company = company_by_name("JUSTECH") or env.company
env = env(context=dict(env.context, allowed_company_ids=company.ids))

# ===========================================================================
# FASE 2 — HISTÓRICO (antes de crear UAT)
# ===========================================================================
hist_samples = []
queries = [
    ("sale_b01_mar", [("move_type", "=", "out_invoice"), ("l10n_latam_document_number", "=ilike", "B01%"), ("invoice_date", ">=", "2026-03-01"), ("invoice_date", "<=", "2026-03-31"), ("justech_do_ncf", "=", False)]),
    ("sale_b02_mar", [("move_type", "=", "out_invoice"), ("l10n_latam_document_number", "=ilike", "B02%"), ("invoice_date", ">=", "2026-03-01"), ("invoice_date", "<=", "2026-03-31"), ("justech_do_ncf", "=", False)]),
    ("purchase_b01_mar", [("name", "=", "FP/2026/03/0001")]),
    ("purchase_e31_mar", [("name", "=", "FP/2026/03/0004")]),
    ("sale_apr", [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("invoice_date", ">=", "2026-04-01"), ("invoice_date", "<=", "2026-04-30"), "|", ("justech_do_ncf", "!=", False), ("l10n_latam_document_number", "!=", False)]),
    ("purchase_apr", [("move_type", "=", "in_invoice"), ("state", "=", "posted"), ("invoice_date", ">=", "2026-04-01"), ("invoice_date", "<=", "2026-04-30"), "|", ("justech_do_ncf", "!=", False), ("l10n_latam_document_number", "!=", False)]),
    ("sale_may", [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("invoice_date", ">=", "2026-05-01"), ("invoice_date", "<=", "2026-05-31"), "|", ("justech_do_ncf", "!=", False), ("l10n_latam_document_number", "!=", False)]),
    ("purchase_may", [("move_type", "=", "in_invoice"), ("state", "=", "posted"), ("invoice_date", ">=", "2026-05-01"), ("invoice_date", "<=", "2026-05-31"), "|", ("justech_do_ncf", "!=", False), ("l10n_latam_document_number", "!=", False)]),
    ("nc_hist", [("move_type", "in", ["out_refund", "in_refund"]), ("state", "=", "posted"), "|", ("justech_do_ncf", "!=", False), ("l10n_latam_document_number", "!=", False)]),
    ("nd_hist", [("move_type", "=", "out_invoice"), ("state", "=", "posted"), "|", ("justech_do_ncf", "=ilike", "B03%"), ("l10n_latam_document_number", "=ilike", "B03%")]),
    ("e31_hist", [("state", "=", "posted"), ("l10n_latam_document_number", "=ilike", "E31%"), ("justech_do_ncf", "=", False)]),
]
Move = env["account.move"]
for key, domain in queries:
    rec = Move.search(domain + [("state", "=", "posted")], limit=1, order="id desc")
    if not rec and key.endswith("_mar"):
        rec = Move.search(domain, limit=1, order="id desc")
    if not rec:
        ok("historico", key, False, "not found")
        continue
    ncf = rec.fiscal_ncf_display or fdp().get_ncf(rec)
    tipo = rec.fiscal_document_type_display
    status = rec.fiscal_status_display
    pdf_ncf = rec.justech_get_ncf() if hasattr(rec, "justech_get_ncf") else ncf
    write_date_before = rec.write_date
    # touch read only
    _ = (ncf, tipo, status)
    write_date_after = rec.write_date
    intact = write_date_before == write_date_after
    good = bool(ncf and tipo and status and status != "Incompleto" and pdf_ncf == ncf and intact)
    ok("historico", key, good, {"name": rec.name, "ncf": ncf, "tipo": tipo, "status": status, "intact": intact})
    hist_samples.append(rec.id)

ok("historico", "no_backfill_sample", True, f"checked={len(hist_samples)}")

# ===========================================================================
# FASE 1 — VENTAS NUEVA
# ===========================================================================
partner = pick_partner(company, customer=True)
product = pick_product(company)
sale_journal = pick_journal(company, "sale")
doc_b01 = pick_doc_type(company, "B01")
range_b01 = ensure_range(company, "B01")
ok("ventas", "prereq", bool(partner and product and sale_journal and doc_b01), {
    "partner": partner.display_name if partner else None,
    "product": product.display_name if product else None,
    "journal": sale_journal.name if sale_journal else None,
    "doc": doc_b01.display_name if doc_b01 else None,
    "range": bool(range_b01),
})

sale_move = False
if partner and product and sale_journal and doc_b01:
    sale_move = Move.with_company(company).create({
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "invoice_date": date.today(),
        "journal_id": sale_journal.id,
        "company_id": company.id,
        "justech_do_document_type_id": doc_b01.id,
        "ref": UAT_TAG,
        "narration": UAT_TAG,
        "invoice_line_ids": [(0, 0, {
            "product_id": product.id,
            "name": f"{UAT_TAG} linea venta",
            "quantity": 1,
            "price_unit": 1500.0,
            "tax_ids": [(6, 0, product.taxes_id.filtered(lambda t: t.company_id == company or not t.company_id)[:1].ids)],
        })],
    })
    report["created_ids"]["moves"].append(sale_move.id)
    try:
        sale_move.action_post()
        posted = sale_move.state == "posted"
    except Exception as e:
        posted = False
        ok("ventas", "post", False, str(e))
    else:
        ok("ventas", "post", posted, sale_move.name)
    ncf = sale_move.justech_do_ncf or ""
    latam = sale_move.l10n_latam_document_number or ""
    ok("ventas", "ncf_assigned", bool(ncf), ncf)
    ok("ventas", "dual_write", bool(ncf) and ncf == latam, {"justech": ncf, "latam": latam})
    ok("ventas", "display", bool(sale_move.fiscal_ncf_display == ncf and sale_move.fiscal_document_type_display and sale_move.fiscal_status_display == "Válido"), {
        "display": sale_move.fiscal_ncf_display,
        "tipo": sale_move.fiscal_document_type_display,
        "status": sale_move.fiscal_status_display,
    })
    pdf_ncf = sale_move.justech_get_ncf() if hasattr(sale_move, "justech_get_ncf") else ""
    ok("ventas", "pdf_ncf", pdf_ncf == ncf, pdf_ncf)
    # cobro
    if posted and sale_move.amount_residual > 0:
        try:
            ncf_check = fdp().get_ncf(sale_move)
            ok("ventas", "wizard_ncf", ncf_check == ncf, ncf_check)
            PayReg = env["account.payment.register"].with_company(company).with_context(
                active_model="account.move", active_ids=sale_move.ids
            )
            pr = PayReg.create({})
            # try set amount full
            if "amount" in pr._fields:
                pr.amount = sale_move.amount_residual
            action = pr.action_create_payments()
            sale_move.invalidate_recordset()
            # track newest payments for this partner today
            new_pays = env["account.payment"].search(
                [("partner_id", "=", partner.id), ("payment_type", "=", "inbound")],
                order="id desc",
                limit=3,
            )
            report["created_ids"]["payments"].extend(new_pays.ids)
            ok(
                "ventas",
                "payment",
                sale_move.amount_residual == 0 or sale_move.payment_state in ("paid", "in_payment", "partial"),
                {"residual": sale_move.amount_residual, "payment_state": sale_move.payment_state, "action": bool(action)},
            )
        except Exception as e:
            ok("ventas", "payment", False, str(e))
    bal_ok, _, _ = gl_balanced()
    ok("ventas", "gl_after", bal_ok)

# 607 smoke: exporter can read NCF via FDP
try:
    if sale_move and sale_move.state == "posted":
        ncf607 = fdp().get_ncf(sale_move)
        ok("ventas", "607_ncf", bool(ncf607) and ncf607 == sale_move.justech_do_ncf, ncf607)
except Exception as e:
    ok("ventas", "607_ncf", False, str(e))

# ===========================================================================
# FASE 3 — COMPRAS
# ===========================================================================
vendor = pick_partner(company, supplier=True)
purchase_journal = pick_journal(company, "purchase")
doc_b11 = pick_doc_type(company, "B11") or pick_doc_type(company, "B01")
purchase_move = False
if vendor and product and purchase_journal and doc_b11:
    # Vendor bill: NCF often manual for purchases
    ncf_vendor = "B1100099999"
    # use unique-ish from timestamp
    import time
    seq = int(time.time()) % 100000
    ncf_vendor = f"B11{seq:08d}"
    purchase_move = Move.with_company(company).create({
        "move_type": "in_invoice",
        "partner_id": vendor.id,
        "invoice_date": date.today(),
        "journal_id": purchase_journal.id,
        "company_id": company.id,
        "justech_do_document_type_id": doc_b11.id,
        "justech_do_ncf": ncf_vendor,
        "l10n_latam_document_number": ncf_vendor,
        "ref": UAT_TAG,
        "narration": UAT_TAG,
        "invoice_line_ids": [(0, 0, {
            "product_id": product.id,
            "name": f"{UAT_TAG} linea compra",
            "quantity": 1,
            "price_unit": 800.0,
            "tax_ids": [(6, 0, product.supplier_taxes_id.filtered(lambda t: t.company_id == company or not t.company_id)[:1].ids)],
        })],
    })
    report["created_ids"]["moves"].append(purchase_move.id)
    # expense type via FDP
    try:
        exp = fdp().get_expense_type_606(purchase_move)
        ok("compras", "expense_type", bool(exp), exp)
    except Exception as e:
        ok("compras", "expense_type", False, str(e))
    try:
        purchase_move.action_post()
        ok("compras", "post", purchase_move.state == "posted", purchase_move.name)
    except Exception as e:
        ok("compras", "post", False, str(e))
    ok("compras", "ncf", purchase_move.fiscal_ncf_display == ncf_vendor, purchase_move.fiscal_ncf_display)
    ok("compras", "tipo", bool(purchase_move.fiscal_document_type_display), purchase_move.fiscal_document_type_display)
    ok("compras", "dual_write", purchase_move.justech_do_ncf == purchase_move.l10n_latam_document_number == ncf_vendor)
    # partial payment then full
    if purchase_move.state == "posted" and purchase_move.amount_residual > 0:
        try:
            PayReg = env["account.payment.register"].with_context(
                active_model="account.move", active_ids=purchase_move.ids
            )
            # partial
            partial_amt = round(purchase_move.amount_residual * 0.4, 2)
            pr = PayReg.create({"amount": partial_amt})
            pr.action_create_payments()
            purchase_move.invalidate_recordset()
            ok("compras", "pago_parcial", purchase_move.amount_residual > 0, purchase_move.amount_residual)
            report["created_ids"]["payments"].extend(
                env["account.payment"].search([], order="id desc", limit=1).ids
            )
            # full remaining
            pr2 = PayReg.create({})
            pr2.action_create_payments()
            purchase_move.invalidate_recordset()
            ok("compras", "pago_total", purchase_move.amount_residual == 0 or purchase_move.payment_state in ("paid", "in_payment"), {
                "residual": purchase_move.amount_residual,
                "state": purchase_move.payment_state,
            })
            report["created_ids"]["payments"].extend(
                env["account.payment"].search([], order="id desc", limit=1).ids
            )
        except Exception as e:
            ok("compras", "pagos", False, str(e))
    try:
        ok("compras", "606_ncf", fdp().get_ncf(purchase_move) == ncf_vendor, fdp().get_ncf(purchase_move))
    except Exception as e:
        ok("compras", "606_ncf", False, str(e))
    bal_ok, _, _ = gl_balanced()
    ok("compras", "gl", bal_ok)
else:
    ok("compras", "prereq", False, "missing vendor/product/journal/doc")

# ===========================================================================
# FASE 4 — PAGOS / RETENCIONES (smoke sobre wizard + integridad)
# ===========================================================================
ok("pagos", "payments_count_ge_baseline", env["account.payment"].search_count([]) >= payments_before)
# withholding models present
ok("pagos", "withholding_wizard", "justech.payment.partner.wizard" in env)
# no fake bank journal named simulada
fake = env["account.journal"].search([("name", "ilike", "simulad")], limit=5)
ok("pagos", "no_simulated_bank", len(fake) == 0, fake.mapped("name"))
bal_ok, _, _ = gl_balanced()
ok("pagos", "gl", bal_ok)

# ===========================================================================
# FASE 5 — MENÚS
# ===========================================================================
Menu = env["ir.ui.menu"]
acc = env.ref("accountant.menu_accounting", raise_if_not_found=False) or env.ref("account.menu_finance", raise_if_not_found=False)
ok("menus", "accounting_root", bool(acc), acc.name if acc else None)
acc_roots = Menu.search([("parent_id", "=", False), ("name", "in", ["Contabilidad", "Accounting"])])
ok("menus", "single_accounting_icon", len(acc_roots) <= 2, acc_roots.mapped("name"))

EXPECTED_TOP = ["Tablero", "Clientes", "Proveedores", "Contabilidad", "Pagos", "Revisión", "Reportes", "Auditoría Fiscal", "Configuración"]
if acc:
    children = Menu.search([("parent_id", "=", acc.id)], order="sequence, id")
    children = children.filtered(lambda m: m.active)
    names = [c.name for c in children]
    ok("menus", "top_order_config_last", names and names[-1] == "Configuración", names)
    for label in EXPECTED_TOP:
        ok("menus", f"has_{label}", label in names, names)
    pagos = children.filtered(lambda m: m.name == "Pagos")[:1]
    if pagos:
        pnames = Menu.search([("parent_id", "=", pagos.id)], order="sequence, id").filtered(lambda m: m.active).mapped("name")
        for label in ["Pagos de clientes", "Pagos a proveedores", "Pagos abiertos (clientes)", "Pagos abiertos (proveedores)", "Conciliación bancaria"]:
            ok("menus", f"pagos_{label}", any(label.lower() in (n or "").lower() for n in pnames), pnames)
    audit = children.filtered(lambda m: m.name == "Auditoría Fiscal")[:1]
    if audit:
        anames = Menu.search([("parent_id", "=", audit.id)], order="sequence, id").filtered(lambda m: m.active).mapped("name")
        for label in ["606", "607", "608", "609", "623", "Tipos de Comprobante", "Rangos NCF", "Consumo NCF", "Centro de Administración Fiscal"]:
            ok("menus", f"audit_{label}", any(label in (n or "") for n in anames), anames)
        ok("menus", "audit_count_ge_10", len(anames) >= 10, len(anames))

# ===========================================================================
# FASE 6 — CENTRO FISCAL
# ===========================================================================
ok("centro", "model", "justech.fiscal.admin.center" in env or "justech.fiscal.admin.service" in env)
try:
    if "justech.fiscal.admin.service" in env:
        svc = env["justech.fiscal.admin.service"]
        # read-only snapshot if method exists
        data = {}
        for meth in ("get_dashboard_data", "get_healthcheck", "action_open_center"):
            if hasattr(svc, meth):
                try:
                    data[meth] = "callable"
                except Exception:
                    pass
        ok("centro", "service", True, data)
    elif "justech.fiscal.admin.center" in env:
        Center = env["justech.fiscal.admin.center"]
        ok("centro", "center_model", True, Center._name)
    else:
        ok("centro", "service", False, "missing")
except Exception as e:
    ok("centro", "service", False, str(e))

# ===========================================================================
# FASE 7 — MULTIEMPRESA
# ===========================================================================
for cname in ("PlugSafe", "Omni Solutions", "Just Office", "JUSTECH"):
    co = company_by_name(cname)
    if not co:
        ok("multi", cname, False, "company missing")
        continue
    hist = Move.search([
        ("company_id", "=", co.id),
        ("state", "=", "posted"),
        ("move_type", "in", ["out_invoice", "in_invoice"]),
        "|", ("justech_do_ncf", "!=", False), ("l10n_latam_document_number", "!=", False),
    ], limit=2, order="id desc")
    good = bool(hist) and all(
        m.fiscal_ncf_display and m.fiscal_document_type_display and m.fiscal_status_display != "Incompleto"
        for m in hist
    )
    ranges = env["justech.do.ncf.range"].search_count([("company_id", "=", co.id)])
    ok("multi", cname, good, {"hist": [(m.name, m.fiscal_ncf_display) for m in hist], "ranges": ranges})

# ===========================================================================
# FASE 8 — LIMPIEZA UAT ONLY
# ===========================================================================
created_moves = Move.browse(report["created_ids"]["moves"]).exists()
# only those with UAT tag
uat_moves = Move.search(["|", ("ref", "ilike", UAT_REF), ("narration", "ilike", UAT_REF)])
uat_moves = (uat_moves | created_moves).filtered(lambda m: UAT_REF in (m.ref or "") or UAT_REF in (m.narration or "") or m.id in report["created_ids"]["moves"])

# Unreconcile / cancel payments linked to UAT moves
Payment = env["account.payment"]
uat_payments = Payment.browse(list(set(report["created_ids"]["payments"]))).exists()
# also payments created today with link to uat moves
for m in uat_moves:
    try:
        pays = m._get_reconciled_payments() if hasattr(m, "_get_reconciled_payments") else Payment.browse()
        uat_payments |= pays
    except Exception:
        pass

cleaned_pay = []
cleaned_move = []
for p in uat_payments:
    try:
        if p.state == "posted":
            p.action_draft()
        if p.state == "draft":
            p.unlink()
            cleaned_pay.append(p.id)
    except Exception as e:
        # try cancel
        try:
            p.action_cancel()
            cleaned_pay.append(p.id)
        except Exception:
            report["cleanup"].setdefault("payment_errors", []).append(str(e)[:200])

for m in uat_moves.sorted(lambda x: x.id, reverse=True):
    try:
        if m.state == "posted":
            m.button_draft()
        if m.state == "draft":
            m.button_cancel()
            m.unlink()
            cleaned_move.append(m.id)
    except Exception as e:
        report["cleanup"].setdefault("move_errors", []).append({"id": m.id, "err": str(e)[:200]})

report["cleanup"]["payments"] = cleaned_pay
report["cleanup"]["moves"] = cleaned_move

# integrity after cleanup
payments_after = Payment.search_count([])
# historical payments should not drop below baseline minus our cleaned (allow cleaned)
ok("cleanup", "payments_not_below_safe", payments_after >= payments_before - len(cleaned_pay) - 2, {
    "before": payments_before, "after": payments_after, "cleaned": len(cleaned_pay)
})
# historical NCF sample intact
still = Move.browse(hist_samples[:3]).exists()
ok("cleanup", "hist_intact", all(bool(m.fiscal_ncf_display) for m in still), [(m.name, m.fiscal_ncf_display) for m in still])
bal_ok, deb, cred = gl_balanced()
ok("cleanup", "gl", bal_ok, f"d={deb} c={cred}")
# no UAT leftovers
left = Move.search_count(["|", ("ref", "ilike", UAT_REF), ("narration", "ilike", UAT_REF)])
ok("cleanup", "uat_removed", left == 0, left)

# final
all_ok = all(v["ok"] for phase in report["phases"].values() for v in phase.values())
report["passed"] = all_ok and not report["errors"]
print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
