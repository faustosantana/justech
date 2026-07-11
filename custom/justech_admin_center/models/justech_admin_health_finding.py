from odoo import fields, models


class JustechAdminHealthFinding(models.Model):
    _name = "justech.admin.health.finding"
    _description = "Hallazgo de diagnóstico Justech Admin"
    _order = "severity desc, id desc"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    module_id = fields.Many2one("justech.admin.module", ondelete="cascade")
    severity = fields.Selection(
        selection=[
            ("info", "Informativo"),
            ("warning", "Advertencia"),
            ("error", "Error"),
            ("critical", "Crítico"),
        ],
        default="warning",
        required=True,
    )
    state = fields.Selection(
        selection=[("open", "Abierto"), ("resolved", "Resuelto")],
        default="open",
        required=True,
    )
    detail = fields.Text()
    recommendation = fields.Text()
    res_model = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one("res.company")

    def action_open_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    def action_mark_resolved(self):
        self.write({"state": "resolved"})
