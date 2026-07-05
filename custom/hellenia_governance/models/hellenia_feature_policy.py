from odoo import fields, models


class HelleniaFeaturePolicy(models.Model):
    _name = "hellenia.feature.policy"
    _description = "Hellenia Operational Feature Policy"
    _order = "feature_code, company_id"

    feature_code = fields.Char(required=True, index=True)
    name = fields.Char(string="Nombre")
    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    enabled = fields.Boolean(default=True)
    enabled_at = fields.Datetime()
    enabled_by_id = fields.Many2one("res.users")
    notes = fields.Text()

    _feature_company_uniq = models.Constraint(
        "unique(feature_code, company_id)",
        "One policy per feature and company.",
    )
