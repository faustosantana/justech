# -*- coding: utf-8 -*-
"""Mixin compartido — datos del Conduce de Entrega Justech."""
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools import format_datetime, is_html_empty


class JtDeliveryReportMixin(models.AbstractModel):
    _name = "jt.delivery.report.mixin"
    _description = "Justech Conduce de Entrega — datos para QWeb"

    jt_delivery_note_count = fields.Integer(
        string="Conduces",
        compute="_compute_jt_delivery_ui",
    )
    # Alias Fase 26D — vistas en BD pueden referenciarlo hasta actualizar el módulo.
    jt_delivery_picking_count = fields.Integer(
        string="Conduces (legacy)",
        compute="_compute_jt_delivery_ui",
    )
    jt_delivery_stat_label = fields.Char(
        string="Etiqueta Conduce",
        compute="_compute_jt_delivery_ui",
    )

    def _jt_delivery_note_records(self):
        """Conduces vinculados — sobreescribir en sale.order / account.move / stock.picking."""
        return self.env["justech.delivery.note"]

    @api.depends()
    def _compute_jt_delivery_ui(self):
        for rec in self:
            notes = rec._jt_delivery_note_records().filtered(lambda n: n.state != "cancel")
            count = len(notes)
            rec.jt_delivery_note_count = count
            rec.jt_delivery_picking_count = count
            if count == 1:
                rec.jt_delivery_stat_label = _("Conduce")
            else:
                rec.jt_delivery_stat_label = _("Conduces") if count else _("Conduce")

    def _jt_delivery_outgoing_pickings(self):
        return self.env["stock.picking"]

    def _jt_post_delivery_note_origin_chatter(self, note, created):
        self.ensure_one()
        now_utc = fields.Datetime.now()
        if created:
            body = _(
                "Conduce de Entrega %(name)s creado por %(user)s el %(date)s.",
                name=note.name,
                user=self.env.user.display_name,
                date=format_datetime(self.env, now_utc),
            )
        else:
            body = _(
                "Conduce de Entrega %(name)s reimpreso por %(user)s el %(date)s.",
                name=note.name,
                user=self.env.user.display_name,
                date=format_datetime(self.env, now_utc),
            )
        self.message_post(body=body, subtype_xmlid="mail.mt_note")

    def action_jt_view_delivery_notes(self):
        self.ensure_one()
        notes = self._jt_delivery_note_records().filtered(lambda n: n.state != "cancel")
        action = self.env.ref("justech_report_design.action_justech_delivery_note").read()[0]
        action["domain"] = [("id", "in", notes.ids)]
        if len(notes) == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = notes.id
        return action

    def action_jt_view_delivery_pickings(self):
        """Compatibilidad Fase 26D — redirige al listado de conduces."""
        return self.action_jt_view_delivery_notes()

    def action_jt_create_delivery_conduce(self):
        raise NotImplementedError

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

    def _jt_delivery_delivery_partners(self, partner):
        """Hijos de entrega del contacto (dirección separada en perfil)."""
        if not partner:
            return self.env["res.partner"]
        delivery = partner.child_ids.filtered(lambda c: c.type == "delivery")
        if delivery:
            return delivery
        return self.env["res.partner"]

    def _jt_delivery_expand_partner_candidates(self, *partners):
        """Orden: cada partner y sus contactos de entrega."""
        candidates = []
        seen = set()
        for partner in partners:
            if not partner:
                continue
            for cand in (partner, *self._jt_delivery_delivery_partners(partner)):
                if cand.id not in seen:
                    seen.add(cand.id)
                    candidates.append(cand)
        return candidates

    def _jt_delivery_warehouse_from_picking(self, picking):
        """Almacén real; nunca el nombre legal de la empresa como etiqueta."""
        if not picking:
            return "—"
        company = (picking.company_id.name or "").strip()
        wh = picking.picking_type_id.warehouse_id if picking.picking_type_id else False
        if wh:
            name = (wh.name or "").strip()
            code = (wh.code or "").strip()
            if code:
                return code
            if name and name != company:
                return name
        if picking.location_id:
            complete = (
                picking.location_id.complete_name
                or picking.location_id.display_name
                or ""
            ).strip()
            if complete:
                root = complete.split("/")[0].strip()
                if root and root != company:
                    return root
            loc_name = (picking.location_id.name or "").strip()
            if loc_name:
                return loc_name
        return "—"

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
