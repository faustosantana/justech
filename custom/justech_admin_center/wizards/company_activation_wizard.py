from odoo import api, fields, models, _
from odoo.exceptions import UserError


class JustechAdminCompanyActivationWizard(models.TransientModel):
    _name = "justech.admin.company.activation.wizard"
    _description = "Previsualización activación por empresa"

    line_id = fields.Many2one("justech.admin.module.company", required=True)
    operation = fields.Selection(
        selection=[
            ("activate", "Activar"),
            ("deactivate", "Desactivar"),
            ("engine", "Cambiar motor"),
        ],
        required=True,
    )
    new_engine = fields.Selection(
        selection=[
            ("traditional_ncf", "NCF tradicional"),
            ("electronic", "Facturación electrónica"),
        ],
        string="Motor fiscal destino",
    )
    preview_before = fields.Text(readonly=True)
    preview_after = fields.Text(readonly=True)
    risks = fields.Text(readonly=True)
    no_impact = fields.Text(readonly=True)
    rollback_notes = fields.Text(readonly=True)
    confirmation = fields.Boolean(string="Confirmo el cambio")

    @api.model
    def action_open(self, line, operation):
        wiz = self.create({"line_id": line.id, "operation": operation})
        wiz._load_preview()
        return {
            "type": "ir.actions.act_window",
            "name": _("Confirmar cambio por empresa"),
            "res_model": self._name,
            "res_id": wiz.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.onchange("new_engine", "operation")
    def _onchange_preview(self):
        if self.line_id and self.operation:
            self._load_preview()

    def _load_preview(self):
        data = self.env["justech.admin.company.activation.service"].build_preview(
            self.line_id, self.operation, new_engine=self.new_engine
        )
        self.preview_before = str(data["before"])
        self.preview_after = str(data["after"])
        self.risks = data["risks"]
        self.no_impact = data["no_impact"]
        self.rollback_notes = data["rollback"]

    def action_apply(self):
        self.ensure_one()
        if not self.confirmation:
            raise UserError(_("Debe confirmar el cambio."))
        self.env["justech.admin.center.auth.service"].require_session()
        self.env["justech.admin.company.activation.service"].apply(
            self.line_id, self.operation, new_engine=self.new_engine
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cambio aplicado"),
                "message": _("Estado actualizado para %s") % self.line_id.company_id.name,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
