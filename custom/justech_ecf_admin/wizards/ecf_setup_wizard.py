from odoo import fields, models, _
from odoo.exceptions import UserError


class JustechEcfSetupWizard(models.TransientModel):
    _name = "justech.ecf.setup.wizard"
    _description = "Asistente visual de implementación e-CF"

    step = fields.Integer(default=1)
    company_id = fields.Many2one("res.company", required=True, default=lambda s: s.env.company)
    fiscal_mode = fields.Selection(
        selection=[
            ("traditional_ncf", "NCF tradicional"),
            ("ecf_certification", "e-CF en certificación"),
            ("ecf_production", "e-CF en producción"),
        ],
        required=True,
        default="traditional_ncf",
    )
    dgii_environment = fields.Selection(
        selection=[
            ("mock", "Simulación (recomendado en desarrollo)"),
            ("testecf", "Pre-certificación DGII"),
            ("certecf", "Certificación DGII"),
            ("ecf", "Producción DGII (bloqueada)"),
        ],
        default="mock",
        required=True,
    )
    checklist_html = fields.Html(readonly=True, sanitize=False)
    result_message = fields.Text(readonly=True)

    def action_next(self):
        self.ensure_one()
        if self.step >= 11:
            return self.action_activate()
        self.step += 1
        self._refresh_checklist()
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.step = max(1, self.step - 1)
        self._refresh_checklist()
        return self._reopen()

    def _refresh_checklist(self):
        steps = [
            _("1. Seleccionar empresa"),
            _("2. Seleccionar modo fiscal"),
            _("3. Cargar certificado"),
            _("4. Validar certificado"),
            _("5. Configurar ambiente DGII"),
            _("6. Verificar servicios DGII (mock/catálogo)"),
            _("7. Firma de prueba"),
            _("8. XML de prueba"),
            _("9. Envío de certificación (solo si autorizado)"),
            _("10. Revisar resultados"),
            _("11. Activar"),
        ]
        self.checklist_html = "<ol>%s</ol>" % "".join(
            "<li%s>%s</li>" % (' style="font-weight:bold"' if i + 1 == self.step else "", s)
            for i, s in enumerate(steps)
        )

    def action_activate(self):
        self.ensure_one()
        if self.fiscal_mode == "ecf_production" or self.dgii_environment == "ecf":
            raise UserError(
                _(
                    "Producción DGII no se puede activar desde este asistente sin Gate "
                    "y autorización explícita. Use mock o certificación."
                )
            )
        Config = self.env["justech.ecf.company.config"]
        cfg = Config.search([("company_id", "=", self.company_id.id)], limit=1)
        vals = {
            "company_id": self.company_id.id,
            "fiscal_mode": self.fiscal_mode,
            "dgii_environment": self.dgii_environment,
            "setup_complete": True,
            "setup_step": 11,
        }
        if cfg:
            cfg.write(vals)
        else:
            cfg = Config.create(vals)
        self.result_message = _(
            "Configuración guardada para %(co)s · modo %(mode)s · ambiente %(env)s. "
            "Histórico y GL no fueron modificados."
        ) % {"co": self.company_id.name, "mode": self.fiscal_mode, "env": self.dgii_environment}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("e-CF configurado"),
                "message": self.result_message,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        wiz = self.new(res)
        wiz._refresh_checklist()
        res["checklist_html"] = wiz.checklist_html
        return res
