# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class JustechRecurringFeeLine(models.Model):
    _name = "justech.recurring.fee.line"
    _description = "Línea de fee recurrente"
    _order = "sequence, id"

    fee_id = fields.Many2one(
        "justech.recurring.fee",
        string="Fee",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="fee_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="fee_id.currency_id")
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        "product.product",
        string="Producto / Servicio",
        required=True,
        domain="[('sale_ok', '=', True)]",
    )
    name = fields.Char(string="Descripción")
    product_uom_qty = fields.Float(string="Cantidad", default=1.0, required=True)
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="UdM",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit", raise_if_not_found=False),
    )
    price_unit = fields.Float(string="Precio", digits="Product Price", required=True)
    tax_ids = fields.Many2many("account.tax", string="Impuestos")
    price_subtotal = fields.Monetary(
        string="Subtotal", compute="_compute_amount", store=True, currency_field="currency_id"
    )
    price_total = fields.Monetary(
        string="Total", compute="_compute_amount", store=True, currency_field="currency_id"
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.name = self.product_id.get_product_multiline_description_sale()
        self.product_uom_id = self.product_id.uom_id
        self.price_unit = self.product_id.lst_price
        company = self.fee_id.company_id
        self.tax_ids = self.product_id.taxes_id.filtered(
            lambda t: not t.company_id or t.company_id == company
        )

    def write(self, vals):
        tracked = {"product_id", "product_uom_qty", "price_unit", "tax_ids", "name"}
        audits = []
        touch = set(vals) & tracked
        if touch:
            for line in self:
                changes = []
                for field in sorted(touch):
                    old = line[field]
                    new = vals.get(field)
                    if field == "tax_ids":
                        old = old.ids
                        if isinstance(new, list) and new and isinstance(new[0], (list, tuple)):
                            # (6, 0, ids)
                            cmds = new
                            if cmds and cmds[0][0] == 6:
                                new = cmds[0][2]
                    if old != new:
                        changes.append("%s: %s → %s" % (field, old, new))
                if changes:
                    audits.append((line.fee_id, line, changes))
        res = super().write(vals)
        for fee, line, changes in audits:
            fee.message_post(
                body=_(
                    "Cambio de línea (aplica a ciclos futuros) · desde ciclo siguiente: %(changes)s"
                )
                % {"changes": "; ".join(changes)}
            )
        return res

    @api.depends(
        "product_uom_qty",
        "price_unit",
        "tax_ids",
        "currency_id",
        "product_id",
        "fee_id.partner_id",
        "fee_id.company_id",
    )
    def _compute_amount(self):
        for line in self:
            taxes = line.tax_ids.filtered(
                lambda t: not t.company_id or t.company_id == line.fee_id.company_id
            )
            taxes_res = taxes.compute_all(
                line.price_unit,
                currency=line.currency_id,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=line.fee_id.partner_id,
            )
            line.price_subtotal = taxes_res["total_excluded"]
            line.price_total = taxes_res["total_included"]
