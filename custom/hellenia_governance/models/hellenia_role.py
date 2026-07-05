from odoo import fields, models


class HelleniaRole(models.Model):
    _name = "hellenia.role"
    _description = "Hellenia Functional Role"
    _order = "sequence, name"

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    permission_ids = fields.Many2many(
        "hellenia.permission",
        "hellenia_role_permission_rel",
        "role_id",
        "permission_id",
        string="Permisos",
    )
    is_system = fields.Boolean(
        default=False,
        help="Roles seeded by platform; avoid deleting.",
    )

    _code_uniq = models.Constraint(
        "unique(code)",
        "Role code must be unique.",
    )
