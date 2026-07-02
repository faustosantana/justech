# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class JustechDeliveryNote(models.Model):
    _name = "justech.delivery.note"
    _description = "Conduce de Entrega"
    _inherit = ["mail.thread", "mail.activity.mixin", "jt.delivery.report.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Número de conduce",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    partner_id = fields.Many2one("res.partner", string="Cliente", required=True, tracking=True)
    sale_order_id = fields.Many2one("sale.order", string="Orden de venta", index=True, ondelete="set null")
    invoice_id = fields.Many2one("account.move", string="Factura", index=True, ondelete="set null")
    picking_id = fields.Many2one("stock.picking", string="Entrega", index=True, ondelete="set null")
    date = fields.Datetime(
        string="Fecha",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("done", "Emitido"),
            ("cancel", "Cancelado"),
        ],
        string="Estado",
        default="done",
        required=True,
        tracking=True,
    )
    note = fields.Html(string="Observaciones")
    origin_type = fields.Selection(
        [
            ("sale", "Cotización / OV"),
            ("invoice", "Factura"),
            ("picking", "Entrega"),
        ],
        string="Origen",
        required=True,
        index=True,
    )
    line_ids = fields.One2many(
        "justech.delivery.note.line",
        "delivery_note_id",
        string="Líneas",
        copy=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = seq.next_by_code("justech.delivery.note") or _("Nuevo")
        records = super().create(vals_list)
        for note in records:
            note._jt_post_creation_chatter()
        return records

    def _jt_post_creation_chatter(self):
        self.ensure_one()
        origin = []
        if self.sale_order_id:
            origin.append(_("Cotización/OV: %s") % self.sale_order_id.name)
        if self.invoice_id:
            origin.append(_("Factura: %s") % self.invoice_id.name)
        if self.picking_id:
            origin.append(_("Entrega: %s") % self.picking_id.name)
        body = _(
            "Conduce creado por %(user)s el %(date)s. Origen: %(origin)s",
            user=self.user_id.display_name,
            date=fields.Datetime.to_string(self.date),
            origin=", ".join(origin) if origin else _("manual"),
        )
        self.message_post(body=body, subtype_xmlid="mail.mt_note")

    # --- API QWeb (mixin) ---
    def get_jt_delivery_company(self):
        return self.company_id

    def get_jt_delivery_conduce_number(self):
        return self.name or "—"

    def get_jt_delivery_picking_number(self):
        return self.picking_id.name if self.picking_id else "—"

    def get_jt_delivery_sale_order_name(self):
        return self.sale_order_id.name if self.sale_order_id else "—"

    def get_jt_delivery_invoice_name(self):
        return self.invoice_id.name if self.invoice_id else "—"

    def get_jt_delivery_state_display(self):
        labels = {"draft": "Borrador", "done": "Emitido", "cancel": "Cancelado"}
        return labels.get(self.state, self.state or "—")

    def get_jt_delivery_date_display(self):
        if not self.date:
            return "—"
        return self.date.strftime("%d/%m/%Y")

    def get_jt_delivery_customer_name(self):
        return self.partner_id.name if self.partner_id else "—"

    def _jt_delivery_resolve_shipping_partner(self):
        self.ensure_one()
        candidates = []
        if self.picking_id and self.picking_id.partner_id:
            candidates.append(self.picking_id.partner_id)
        if self.sale_order_id:
            if self.sale_order_id.partner_shipping_id:
                candidates.append(self.sale_order_id.partner_shipping_id)
            if self.sale_order_id.partner_id:
                candidates.append(self.sale_order_id.partner_id)
        if self.invoice_id:
            if self.invoice_id.partner_shipping_id:
                candidates.append(self.invoice_id.partner_shipping_id)
            if self.invoice_id.partner_id:
                candidates.append(self.invoice_id.partner_id)
        if self.partner_id:
            candidates.append(self.partner_id)
        expanded = self._jt_delivery_expand_partner_candidates(*candidates)
        for partner in expanded:
            if self._jt_delivery_partner_has_address(partner):
                return partner
        return expanded[0] if expanded else self.partner_id

    def get_jt_delivery_responsible_display(self):
        if self.picking_id and self.picking_id.user_id:
            return self._jt_delivery_user_label(self.picking_id.user_id)
        return self._jt_delivery_user_label(self.user_id)

    def get_jt_delivery_salesperson_display(self):
        if self.sale_order_id and self.sale_order_id.user_id:
            return self._jt_delivery_user_label(self.sale_order_id.user_id)
        if self.invoice_id and self.invoice_id.invoice_user_id:
            return self._jt_delivery_user_label(self.invoice_id.invoice_user_id)
        return "—"

    def get_jt_delivery_warehouse_origin(self):
        if self.picking_id:
            return self.picking_id.get_jt_delivery_warehouse_origin()
        if self.sale_order_id:
            return self.sale_order_id.get_jt_delivery_warehouse_origin()
        return "—"

    def get_jt_delivery_observations_html(self):
        return self.note or False

    def get_jt_delivery_lines(self):
        self.ensure_one()
        lines = []
        for line in self.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
            lot = line.lot_id.name if line.lot_id else ""
            lines.append(
                self._jt_delivery_line_dict(
                    line.default_code or "",
                    line.name,
                    line.product_uom_qty,
                    line.qty_delivered,
                    line.product_uom_id.name if line.product_uom_id else "",
                    lot,
                )
            )
        return lines

    def action_print_delivery_note(self):
        self.ensure_one()
        return self.env.ref(
            "justech_report_design.action_report_justech_delivery_note"
        ).report_action(self)
