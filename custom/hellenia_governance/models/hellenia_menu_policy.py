from odoo import fields, models


class HelleniaMenuPolicy(models.Model):
    _name = "hellenia.menu.policy"
    _description = "Hellenia Menu Policy"
    _order = "menu_xmlid"

    menu_id = fields.Many2one("ir.ui.menu", ondelete="cascade")
    menu_xmlid = fields.Char(string="XML ID", index=True)
    name = fields.Char(string="Etiqueta")
    visibility = fields.Selection(
        [
            ("visible", "Visible"),
            ("hidden", "Oculto"),
            ("inherit", "Heredar"),
        ],
        default="visible",
        required=True,
    )
    description = fields.Text(string="Motivo / impacto")
    company_id = fields.Many2one("res.company")
    role_ids = fields.Many2many("hellenia.role", string="Roles autorizados")
    active = fields.Boolean(default=True)
