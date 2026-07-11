# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hellenia_quotation_terms = fields.Html(
        related="company_id.hellenia_quotation_terms",
        readonly=False,
        string="Términos y Condiciones",
    )
