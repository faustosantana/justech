from odoo import api, fields, models


class HelleniaUserProfile(models.Model):
    _name = "hellenia.user.profile"
    _description = "Hellenia User Functional Profile"
    _order = "user_id, company_id"

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    role_ids = fields.Many2many("hellenia.role", string="Roles funcionales")
    permission_ids = fields.Many2many(
        "hellenia.permission",
        "hellenia_user_profile_permission_rel",
        "profile_id",
        "permission_id",
        string="Permisos directos",
    )
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    _user_company_uniq = models.Constraint(
        "unique(user_id, company_id)",
        "One functional profile per user and company.",
    )

    @api.depends("user_id", "company_id")
    def _compute_name(self):
        for profile in self:
            user = profile.user_id.name or "?"
            company = profile.company_id.name or "?"
            profile.name = f"{user} @ {company}"
