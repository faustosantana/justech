from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class JustechEcfCompanyConfig(models.Model):
    _name = "justech.ecf.company.config"
    _description = "Configuración e-CF por empresa"
    _rec_name = "company_id"

    company_id = fields.Many2one("res.company", required=True, index=True, ondelete="cascade")
    active = fields.Boolean(default=True)
    fiscal_mode = fields.Selection(
        selection=[
            ("traditional_ncf", "NCF tradicional"),
            ("ecf_certification", "e-CF en certificación"),
            ("ecf_production", "e-CF en producción"),
        ],
        string="Modo fiscal",
        default="traditional_ncf",
        required=True,
        help="Un solo motor fiscal activo por empresa.",
    )
    dgii_environment = fields.Selection(
        selection=[
            ("mock", "Simulación (mock)"),
            ("testecf", "Pre-certificación (TesteCF)"),
            ("certecf", "Certificación (CerteCF)"),
            ("ecf", "Producción (eCF) — bloqueada por defecto"),
        ],
        string="Ambiente DGII",
        default="mock",
        required=True,
    )
    production_gate_unlocked = fields.Boolean(
        string="Gate de Producción desbloqueada",
        default=False,
        help="Producción DGII requiere permiso, confirmación y configuración completa.",
    )
    certificate_id = fields.Many2one("justech.ecf.certificate", string="Certificado activo")
    rnc_emisor = fields.Char(string="RNC emisor", related="company_id.vat", readonly=True)
    setup_step = fields.Integer(default=1)
    setup_complete = fields.Boolean(default=False)
    last_health_at = fields.Datetime(readonly=True)
    last_health_summary = fields.Text(readonly=True)
    note = fields.Text()

    _sql_constraints = [
        ("company_uniq", "unique(company_id)", "Solo una configuración e-CF por empresa."),
    ]

    @api.constrains("fiscal_mode", "dgii_environment", "production_gate_unlocked")
    def _check_production_gate(self):
        for rec in self:
            if rec.fiscal_mode == "ecf_production" or rec.dgii_environment == "ecf":
                if not rec.production_gate_unlocked:
                    raise ValidationError(
                        _(
                            "El ambiente de Producción DGII está bloqueado. "
                            "Complete la Gate de Producción antes de activarlo."
                        )
                    )
            if rec.fiscal_mode == "traditional_ncf" and rec.dgii_environment in ("certecf", "ecf"):
                raise ValidationError(
                    _("Con NCF tradicional el ambiente DGII debe ser mock o pre-certificación.")
                )

    def action_run_health(self):
        self.ensure_one()
        checks = []
        checks.append(("módulo", "ok", _("justech_ecf_core instalado")))
        if self.certificate_id and self.certificate_id.state == "valid":
            checks.append(("certificado", "ok", _("Certificado válido hasta %s") % self.certificate_id.date_end))
        else:
            checks.append(("certificado", "warn", _("Sin certificado válido")))
        if self.dgii_environment == "ecf" and not self.production_gate_unlocked:
            checks.append(("producción", "error", _("Gate de Producción bloqueada")))
        else:
            checks.append(("producción", "ok", _("Ambiente %s") % self.dgii_environment))
        summary = " | ".join("%s:%s" % (c[0], c[1]) for c in checks)
        self.write({"last_health_at": fields.Datetime.now(), "last_health_summary": summary})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Diagnóstico e-CF"), "message": summary, "type": "info"},
        }

    def unlock_production_gate(self):
        self.ensure_one()
        if not self.env.user.has_group("justech_ecf_core.group_ecf_admin"):
            raise UserError(_("Solo un Administrador e-CF puede desbloquear Producción."))
        if not self.certificate_id or self.certificate_id.state != "valid":
            raise UserError(_("Se requiere un certificado válido antes de desbloquear Producción."))
        self.production_gate_unlocked = True
