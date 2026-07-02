# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "jt.delivery.report.mixin"]

    delivery_note_ids = fields.One2many(
        "justech.delivery.note",
        "picking_id",
        string="Conduces de entrega",
    )

    def _jt_delivery_related_sale_order(self):
        self.ensure_one()
        if self.sale_id:
            return self.sale_id
        if self.origin:
            so = self.env["sale.order"].search(
                [("name", "=", self.origin), ("company_id", "=", self.company_id.id)],
                limit=1,
            )
            if so:
                return so
        return self.env["sale.order"]

    def _jt_delivery_related_invoices(self):
        self.ensure_one()
        so = self._jt_delivery_related_sale_order()
        if so:
            return so.invoice_ids.filtered(
                lambda m: m.move_type == "out_invoice" and m.state == "posted"
            )
        return self.env["account.move"]

    def get_jt_delivery_conduce_number(self):
        return self._jt_delivery_dash(self.name)

    def get_jt_delivery_picking_number(self):
        return self._jt_delivery_dash(self.name)

    def get_jt_delivery_sale_order_name(self):
        so = self._jt_delivery_related_sale_order()
        return self._jt_delivery_dash(so.name if so else False)

    def get_jt_delivery_invoice_name(self):
        invs = self._jt_delivery_related_invoices()
        if not invs:
            return "—"
        names = invs.mapped("name")
        return ", ".join(n for n in names if n) or "—"

    def get_jt_delivery_state_display(self):
        return self._jt_delivery_state_label_picking(self.state)

    def get_jt_delivery_date_display(self):
        dt = self.date_done or self.scheduled_date
        if not dt:
            return "—"
        return dt.strftime("%d/%m/%Y")

    def get_jt_delivery_customer_name(self):
        return self.partner_id.name if self.partner_id else "—"

    def get_jt_delivery_shipping_address(self):
        lines = self.get_jt_delivery_shipping_address_lines()
        return ", ".join(lines) if lines else "—"

    def _jt_delivery_resolve_shipping_partner(self):
        self.ensure_one()
        so = self._jt_delivery_related_sale_order()
        raw = []
        if self.partner_id:
            raw.append(self.partner_id)
        if so and so.partner_shipping_id:
            raw.append(so.partner_shipping_id)
        if so and so.partner_id:
            raw.append(so.partner_id)
        candidates = self._jt_delivery_expand_partner_candidates(*raw)
        for partner in candidates:
            if self._jt_delivery_partner_has_address(partner):
                return partner
        return candidates[0] if candidates else self.env["res.partner"]

    def get_jt_delivery_responsible_display(self):
        return self._jt_delivery_user_label(self.user_id)

    def get_jt_delivery_salesperson_display(self):
        so = self._jt_delivery_related_sale_order()
        salesperson = so.user_id if so else False
        return self._jt_delivery_user_label(salesperson)

    def get_jt_delivery_carrier_display(self):
        if self._fields.get("carrier_id") and self.carrier_id:
            return self.carrier_id.name
        return "—"

    def get_jt_delivery_warehouse_origin(self):
        self.ensure_one()
        return self._jt_delivery_warehouse_from_picking(self)

    def get_jt_delivery_destination_location(self):
        return self.location_dest_id.display_name if self.location_dest_id else "—"

    def get_jt_delivery_observations_html(self):
        return self.note or False

    def get_jt_delivery_lines(self):
        self.ensure_one()
        lines = []
        moves = self.move_ids.filtered(
            lambda m: m.product_id
            and m.state != "cancel"
            and not getattr(m, "scrapped", False)
        )
        for move in moves.sorted(key=lambda m: (m.sequence, m.id)):
            product = move.product_id
            code = product.default_code or ""
            desc = move.description_picking or product.display_name
            uom = move.product_uom.name if move.product_uom else ""
            qty_req = move.product_uom_qty
            detail_lines = move.move_line_ids.filtered(lambda l: l.quantity > 0)
            if detail_lines:
                for ml in detail_lines.sorted(key=lambda l: l.id):
                    lot = ""
                    if ml.lot_id:
                        lot = ml.lot_id.name
                    elif ml.lot_name:
                        lot = ml.lot_name
                    lines.append(
                        self._jt_delivery_line_dict(
                            code,
                            desc,
                            qty_req,
                            ml.quantity,
                            ml.product_uom_id.name if ml.product_uom_id else uom,
                            lot,
                        )
                    )
            else:
                lines.append(
                    self._jt_delivery_line_dict(
                        code, desc, qty_req, move.quantity, uom, ""
                    )
                )
        return lines

    def _jt_delivery_note_records(self):
        return self.delivery_note_ids

    def _jt_get_or_create_delivery_note(self):
        self.ensure_one()
        Note = self.env["justech.delivery.note"]
        existing = Note.search(
            [("picking_id", "=", self.id), ("state", "!=", "cancel")],
            limit=1,
        )
        if existing:
            return existing, False
        svc = self.env["justech.delivery.note.service"]
        vals = svc._jt_delivery_note_vals_from_picking(self)
        note = Note.create(vals)
        self._jt_post_delivery_note_origin_chatter(note, True)
        return note, True

    @api.depends("delivery_note_ids", "delivery_note_ids.state")
    def _compute_jt_delivery_ui(self):
        return super()._compute_jt_delivery_ui()

    def action_jt_view_delivery_notes(self):
        return super().action_jt_view_delivery_notes()
