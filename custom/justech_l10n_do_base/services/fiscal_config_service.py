"""Proveedor de configuración fiscal por empresa."""
from odoo import models


class JustechDoFiscalConfigService(models.AbstractModel):
    _name = "justech.do.fiscal.config.service"
    _description = "Justech Fiscal Configuration Service"

    def is_fiscal_enabled(self, company=None):
        company = company or self.env.company
        if not (company.country_id.code == "DO" and company.justech_do_fiscal_enabled):
            return False
        if "justech.fiscal.feature.flag" in self.env:
            # Lectura técnica del motor: no exigir grupo Fiscal Admin al facturador.
            return self.env["justech.fiscal.feature.flag"].sudo().is_enabled(
                "ncf_motor", company
            )
        return True

    def is_dual_write_enabled(self, company=None):
        company = company or self.env.company
        if "justech.fiscal.feature.flag" not in self.env:
            return True
        return self.env["justech.fiscal.feature.flag"].sudo().is_enabled(
            "ncf_dual_write", company
        )

    def is_duplicate_blocking_enabled(self, company=None):
        company = company or self.env.company
        if "justech.fiscal.feature.flag" not in self.env:
            return True
        return self.env["justech.fiscal.feature.flag"].sudo().is_enabled(
            "duplicate_blocking", company
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
