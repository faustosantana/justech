# -*- coding: utf-8 -*-
"""Mixin compartido — datos del Conduce de Entrega Justech."""
from odoo import _, models
from odoo.tools import is_html_empty


class JtDeliveryReportMixin(models.AbstractModel):
    _name = "jt.delivery.report.mixin"
    _description = "Justech Conduce de Entrega — datos para QWeb"

    # --- helpers comunes ---

    def _jt_delivery_format_address(self, partner):
        if not partner:
            return "—"
        parts = []
        if partner.street:
            parts.append(partner.street)
        if partner.street2:
            parts.append(partner.street2)
        city_parts = [
            p
            for p in (
                partner.city,
                partner.state_id.name if partner.state_id else "",
                partner.country_id.name if partner.country_id else "",
            )
            if p
        ]
        if city_parts:
            parts.append(", ".join(city_parts))
        return ", ".join(parts) if parts else "—"

    def _jt_delivery_dash(self, value):
        if not value or value in ("/", "False"):
            return "—"
        return value

    def _jt_delivery_state_label_picking(self, state):
        labels = {
            "draft": "Borrador",
            "waiting": "Esperando otra operación",
            "confirmed": "En espera",
            "assigned": "Listo",
            "done": "Validado",
            "cancel": "Cancelado",
        }
        return labels.get(state, state or "—")

    def _jt_delivery_state_label_sale(self, state):
        labels = {
            "draft": "Borrador",
            "sent": "Enviada",
            "sale": "Confirmada",
            "done": "Bloqueada",
            "cancel": "Cancelada",
        }
        return labels.get(state, state or "—")

    def _jt_delivery_state_label_invoice(self, state):
        labels = {
            "draft": "Borrador",
            "posted": "Registrada",
            "cancel": "Cancelada",
        }
        return labels.get(state, state or "—")

    def _jt_delivery_line_dict(
        self, code, description, qty_req, qty_del, uom_name, lot_serial=""
    ):
        return {
            "code": code or "—",
            "description": description or "—",
            "qty_requested": qty_req,
            "qty_delivered": qty_del,
            "uom": uom_name or "—",
            "lot_serial": lot_serial or "",
        }

    def _jt_delivery_show_lot_column(self, lines):
        return any((l.get("lot_serial") or "").strip() for l in lines)

    def get_jt_delivery_company(self):
        self.ensure_one()
        return self.company_id

    def jt_show_delivery_observations(self):
        self.ensure_one()
        return not is_html_empty(self.get_jt_delivery_observations_html())

    def get_jt_delivery_observations_html(self):
        self.ensure_one()
        return False

    def get_jt_delivery_conduce_number(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_picking_number(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_sale_order_name(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_invoice_name(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_state_display(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_date_display(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_customer_name(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_shipping_address(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_responsible_display(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_salesperson_display(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_carrier_display(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_warehouse_origin(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_destination_location(self):
        self.ensure_one()
        return "—"

    def get_jt_delivery_lines(self):
        self.ensure_one()
        return []

    def get_jt_delivery_show_lot_column(self):
        self.ensure_one()
        return self._jt_delivery_show_lot_column(self.get_jt_delivery_lines())
