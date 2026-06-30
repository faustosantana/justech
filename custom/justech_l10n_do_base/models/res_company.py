from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    justech_do_fiscal_enabled = fields.Boolean(
        string="Dominican Fiscal (Justech)",
        default=True,
    )
    justech_do_ncf_alert_days = fields.Integer(
        string="NCF Range Alert (days)",
        default=30,
    )
