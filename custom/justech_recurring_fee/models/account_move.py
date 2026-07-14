# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

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

    def action_open_justech_fee(self):
        self.ensure_one()
        if not self.justech_fee_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": self.justech_fee_id.display_name,
            "res_model": "justech.recurring.fee",
            "res_id": self.justech_fee_id.id,
            "view_mode": "form",
            "target": "current",
        }
