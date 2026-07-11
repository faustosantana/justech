# Gate 2 — Operación E2E (justech_dev) — evidencia consolidada
# Ejecutado 2026-07-11 en erp.justech.do / justech_dev
from odoo import api, fields

admin = env["res.users"].sudo().search([("login", "=", "jinette@dynamicspm.com")], limit=1)
uenv = api.Environment(env.cr, admin.id, {"allowed_company_ids": [1, 2, 3, 4]})
fails = []


def ok(name, cond, detail=""):
    print("%s %s %s" % ("PASS" if cond else "FAIL", name, detail))
    if not cond:
        fails.append((name, str(detail)[:200]))


# Ventas E2E residual evidence
sale_inv = uenv["account.move"].sudo().search(
    [("name", "=", "FC/2026/00398"), ("company_id", "=", 1)], limit=1
)
ok("sale_invoice_posted", sale_inv.state == "posted", sale_inv.name)
ok("sale_ncf", bool(sale_inv.justech_do_ncf), sale_inv.justech_do_ncf)
ok("sale_payment_state", sale_inv.payment_state in ("paid", "in_payment", "partial"), sale_inv.payment_state)
env.cr.execute(
    "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM account_move_line WHERE move_id=%s",
    [sale_inv.id],
)
d, c = env.cr.fetchone()
ok("sale_gl", abs(d - c) < 0.01, "d=%s c=%s" % (d, c))

# Compras
bill = uenv["account.move"].sudo().browse(4293)
ok("purchase_bill_posted", bill.state == "posted", bill.name)
ok("purchase_ncf", bool(bill.justech_do_ncf), bill.justech_do_ncf)
ok("purchase_payment_state", bill.payment_state in ("paid", "in_payment", "partial"), bill.payment_state)
env.cr.execute(
    "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM account_move_line WHERE move_id=%s",
    [bill.id],
)
d, c = env.cr.fetchone()
ok("purchase_gl", abs(d - c) < 0.01, "d=%s c=%s" % (d, c))

# DGII reports period
today = fields.Date.context_today(uenv.user)
period = "%04d%02d" % (today.year, today.month)
Report = uenv["justech.do.fiscal.report"].sudo()
r607 = Report.search([("company_id", "=", 1), ("report_type", "=", "607"), ("period_code", "=", period)], limit=1)
r606 = Report.search([("company_id", "=", 1), ("report_type", "=", "606"), ("period_code", "=", period)], limit=1)
ok("report_607_exists", bool(r607), r607.state if r607 else None)
ok("report_606_exists", bool(r606), r606.state if r606 else None)

ok("exporters", "justech.do.dgii.606.exporter" in uenv and "justech.do.dgii.607.exporter" in uenv)
ok("withholding", "justech.do.withholding.catalog" in uenv or "justech.payment.withholding.line" in uenv)
ok("bank_journals", uenv["account.journal"].search_count([("type", "=", "bank"), ("company_id", "=", 1)]) >= 1)
ok("fiscal_center", "justech.fiscal.admin.center" in uenv)

# No hard missing NCF after gate1+2
env.cr.execute(
    """
    SELECT count(*) FROM account_move
    WHERE state='posted' AND move_type IN ('out_invoice','out_refund') AND company_id=1
      AND COALESCE(justech_do_ncf,'')='' AND COALESCE(l10n_latam_document_number,'')=''
    """
)
ok("no_hard_missing_ncf", env.cr.fetchone()[0] == 0)

print("---")
print("GATE2_FAILS", len(fails))
for f in fails:
    print("FAIL", f)
print("GATE2_PASS" if not fails else "GATE2_FAIL")
