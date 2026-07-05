# -*- coding: utf-8 -*-
"""Genera sesión HTTP + URLs para capturas UI Fase 27."""
from __future__ import annotations

import json

DB = env.cr.dbname
user = env["res.users"].search([("login", "=", "admin"), ("share", "=", False)], limit=1) or env.user
base = env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
env_name = "prod" if DB == "hellenia_prod" else "test"

doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02")
partner = env["res.partner"].search(
    [("justech_do_default_document_type_id", "=", doc_b02.id)], limit=1
)
if not partner:
    partner = env["res.partner"].create(
        {"name": "UI P27 Cliente B02", "justech_do_default_document_type_id": doc_b02.id}
    )

so = env["sale.order"].search([("partner_id", "=", partner.id)], limit=1, order="id desc")
if not so:
    product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
    so = env["sale.order"].create(
        {
            "partner_id": partner.id,
            "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 1, "price_unit": 100.0})],
        }
    )

inv = env["account.move"].search(
    [("partner_id", "=", partner.id), ("move_type", "=", "out_invoice")], limit=1, order="id desc"
)

from odoo import http

root = http.root
session = root.session_store.new()
session.update(
    {
        "db": DB,
        "uid": user.id,
        "login": user.login,
        "session_token": user._compute_session_token(session.sid),
    }
)
root.session_store.save(session)

out = {
    "database": DB,
    "session_id": session.sid,
    "partner_id": partner.id,
    "partner_url": f"{base}/odoo/action-contacts.action_contacts/{partner.id}",
    "so_url": f"{base}/odoo/action-sale.action_orders/{so.id}",
    "invoice_url": f"{base}/odoo/action-account.action_move_out_invoice_type/{inv.id}" if inv else None,
    "partner_doc_type": partner.justech_do_default_document_type_id.display_name,
    "so_doc_type": so.justech_do_document_type_id.display_name if so.justech_do_document_type_id else None,
}
path = f"/tmp/odoo_{env_name}_session_phase27_doc_type.json"
with open(path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
print(json.dumps(out, ensure_ascii=False))
