from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    justech_ecf_config_id = fields.Many2one(
        "justech.ecf.company.config",
        string="Configuración e-CF",
        compute="_compute_justech_ecf_config",
    )

    def _compute_justech_ecf_config(self):
        Config = self.env["justech.ecf.company.config"]
        for company in self:
            company.justech_ecf_config_id = Config.search([("company_id", "=", company.id)], limit=1)
