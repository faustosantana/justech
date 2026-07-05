from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    justech_do_fiscal_enabled = fields.Boolean(
        string="Fiscal dominicano activo",
        default=True,
    )
    justech_do_ncf_alert_days = fields.Integer(
        string="Días de alerta rangos NCF",
        default=30,
    )
