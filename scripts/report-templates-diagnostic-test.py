# -*- coding: utf-8 -*-
"""Inventario reportes QWeb — sale / account / purchase / stock (solo TEST)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/report-templates-diagnostic"
os.makedirs(OUT_DIR, exist_ok=True)

STANDARD_MODULES = {
    "sale", "account", "purchase", "stock", "web", "snailmail",
    "sale_management", "account_payment", "account_followup",
    "sale_pdf_quote_builder", "purchase_stock", "stock_delivery",
}

TARGET_REPORT_KEYS = [
    # Cotización / Orden venta
    ("sale.report_saleorder", "sale.order", "Cotización / Orden venta (wrapper)"),
    ("sale.report_saleorder_raw", "sale.order", "Cotización / Orden venta (raw)"),
    ("sale.report_saleorder_document", "sale.order", "Cotización / Orden venta (documento)"),
    # Factura / NC
    ("account.report_invoice", "account.move", "Factura (wrapper)"),
    ("account.report_invoice_with_payments", "account.move", "Factura con pagos"),
    ("account.report_invoice_document", "account.move", "Factura (documento)"),
    # Compra / RFQ
    ("purchase.report_purchaseorder", "purchase.order", "Orden compra (wrapper)"),
    ("purchase.report_purchaseorder_document", "purchase.order", "Orden compra (documento)"),
    ("purchase.report_purchasequotation", "purchase.order", "RFQ (wrapper)"),
    ("purchase.report_purchasequotation_document", "purchase.order", "RFQ (documento)"),
    # Pagos
    ("account.report_payment_receipt", "account.payment", "Recibo de pago (wrapper)"),
    ("account.report_payment_receipt_document", "account.payment", "Recibo de pago (documento)"),
    # Delivery
    ("stock.report_deliveryslip", "stock.picking", "Albarán entrega (wrapper)"),
    ("stock.report_delivery_document", "stock.picking", "Albarán entrega (documento)"),
    ("stock.report_picking", "stock.picking", "Operación stock / picking"),
]

LAYOUT_KEYS = [
    "web.external_layout",
    "web.external_layout_standard",
    "web.external_layout_boxed",
    "web.external_layout_bold",
    "web.external_layout_striped",
    "web.html_container",
    "web.report_layout",
    "web.basic_layout",
    "web.minimal_layout",
]


def is_custom_module(module_name):
    if not module_name:
        return False
    return module_name not in STANDARD_MODULES and not module_name.startswith("l10n_")


def view_record(view):
    if not view:
        return None
    return {
        "id": view.id,
        "xml_id": view.get_external_id().get(view.id, ""),
        "key": view.key,
        "name": view.name,
        "module": view.key.split(".")[0] if view.key and "." in view.key else "",
        "inherit_id": view.inherit_id.id if view.inherit_id else None,
        "inherit_key": view.inherit_id.key if view.inherit_id else None,
        "priority": view.priority,
        "customized": is_custom_module(view.key.split(".")[0] if view.key else ""),
    }


def inherit_chain(view):
    chain = []
    current = view
    seen = set()
    while current and current.id not in seen:
        seen.add(current.id)
        chain.append(view_record(current))
        current = current.inherit_id
    chain.reverse()
    return chain


def inherit_children(view, depth=0, max_depth=8):
    if depth > max_depth or not view:
        return []
    children = env["ir.ui.view"].search([("inherit_id", "=", view.id)], order="priority, id")
    result = []
    for child in children:
        rec = view_record(child)
        rec["children"] = inherit_children(child, depth + 1, max_depth)
        result.append(rec)
    return result


def classify_view(view):
    if not view:
        return "missing"
    mod = view.key.split(".")[0] if view.key and "." in view.key else ""
    inherits = inherit_chain(view)
    custom_in_chain = [v for v in inherits if v and v.get("customized")]
    if custom_in_chain:
        return "customized"
    if view.inherit_id:
        return "inherited_standard"
    if mod in STANDARD_MODULES:
        return "original_standard"
    return "custom_module"


def find_report_action(report_name):
    return env["ir.actions.report"].search([("report_name", "=", report_name)], limit=1)


def pdf_pages(path):
    try:
        out = subprocess.check_output(["pdfinfo", path], stderr=subprocess.DEVNULL, timeout=15)
        for line in out.decode().splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return None


def try_render_pdf(report_name, model, domain):
    action = env["ir.actions.report"].search([("report_name", "=", report_name)], limit=1)
    if not action:
        return {"status": "no_action", "detail": report_name}
    rec = env[model].search(domain, limit=1)
    if not rec:
        return {"status": "no_record", "model": model, "domain": str(domain)}
    try:
        pdf_bytes, _ = env["ir.actions.report"]._render_qweb_pdf(report_name, rec.ids)
        safe = report_name.replace(".", "_")
        fname = f"sample_{safe}.pdf"
        path = os.path.join(OUT_DIR, fname)
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        return {
            "status": "ok",
            "record": rec.display_name,
            "record_id": rec.id,
            "file": fname,
            "size_bytes": len(pdf_bytes),
            "pages": pdf_pages(path),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)[:300]}


report = {
    "phase": "report-templates-diagnostic",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "environment": "TEST ONLY — no producción",
    "module_installed": bool(
        env["ir.module.module"].search([("name", "=", "justech_report_templates_test"), ("state", "=", "installed")])
    ),
    "reports": {},
    "layouts": {},
    "custom_inherits_summary": [],
    "all_custom_report_views": [],
    "sample_pdfs": {},
    "redesign_notes": {
        "approach": "Usar reporte independiente (web.html_container + article) o herencia primary=True",
        "avoid": ["xpath frágiles sobre texto", "web.external_layout para diseños custom completos"],
        "keep": ["ir.actions.report propio por documento", "paperformat dedicado"],
    },
}

# Instalar módulo test si no está
mod = env["ir.module.module"].search([("name", "=", "justech_report_templates_test")], limit=1)
if mod.state != "installed":
    mod.button_immediate_install()
    env.cr.commit()

for key, model, label in TARGET_REPORT_KEYS:
    view = env["ir.ui.view"].search([("key", "=", key), ("type", "=", "qweb")], limit=1)
    action = find_report_action(key)
    children = inherit_children(view) if view else []
    custom_children = []

    def collect_custom(nodes):
        for n in nodes:
            if n.get("customized"):
                custom_children.append(n)
            collect_custom(n.get("children", []))

    collect_custom(children)

    entry = {
        "label": label,
        "report_name": key,
        "model": model,
        "xml_id_action": action.get_external_id().get(action.id, "") if action else "",
        "action_name": action.name if action else "",
        "paperformat": action.paperformat_id.name if action and action.paperformat_id else "",
        "view": view_record(view),
        "classification": classify_view(view),
        "inherit_chain_ancestors": inherit_chain(view),
        "inherit_children": children,
        "custom_modifiers": custom_children,
        "is_customized": bool(custom_children) or classify_view(view) == "customized",
    }
    report["reports"][key] = entry

    for c in custom_children:
        report["custom_inherits_summary"].append({
            "target_report": key,
            "custom_view_key": c.get("key"),
            "custom_xml_id": c.get("xml_id"),
            "module": c.get("module"),
        })

for layout_key in LAYOUT_KEYS:
    view = env["ir.ui.view"].search([("key", "=", layout_key), ("type", "=", "qweb")], limit=1)
    if view:
        report["layouts"][layout_key] = {
            "view": view_record(view),
            "classification": classify_view(view),
            "inherit_children": inherit_children(view),
        }

# Todas las vistas QWeb custom que tocan reportes
custom_views = env["ir.ui.view"].search([
    ("type", "=", "qweb"),
    ("key", "ilike", ".report_%"),
])
for v in custom_views:
    mod = v.key.split(".")[0] if v.key else ""
    if is_custom_module(mod):
        top = v
        while top.inherit_id:
            top = top.inherit_id
        report["all_custom_report_views"].append({
            "key": v.key,
            "xml_id": v.get_external_id().get(v.id, ""),
            "inherits": v.inherit_id.key if v.inherit_id else None,
            "root_standard_key": top.key,
            "module": mod,
            "name": v.name,
        })

# PDFs muestra (con personalizaciones activas — refleja lo que imprime TEST hoy)
sample_specs = [
    ("sale.report_saleorder", "sale.order", [("state", "in", ["draft", "sent"])]),
    ("sale.report_saleorder", "sale.order", [("state", "in", ["sale", "done"])]),
    ("account.report_invoice", "account.move", [("move_type", "=", "out_invoice"), ("state", "=", "posted")]),
    ("account.report_invoice", "account.move", [("move_type", "=", "out_refund"), ("state", "=", "posted")]),
    ("purchase.report_purchaseorder", "purchase.order", [("state", "in", ["purchase", "done"])]),
    ("purchase.report_purchasequotation", "purchase.order", [("state", "in", ["draft", "sent"])]),
    ("account.report_payment_receipt", "account.payment", [("state", "=", "posted")]),
    ("stock.report_deliveryslip", "stock.picking", [("picking_type_code", "=", "outgoing"), ("state", "=", "done")]),
]

for spec_key, model, domain in sample_specs:
    label = f"{spec_key}__{domain[0][0]}_{domain[0][1]}"
    report["sample_pdfs"][label] = try_render_pdf(spec_key, model, domain)

report["summary"] = {
    "total_targets": len(TARGET_REPORT_KEYS),
    "customized_count": sum(1 for r in report["reports"].values() if r["is_customized"]),
    "original_standard_count": sum(
        1 for r in report["reports"].values() if r["classification"] == "original_standard"
    ),
    "custom_modules_touching_reports": sorted(set(
        v["module"] for v in report["all_custom_report_views"]
    )),
    "pdfs_generated": sum(1 for p in report["sample_pdfs"].values() if p.get("status") == "ok"),
}

out_json = os.path.join(OUT_DIR, "report_templates_diagnostic.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("REPORT_TEMPLATES_DIAG:" + json.dumps(report["summary"], indent=2, ensure_ascii=False))
