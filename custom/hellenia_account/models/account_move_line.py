from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    justech_do_ncf = fields.Char(related="move_id.justech_do_ncf", string="NCF", readonly=True)
