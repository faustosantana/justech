from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class JustechLicenseCompany(models.Model):
    _name = "justech.license.company"
    _description = "Company covered by a License"
    _order = "license_id, company_id"

    license_id = fields.Many2one(
        "justech.license",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="cascade",
        index=True,
    )

    _sql_constraints = [
        (
            "license_company_unique",
            "UNIQUE(license_id, company_id)",
            "Company already assigned to this license.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("license_id")._check_max_companies()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.mapped("license_id")._check_max_companies()
        return res

    def unlink(self):
        licenses = self.mapped("license_id")
        res = super().unlink()
        licenses._check_max_companies()
        return res
