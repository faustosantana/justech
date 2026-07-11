from odoo import api, fields, models, _


class JustechAdminProduct(models.Model):
    _name = "justech.admin.product"
    _description = "Producto funcional Justech"
    _order = "sequence, name"

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    short_description = fields.Text(required=True, translate=True)
    long_description = fields.Html(translate=True)
    icon = fields.Char(default="fa-cube")
    sequence = fields.Integer(default=100)
    active = fields.Boolean(default=True)
    module_ids = fields.One2many("justech.admin.module", "product_id", string="Submódulos")
    module_count = fields.Integer(compute="_compute_counts")
    installed_count = fields.Integer(compute="_compute_counts")
    active_company_count = fields.Integer(compute="_compute_counts")
    status_visual = fields.Selection(
        selection=[
            ("green", "Correcto"),
            ("yellow", "Atención"),
            ("red", "Error"),
            ("blue", "Informativo"),
            ("grey", "No configurado"),
        ],
        compute="_compute_counts",
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "El código de producto debe ser único."),
    ]

    def _compute_counts(self):
        CompanyLine = self.env["justech.admin.module.company"]
        for rec in self:
            mods = rec.module_ids
            rec.module_count = len(mods)
            rec.installed_count = len(mods.filtered(lambda m: m.technical_state == "installed"))
            active_lines = CompanyLine.search_count(
                [("module_id", "in", mods.ids), ("functional_state", "=", "active")]
            )
            rec.active_company_count = active_lines
            if mods.filtered(lambda m: m.status_visual == "red"):
                rec.status_visual = "red"
            elif mods.filtered(lambda m: m.status_visual == "yellow"):
                rec.status_visual = "yellow"
            elif rec.installed_count:
                rec.status_visual = "green"
            else:
                rec.status_visual = "grey"

    def action_open_detail(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "justech.admin.product",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_company_matrix(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Estados por empresa — %s") % self.name,
            "res_model": "justech.admin.module.company",
            "view_mode": "list,form",
            "domain": [("product_id", "=", self.id)],
            "context": {"search_default_group_company": 1},
            "target": "current",
        }
