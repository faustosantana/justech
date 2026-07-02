# -*- coding: utf-8 -*-
"""
Comparación PDFs reportes — Grupo A (custom) vs Grupo B (Odoo puro).
Solo hellenia_test. Backup + restore automático.
"""
from __future__ import annotations

import json
import os
import subprocess
import traceback
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

REF = "P23-REPORT-CMP"
OUT_DIR = "/tmp/report-templates-comparison"
BACKUP_DIR = os.path.join(OUT_DIR, "backup")
GROUP_A = os.path.join(OUT_DIR, "group_a_custom")
GROUP_B = os.path.join(OUT_DIR, "group_b_pure_odoo")
for d in (OUT_DIR, BACKUP_DIR, GROUP_A, GROUP_B):
    os.makedirs(d, exist_ok=True)

CUSTOM_REPORT_MODULES = ["hellenia_ux", "hellenia_reports"]
CUSTOM_VIEW_PREFIXES = ("hellenia_reports.", "hellenia_account.", "justech_l10n_do_ncf.")
REPORT_ACTIONS = [
    ("sale.action_report_saleorder", "sale.report_saleorder"),
    ("account.account_invoices", "account.report_invoice"),
    ("purchase.action_report_purchase_order", "purchase.report_purchaseorder"),
    ("purchase.report_purchase_quotation", "purchase.report_purchasequotation"),
    ("account.action_report_payment_receipt", "account.report_payment_receipt"),
    ("stock.action_report_delivery", "stock.report_deliveryslip"),
]

PDF_SPECS = [
    ("cotizacion", "sale.report_saleorder", "sale.order", [("state", "in", ["draft", "sent"])]),
    ("factura", "account.report_invoice", "account.move", [("move_type", "=", "out_invoice"), ("state", "=", "posted")]),
    ("orden_compra", "purchase.report_purchaseorder", "purchase.order", [("state", "in", ["purchase", "done"])]),
    ("rfq", "purchase.report_purchasequotation", "purchase.order", [("state", "in", ["draft", "sent", "to approve"])]),
    ("recibo_pago", "account.report_payment_receipt", "account.payment", [("state", "=", "posted")]),
    ("albaran", "stock.report_deliveryslip", "stock.picking", [("picking_type_id.code", "=", "outgoing"), ("state", "=", "done")]),
]

report = {
    "phase": "report-templates-comparison-ab",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "ref": REF,
    "test_records": {},
    "backup": {},
    "group_a": {},
    "group_b": {},
    "restore": {},
    "pass": True,
    "errors": [],
}


def log_error(msg):
    report["errors"].append(msg)
    report["pass"] = False


def pdf_pages(path):
    try:
        out = subprocess.check_output(["pdfinfo", path], stderr=subprocess.DEVNULL, timeout=15)
        for line in out.decode().splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return None


def module_states():
    mods = env["ir.module.module"].search([("name", "in", CUSTOM_REPORT_MODULES + ["hellenia_account", "justech_l10n_do_ncf"])])
    return {m.name: m.state for m in mods}


def backup_state():
    company = env.company
    layout_xml = ""
    if company.external_report_layout_id:
        layout_xml = company.external_report_layout_id.get_external_id().get(company.external_report_layout_id.id, "")
    paperformats = {}
    for xmlid, rname in REPORT_ACTIONS:
        try:
            act = env.ref(xmlid)
            pf = act.paperformat_id
            paperformats[xmlid] = {
                "id": pf.id if pf else False,
                "xml_id": pf.get_external_id().get(pf.id, "") if pf else "",
            }
        except Exception:
            paperformats[xmlid] = {"id": False, "xml_id": ""}
    custom_views = env["ir.ui.view"].search([
        ("type", "=", "qweb"),
        "|", "|",
        ("key", "like", "hellenia_reports.%"),
        ("key", "like", "hellenia_account.%"),
        ("key", "like", "justech_l10n_do_ncf.%"),
    ])
    view_states = {v.id: {"key": v.key, "active": v.active, "xml_id": v.get_external_id().get(v.id, "")} for v in custom_views}
    backup = {
        "modules": module_states(),
        "company_layout_xml_id": layout_xml,
        "company_layout_view_id": company.external_report_layout_id.id if company.external_report_layout_id else False,
        "paperformats": paperformats,
        "view_states": view_states,
    }
    path = os.path.join(BACKUP_DIR, "restore_backup.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)
    report["backup"] = {"file": path, "modules": backup["modules"], "views_count": len(view_states)}
    return backup


def restore_state(backup):
    result = {"ok": True, "steps": []}
    try:
        for mod_name in ["hellenia_reports", "hellenia_ux"]:
            mod = env["ir.module.module"].search([("name", "=", mod_name)], limit=1)
            if mod and backup["modules"].get(mod_name) == "installed" and mod.state != "installed":
                mod.button_immediate_install()
                result["steps"].append(f"reinstalled_{mod_name}")
            elif mod and mod.state == "installed" and mod_name == "hellenia_reports":
                mod.button_immediate_upgrade()
                result["steps"].append("upgraded_hellenia_reports")
        env.cr.commit()

        for vid, info in backup.get("view_states", {}).items():
            v = env["ir.ui.view"].browse(int(vid)).exists()
            if v:
                v.write({"active": info["active"]})
        result["steps"].append("views_restored")

        company = env.company
        layout_xml = backup.get("company_layout_xml_id")
        if layout_xml:
            layout = env.ref(layout_xml, raise_if_not_found=False)
            if layout:
                company.write({"external_report_layout_id": layout.id})
        result["steps"].append("company_layout_restored")

        for xmlid, pf_info in backup.get("paperformats", {}).items():
            try:
                act = env.ref(xmlid)
                pf_id = False
                if isinstance(pf_info, dict):
                    pf_xml = pf_info.get("xml_id")
                    if pf_xml:
                        pf = env.ref(pf_xml, raise_if_not_found=False)
                        pf_id = pf.id if pf else False
                    elif pf_info.get("id"):
                        pf = env["report.paperformat"].browse(pf_info["id"]).exists()
                        pf_id = pf.id if pf else False
                elif pf_info:
                    pf = env["report.paperformat"].browse(pf_info).exists()
                    pf_id = pf.id if pf else False
                act.write({"paperformat_id": pf_id or False})
            except Exception:
                pass
        result["steps"].append("paperformats_restored")

        env.cr.commit()
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)[:500]
        log_error(f"restore_failed: {e}")
    report["restore"] = result


def ensure_test_records():
    company = env.company
    product = env["product.product"].search([("purchase_ok", "=", True)], limit=1) or env["product.product"].search([], limit=1)
    vendor = env["res.partner"].search([("ref", "=", REF), ("supplier_rank", ">", 0)], limit=1)
    if not vendor:
        vendor = env["res.partner"].create({"name": f"{REF} Proveedor", "ref": REF, "supplier_rank": 1, "company_type": "company"})
    tax_purchase = env["account.tax"].search([("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)], limit=1)

    rfq = env["purchase.order"].search([("partner_ref", "=", f"{REF}-RFQ")], limit=1)
    if not rfq and product:
        rfq = env["purchase.order"].create({
            "partner_id": vendor.id,
            "partner_ref": f"{REF}-RFQ",
            "date_order": date.today(),
            "order_line": [Command.create({
                "product_id": product.id,
                "product_qty": 2,
                "price_unit": 150.0,
                "tax_ids": [Command.set(tax_purchase.ids)] if tax_purchase else [],
            })],
        })
    report["test_records"]["rfq"] = {"name": rfq.name, "id": rfq.id, "state": rfq.state} if rfq else {"status": "failed"}

    pay = env["account.payment"].search([("payment_reference", "=", f"{REF}-PAY")], limit=1)
    if not pay:
        pay = env["account.payment"].search([("hellenia_payment_reference", "=", f"{REF}-PAY")], limit=1)
    if not pay:
        invoice = env["account.move"].search([
            ("move_type", "=", "out_invoice"), ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("company_id", "=", company.id),
        ], limit=1)
        journal = env["account.journal"].search([
            ("type", "in", ["bank", "cash"]), ("company_id", "=", company.id),
        ], limit=1)
        if invoice and journal:
            try:
                pay = env["account.payment"].create({
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": invoice.partner_id.id,
                    "amount": min(500.0, invoice.amount_residual),
                    "journal_id": journal.id,
                    "payment_reference": f"{REF}-PAY",
                })
                pay.action_post()
                if invoice.amount_residual and hasattr(pay, "action_validate"):
                    try:
                        pay.action_validate()
                    except Exception:
                        pass
            except Exception as e:
                pay = env["account.payment"].search([("state", "=", "posted"), ("company_id", "=", company.id)], limit=1)
                report["test_records"]["payment_note"] = f"create_failed_used_existing: {e}"[:200]
    report["test_records"]["payment"] = {"name": pay.name, "id": pay.id, "state": pay.state} if pay else {"status": "failed"}

    for key, rname, model, domain in PDF_SPECS:
        extra = []
        if model == "purchase.order" and key == "rfq":
            rec = env[model].search([("partner_ref", "=", f"{REF}-RFQ")] + extra, limit=1)
        elif model == "account.payment" and key == "recibo_pago":
            rec = pay
        else:
            rec = env[model].search(domain + [("company_id", "=", company.id)], limit=1)
        report["test_records"][f"source_{key}"] = {
            "model": model,
            "id": rec.id if rec else None,
            "name": rec.display_name if rec else None,
        }
    env.cr.commit()


def render_pdfs(group_dir, prefix, extra_domain=None):
    results = {}
    Report = env["ir.actions.report"]
    company = env.company
    for key, rname, model, domain in PDF_SPECS:
        d = list(domain)
        if model == "purchase.order" and key == "rfq":
            rec = env[model].search([("partner_ref", "=", f"{REF}-RFQ")], limit=1)
        elif model == "account.payment" and key == "recibo_pago":
            rec = env[model].search([
                "|", ("payment_reference", "=", f"{REF}-PAY"),
                ("hellenia_payment_reference", "=", f"{REF}-PAY"),
            ], limit=1) or env[model].search([("state", "=", "posted")], limit=1)
        else:
            rec = env[model].search(d + [("company_id", "=", company.id)], limit=1)
        if not rec:
            results[key] = {"status": "no_record", "report": rname}
            continue
        try:
            pdf_bytes, _ = Report._render_qweb_pdf(rname, rec.ids)
            fname = f"{prefix}_{key}.pdf"
            path = os.path.join(group_dir, fname)
            with open(path, "wb") as f:
                f.write(pdf_bytes)
            results[key] = {
                "status": "ok",
                "report": rname,
                "record": rec.display_name,
                "record_id": rec.id,
                "file": fname,
                "size_bytes": len(pdf_bytes),
                "pages": pdf_pages(path),
                "is_pdf": pdf_bytes[:4] == b"%PDF",
            }
        except Exception as e:
            results[key] = {"status": "error", "detail": str(e)[:400]}
            log_error(f"{prefix}_{key}: {e}")
    return results


def apply_pure_odoo_mode(backup):
    steps = []
    for mod_name in CUSTOM_REPORT_MODULES:
        mod = env["ir.module.module"].search([("name", "=", mod_name)], limit=1)
        if mod and mod.state == "installed":
            mod.button_immediate_uninstall()
            steps.append(f"uninstalled_{mod_name}")
    env.cr.commit()

    custom_views = env["ir.ui.view"].search([
        ("type", "=", "qweb"),
        "|", "|",
        ("key", "like", "hellenia_account.%"),
        ("key", "like", "justech_l10n_do_ncf.%"),
        ("key", "like", "hellenia_reports.%"),
    ])
    for v in custom_views:
        if v.active:
            v.write({"active": False})
    steps.append(f"deactivated_views_{len(custom_views)}")

    std_layout = env.ref("web.external_layout_standard", raise_if_not_found=False)
    if std_layout:
        env.company.write({"external_report_layout_id": std_layout.id})
        steps.append("layout_standard")

    for xmlid, _ in REPORT_ACTIONS:
        try:
            env.ref(xmlid).write({"paperformat_id": False})
        except Exception:
            pass
    steps.append("paperformats_cleared")
    env.cr.commit()
    return steps


backup = backup_state()
ensure_test_records()

try:
    report["group_a"] = {
        "label": "Personalizaciones Hellenia/Justech activas",
        "modules": module_states(),
        "pdfs": render_pdfs(GROUP_A, "A"),
    }
    env.cr.commit()

    pure_steps = apply_pure_odoo_mode(backup)
    report["group_b"] = {
        "label": "Odoo puro — hellenia_reports/ux desinstalados, herencias account/ncf desactivadas",
        "steps": pure_steps,
        "modules": module_states(),
        "pdfs": render_pdfs(GROUP_B, "B"),
    }
    env.cr.commit()
finally:
    restore_state(backup)

report["summary"] = {
    "group_a_ok": sum(1 for p in report["group_a"].get("pdfs", {}).values() if p.get("status") == "ok"),
    "group_b_ok": sum(1 for p in report["group_b"].get("pdfs", {}).values() if p.get("status") == "ok"),
    "total_docs": len(PDF_SPECS),
    "restore_ok": report["restore"].get("ok", False),
}

diag_path = os.path.join(OUT_DIR, "report_templates_diagnostic.json")
if os.path.exists("/tmp/report-templates-diagnostic/report_templates_diagnostic.json"):
    with open("/tmp/report-templates-diagnostic/report_templates_diagnostic.json", encoding="utf-8") as f:
        diag = json.load(f)
    diag["comparison_ab"] = report
    diag["updated_utc"] = datetime.now(timezone.utc).isoformat()
else:
    diag = report

with open(diag_path, "w", encoding="utf-8") as f:
    json.dump(diag, f, indent=2, ensure_ascii=False)

print("REPORT_CMP:" + json.dumps(report["summary"], indent=2, ensure_ascii=False))
