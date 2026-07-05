from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def has_hellenia_permission(self, code, company=None):
        return self.env["hellenia.governance.service"].has_permission(
            code, user=self, company=company
        )

    def require_hellenia_permission(self, code, company=None):
        return self.env["hellenia.governance.service"].require_permission(
            code, user=self, company=company
        )
