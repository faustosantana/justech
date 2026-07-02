# -*- coding: utf-8 -*-
"""Mixin compartido — datos del Conduce de Entrega Justech."""
from odoo import _, models
from odoo.tools import is_html_empty


class JtDeliveryReportMixin(models.AbstractModel):
    _name = "jt.delivery.report.mixin"
    _description = "Justech Conduce de Entrega — datos para QWeb"

    # --- helpers comunes ---

    def _jt_delivery_format_address(self, partner):
        """Dirección en una línea (legacy)."""
        lines = self._jt_delivery_format_address_lines(partner)
        if not lines:
            return "—"
        return ", ".join(lines)

    def _jt_delivery_format_address_lines(self, partner):
        """Dirección multilínea: calle, ciudad/provincia, país."""
        if not partner:
            return []
        lines = []
        street_parts = [p for p in (partner.street, partner.street2) if p]
        if street_parts:
            lines.append(", ".join(street_parts))
        city_parts = [
            p
            for p in (
                partner.city,
                partner.state_id.name if partner.state_id else "",
            )
            if p
        ]
        if city_parts:
            lines.append(" / ".join(city_parts))
        if partner.country_id and partner.country_id.name:
            # Evitar duplicar país si es la única info y ya hay ciudad
            if not lines or partner.country_id.name not in " / ".join(lines):
                lines.append(partner.country_id.name)
        return lines

    def _jt_delivery_partner_has_address(self, partner):
        if not partner:
            return False
        return bool(
            partner.street
            or partner.street2
            or partner.city
            or partner.state_id
        )

    def _jt_delivery_user_label(self, user):
        if not user:
            return "—"
        name = (user.name or "").strip()
        login = (user.login or "").lower()
        if not name:
            return "—"
        if login in ("__system__", "odoobot") or name.lower() in ("odoo bot", "odobot"):
            return "—"
        return name

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
        """Siempre mostrar bloque OBSERVACIONES."""
        self.ensure_one()
        return True

    def jt_delivery_has_observations_content(self):
        self.ensure_one()
        return not is_html_empty(self.get_jt_delivery_observations_html())

    def get_jt_delivery_shipping_address_lines(self):
        self.ensure_one()
        return self._jt_delivery_format_address_lines(
            self._jt_delivery_resolve_shipping_partner()
        )

    def _jt_delivery_resolve_shipping_partner(self):
        """Sobreescribir en cada modelo."""
        self.ensure_one()
        return False

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
