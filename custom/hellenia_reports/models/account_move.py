# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def hellenia_invoice_qr_uri(self):
        self.ensure_one()
        value = self.justech_do_ncf or self.name
        return self.company_id.hellenia_qr_data_uri(value)
