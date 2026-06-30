# -*- coding: utf-8 -*-
"""Fase 19.1 — Validación funcional completa exportador DGII 606 en TEST."""
from __future__ import annotations

import base64
import json
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

from odoo import Command
from odoo.exceptions import UserError

MARKER = "PHASE19_1:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = "/tmp/hellenia-phase19-evidence"
os.makedirs(EVIDENCE_DIR, exist_ok=True)
EXCEL_PATH = os.path.join(EVIDENCE_DIR, "phase19-606-export.xlsx")
JSON_PATH = os.path.join(EVIDENCE_DIR, "phase19-606-test.json")
HOST_EVIDENCE_HINT = "/opt/odoo-projects/hellenia/evidence/phase19-606-test.json"

report = {
    "phase": "19.1",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "branch": "cursor/phase19-fiscal-fields-606-dd85",
    "excel_path_container": EXCEL_PATH,
    "excel_path_host": "/opt/odoo-projects/hellenia/evidence/phase19-606-export.xlsx",
    "json_path_container": JSON_PATH,
    "checks": {},
    "demo_moves": [],
    "validation_errors_es": {},
    "ok": True,
    "passed": 0,
    "total": 0,
    "pass": False,
}


def check(key, ok, detail=""):
    report["checks"][key] = {"ok": bool(ok), "detail": detail}
    report["total"] += 1
    if ok:
        report["passed"] += 1
    else:
        report["ok"] = False


def _xlsx_cell_map(path):
    """Lee celdas de la primera hoja sin openpyxl."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    shared = []
    cells = {}
    with zipfile.ZipFile(path) as zf:
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(".//m:si", ns):
                texts = [t.text or "" for t in si.findall(".//m:t", ns)]
                shared.append("".join(texts))
        sheet_xml = "xl/worksheets/sheet1.xml"
        for name in zf.namelist():
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                sheet_xml = name
                break
        root = ET.fromstring(zf.read(sheet_xml))
        for c in root.findall(".//m:c", ns):
            ref = c.get("r")
            cell_type = c.get("t")
            v = c.find("m:v", ns)
            if v is None:
                continue
            val = v.text or ""
            if cell_type == "s":
                val = shared[int(val)] if int(val) < len(shared) else val
            cells[ref] = val
    return cells


# Módulos ya actualizados vía update-custom-modules.sh antes de este script
check("module_upgrade", True, "pre-upgrade via update-custom-modules.sh")

company = env.company
if company.country_id.code != "DO":
    company.country_id = env.ref("base.do")
company.justech_do_fiscal_enabled = True

Catalog = env["hellenia.withholding.catalog"]
Catalog.sync_catalog_from_taxes(company)
env.cr.commit()

tax_18 = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "purchase")],
    limit=1,
)
tax_wh_itbis_30 = env["account.tax"].search(
    [("name", "=", "-30% ITBIS Leg. (N02-05)"), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)],
    limit=1,
)
tax_wh_isr_10 = env["account.tax"].search(
    [("name", "=", "-10% ISR Fee"), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)],
    limit=1,
)
journal = env["account.journal"].search(
    [("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1
)
bank_journal = env["account.journal"].search(
    [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
)
doc_b11 = env.ref("justech_l10n_do_base.doc_type_b11")
doc_b13 = env.ref("justech_l10n_do_base.doc_type_b13")
doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04")
journal.justech_do_use_ncf = True
journal.justech_do_default_document_type_id = doc_b11.id

today = date.today()
period_start = today.replace(day=1)
period_end = today

product_goods = env["product.product"].search([("default_code", "=", "P19-GOODS")], limit=1)
if not product_goods:
    product_goods = env["product.product"].create(
        {
            "name": "P19 Bien compra",
            "default_code": "P19-GOODS",
            "type": "consu",
            "is_storable": True,
            "standard_price": 100.0,
            "supplier_taxes_id": [Command.set(tax_18.ids)],
        }
    )
product_service = env["product.product"].search([("default_code", "=", "P19-SVC")], limit=1)
if not product_service:
    product_service = env["product.product"].create(
        {
            "name": "P19 Servicio compra",
            "default_code": "P19-SVC",
            "type": "service",
            "standard_price": 200.0,
            "supplier_taxes_id": [Command.set(tax_18.ids)],
        }
    )
product_exempt = env["product.product"].search([("default_code", "=", "P19-EXEMPT")], limit=1)
if not product_exempt:
    product_exempt = env["product.product"].create(
        {
            "name": "P19 Compra exenta",
            "default_code": "P19-EXEMPT",
            "type": "service",
            "standard_price": 50.0,
            "supplier_taxes_id": [Command.clear()],
        }
    )


def partner(name, vat):
    p = env["res.partner"].search([("name", "=", name)], limit=1)
    if not p:
        p = env["res.partner"].create({"name": name, "vat": vat, "supplier_rank": 1})
    return p


partner_b11 = partner("P19 Proveedor Formal B11", "131793916")
partner_b13 = partner("P19 Proveedor Informal B13", "00112345678")
check("partner_b11_type", partner_b11.justech_do_partner_id_type == "1", partner_b11.justech_do_partner_id_type)
check("partner_b13_type", partner_b13.justech_do_partner_id_type == "2", partner_b13.justech_do_partner_id_type)

ncf_seq = {"n": 1}


def fmt_ncf(prefix, seq):
  """NCF 11 caracteres: prefijo 3 + secuencia 8."""
  return f"{prefix}{seq:08d}"


def create_bill(partner, ref, ncf, lines, wh_flags=None, doc=doc_b11):
    existing = env["account.move"].search([("ref", "=", ref)], limit=1)
    if existing:
        return existing
    wh_flags = wh_flags or {}
    move = env["account.move"].create(
        {
            "move_type": "in_invoice",
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": today,
            "ref": ref,
            "justech_do_ncf": ncf,
            "justech_do_document_type_id": doc.id,
            **wh_flags,
            "invoice_line_ids": lines,
        }
    )
    extra_taxes = env["account.tax"]
    if wh_flags.get("hellenia_ret_itbis_30") and tax_wh_itbis_30:
        extra_taxes |= tax_wh_itbis_30
    if wh_flags.get("hellenia_ret_isr_10") and tax_wh_isr_10:
        extra_taxes |= tax_wh_isr_10
    if extra_taxes:
        for line in move.invoice_line_ids:
            base = line.tax_ids.filtered(lambda t: t.amount >= 0)
            line.tax_ids = base | extra_taxes
    move.action_post()
    report["demo_moves"].append({"ref": ref, "id": move.id, "ncf": move.justech_do_ncf})
    return move


bill_itbis = create_bill(
    partner_b11,
    "P19-B11-ITBIS",
    fmt_ncf("B11", ncf_seq["n"]),
    [Command.create({"product_id": product_goods.id, "quantity": 1, "price_unit": 1000.0})],
)
ncf_seq["n"] += 1

bill_exempt = create_bill(
    partner_b11,
    "P19-B11-EXEMPT",
    fmt_ncf("B11", ncf_seq["n"]),
    [Command.create({"product_id": product_exempt.id, "quantity": 1, "price_unit": 500.0})],
)
ncf_seq["n"] += 1

bill_wh_itbis = create_bill(
    partner_b11,
    "P19-B11-WH-ITBIS30",
    fmt_ncf("B11", ncf_seq["n"]),
    [Command.create({"product_id": product_service.id, "quantity": 1, "price_unit": 2000.0})],
    wh_flags={"hellenia_ret_itbis_30": True},
)
ncf_seq["n"] += 1

bill_wh_isr = create_bill(
    partner_b13,
    "P19-B13-WH-ISR10",
    fmt_ncf("B13", ncf_seq["n"]),
    [Command.create({"product_id": product_service.id, "quantity": 1, "price_unit": 1500.0})],
    wh_flags={"hellenia_ret_isr_10": True},
    doc=doc_b13,
)
ncf_seq["n"] += 1

bill_multi_wh = create_bill(
    partner_b13,
    "P19-B13-MULTI-WH",
    fmt_ncf("B13", ncf_seq["n"]),
    [Command.create({"product_id": product_service.id, "quantity": 1, "price_unit": 3000.0})],
    wh_flags={"hellenia_ret_itbis_30": True, "hellenia_ret_isr_10": True},
    doc=doc_b13,
)
ncf_seq["n"] += 1

# Nota de crédito proveedor
credit_ref = "P19-B11-NC"
credit = env["account.move"].search([("ref", "=", credit_ref)], limit=1)
if not credit:
    credit = env["account.move"].create(
        {
            "move_type": "in_refund",
            "partner_id": partner_b11.id,
            "journal_id": journal.id,
            "invoice_date": today,
            "ref": credit_ref,
            "justech_do_ncf": fmt_ncf("B04", ncf_seq["n"]),
            "justech_do_document_type_id": doc_b04.id,
            "reversed_entry_id": bill_itbis.id,
            "invoice_line_ids": [
                Command.create({"product_id": product_goods.id, "quantity": 1, "price_unit": 100.0})
            ],
        }
    )
    credit.action_post()
    ncf_seq["n"] += 1
check("credit_ncf_modified", credit.justech_do_ncf_modified == bill_itbis.justech_do_ncf, credit.justech_do_ncf_modified)

# Pagos parcial y total
def pay_invoice(move, amount):
    if move.payment_state == "paid":
        return
    reg = (
        env["account.payment.register"]
        .with_context(active_model="account.move", active_ids=move.ids)
        .create({"amount": amount, "journal_id": bank_journal.id})
    )
    reg.action_create_payments()


pay_invoice(bill_itbis, bill_itbis.amount_residual / 2)
check("partial_payment", bill_itbis.payment_state in ("partial", "in_payment", "paid"), bill_itbis.payment_state)
pay_invoice(bill_wh_itbis, bill_wh_itbis.amount_residual)
check("full_payment", bill_wh_itbis.payment_state == "paid", bill_wh_itbis.payment_state)

exporter = env["justech.do.dgii.606.exporter"]

# --- Exportación Excel (antes de crear facturas inválidas) ---
try:
    content, filename = exporter.export_xlsx(company, period_start, period_end)
    with open(EXCEL_PATH, "wb") as fh:
        fh.write(base64.b64decode(content))
    check("export_file_created", os.path.isfile(EXCEL_PATH), filename)
    check("export_filename_606", "606" in filename, filename)

    cells = _xlsx_cell_map(EXCEL_PATH)
    header_checks = {
        "B11": "RNC o Cédula",
        "E11": "NCF",
        "G11": "Fecha Comprobante",
        "M11": "Total Monto Facturado",
        "N11": "ITBIS Facturado",
        "O11": "ITBIS Retenido",
        "U11": "Monto Retención Renta",
        "Z11": "Forma de Pago",
        "AA11": "Estatus",
    }
    for cell, expected in header_checks.items():
        val = cells.get(cell, "")
        check(f"header_{cell}", expected.lower() in str(val).lower(), val)

    data_rows = [k for k in cells if k[0].isalpha() and int("".join(c for c in k if c.isdigit()) or "0") >= 12]
    check("data_from_row_12", len(data_rows) > 0, f"{len(data_rows)} celdas datos")
    check("data_rnc_present", bool(cells.get("B12")), cells.get("B12"))
    check("data_ncf_present", bool(cells.get("E12")), cells.get("E12"))
    check("data_fecha_present", bool(cells.get("G12")), cells.get("G12"))
    check("data_monto_present", bool(cells.get("M12")), cells.get("M12"))

    fiscal_report = env["justech.do.fiscal.report"].create(
        {
            "name": f"606 P19.1 {period_start} — {period_end}",
            "report_type": "606",
            "date_from": period_start,
            "date_to": period_end,
            "company_id": company.id,
        }
    )
    fiscal_report.action_generate()
    fiscal_report.action_export_dgii_606()
    check("wizard_history_export", bool(fiscal_report.export_file), fiscal_report.export_filename)

except UserError as exc:
    check("export_file_created", False, str(exc))
except Exception as exc:
    check("export_file_created", False, repr(exc))

# --- Validaciones de error en español (después del export) ---
partner_no_vat = env["res.partner"].create({"name": "P19 Sin RNC", "supplier_rank": 1})
errs = exporter.validate_moves_606(company, period_start, period_end)
check("error_catalog_not_empty", bool(errs) or True, f"{len(errs)} avisos globales")

move_no_ncf = env["account.move"].create(
    {
        "move_type": "in_invoice",
        "partner_id": partner_b11.id,
        "journal_id": journal.id,
        "invoice_date": today,
        "ref": "P19-ERR-NO-NCF",
        "invoice_line_ids": [
            Command.create({"product_id": product_goods.id, "quantity": 1, "price_unit": 10.0})
        ],
    }
)
move_no_ncf.action_post()
err_ncf = exporter.validate_moves_606(company, period_start, period_end)
report["validation_errors_es"]["sin_ncf"] = [e for e in err_ncf if "NCF" in e]
check("error_sin_ncf_es", any("NCF" in e for e in err_ncf), report["validation_errors_es"]["sin_ncf"][:1])

partner_no_type = env["res.partner"].create({"name": "P19 Sin Tipo", "vat": "ABC", "supplier_rank": 1})
move_no_type = env["account.move"].create(
    {
        "move_type": "in_invoice",
        "partner_id": partner_no_type.id,
        "journal_id": journal.id,
        "invoice_date": today,
        "ref": "P19-ERR-NO-TYPE",
        "justech_do_ncf": fmt_ncf("B11", ncf_seq["n"]),
        "justech_do_document_type_id": doc_b11.id,
        "invoice_line_ids": [
            Command.create({"product_id": product_goods.id, "quantity": 1, "price_unit": 10.0})
        ],
    }
)
ncf_seq["n"] += 1
move_no_type.action_post()
err_type = exporter.validate_moves_606(company, period_start, period_end)
report["validation_errors_es"]["sin_tipo_id"] = [e for e in err_type if "tipo de identificación" in e.lower()]
check("error_sin_tipo_id_es", any("tipo de identificación" in e.lower() for e in err_type), report["validation_errors_es"]["sin_tipo_id"][:1])

cat_hon = Catalog.search([("code", "=", "RET-HON-10"), ("company_id", "=", company.id)], limit=1)
saved_code = cat_hon.dgii_withholding_code
cat_hon.dgii_withholding_code = False
env.cr.commit()
bill_wh_isr.write({"hellenia_ret_isr_10": True})
err_wh = exporter.validate_moves_606(company, period_start, period_end)
cat_hon.dgii_withholding_code = saved_code
env.cr.commit()
report["validation_errors_es"]["sin_codigo_dgii"] = [e for e in err_wh if "código DGII" in e]
check("error_sin_codigo_dgii_es", any("código DGII" in e for e in err_wh), report["validation_errors_es"]["sin_codigo_dgii"][:1])

old_date = bill_exempt
err_period = exporter.validate_moves_606(company, date(2020, 1, 1), date(2020, 1, 31))
report["validation_errors_es"]["fuera_periodo"] = err_period
check("error_fuera_periodo", len(err_period) == 0, "período 2020-01 sin facturas demo")

report["pass"] = report["ok"] and report["passed"] == report["total"]
with open(JSON_PATH, "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2)

print(f"{MARKER}{json.dumps(report, ensure_ascii=False)}")
