from odoo import fields, models


class HelleniaGovernanceAudit(models.Model):
    _name = "hellenia.governance.audit"
    _description = "Hellenia Governance Audit Log"
    _order = "create_date desc"

    action = fields.Char(required=True, index=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.uid)
    company_id = fields.Many2one("res.company")
    model = fields.Char()
    res_id = fields.Integer()
    details = fields.Json(default=dict)
