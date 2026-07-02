# -*- coding: utf-8 -*-
from odoo import fields, models


class JustechDeliveryNoteLine(models.Model):
    _name = "justech.delivery.note.line"
    _description = "Línea de Conduce de Entrega"
    _order = "sequence, id"

    delivery_note_id = fields.Many2one(
        "justech.delivery.note",
        string="Conduce",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one("product.product", string="Producto")
    default_code = fields.Char(string="Código")
    name = fields.Char(string="Descripción", required=True)
    product_uom_qty = fields.Float(string="Cant. solicitada", digits="Product Unit")
    qty_delivered = fields.Float(string="Cant. entregada", digits="Product Unit")
    product_uom_id = fields.Many2one("uom.uom", string="Unidad")
    lot_id = fields.Many2one("stock.lot", string="Lote / serie")
