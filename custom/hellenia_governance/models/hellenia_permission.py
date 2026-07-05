from odoo import fields, models


class HelleniaPermission(models.Model):
    _name = "hellenia.permission"
    _description = "Hellenia Functional Permission"
    _order = "category, code"

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    description = fields.Text(string="Qué hace", translate=True)
    affects = fields.Text(string="Qué afecta", translate=True)
    risk_level = fields.Selection(
        [
            ("low", "Bajo"),
            ("medium", "Medio"),
            ("high", "Alto"),
            ("critical", "Crítico"),
        ],
        default="medium",
        required=True,
    )
    impacted_modules = fields.Char(string="Módulos impactados")
    category = fields.Selection(
        [
            ("pos", "POS"),
            ("ncf", "NCF"),
            ("dgii", "DGII"),
            ("justech", "Justech"),
            ("admin", "Administración"),
        ],
        default="admin",
    )
    active = fields.Boolean(default=True)
    role_ids = fields.Many2many(
        "hellenia.role",
        "hellenia_role_permission_rel",
        "permission_id",
        "role_id",
        string="Roles",
    )
    odoo_group_id = fields.Many2one("res.groups", string="Grupo Odoo puente")

    _code_company_uniq = models.Constraint(
        "unique(code)",
        "Permission code must be unique.",
    )
