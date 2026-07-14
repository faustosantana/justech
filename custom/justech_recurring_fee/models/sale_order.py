# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    justech_fee_id = fields.Many2one(
        "justech.recurring.fee",
        string="Fee recurrente",
        index=True,
        copy=False,
        ondelete="set null",
    )
    justech_fee_period_from = fields.Date(string="Fee período desde", copy=False)
    justech_fee_period_to = fields.Date(string="Fee período hasta", copy=False)
    justech_fee_cycle_number = fields.Integer(string="Fee ciclo", copy=False)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    justech_fee_line_id = fields.Many2one(
        "justech.recurring.fee.line",
        string="Línea de fee",
        copy=False,
        ondelete="set null",
    )
