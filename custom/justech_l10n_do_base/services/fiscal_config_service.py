"""Proveedor de configuración fiscal por empresa."""
from odoo import models


class JustechDoFiscalConfigService(models.AbstractModel):
    _name = "justech.do.fiscal.config.service"
    _description = "Justech Fiscal Configuration Service"

    def is_fiscal_enabled(self, company=None):
        company = company or self.env.company
        return bool(
            company.country_id.code == "DO" and company.justech_do_fiscal_enabled
        )

    def get_param(self, key, company=None, default=None):
        company = company or self.env.company
        full_key = f"justech_fiscal.{company.id}.{key}"
        value = self.env["ir.config_parameter"].sudo().get_param(full_key)
        if value is None:
            value = self.env["ir.config_parameter"].sudo().get_param(
                f"justech_fiscal.{key}", default
            )
        return value
