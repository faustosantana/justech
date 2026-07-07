from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    justech_multicurrency_policy_id = fields.Many2one(
        "justech.multicurrency.policy",
        string="Política multimoneda Justech",
        compute="_compute_justech_multicurrency_policy",
    )

    def _compute_justech_multicurrency_policy(self):
        Policy = self.env["justech.multicurrency.policy"]
        policies = Policy.search([("company_id", "in", self.ids)])
        by_company = {p.company_id.id: p for p in policies}
        for company in self:
            company.justech_multicurrency_policy_id = by_company.get(company.id)
