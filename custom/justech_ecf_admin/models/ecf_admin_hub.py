from odoo import api, fields, models, _


class JustechEcfAdminHub(models.TransientModel):
    _name = "justech.ecf.admin.hub"
    _description = "Administración Justech e-CF"

    name = fields.Char(default="1.3 Facturación electrónica e-CF", readonly=True)
    company_id = fields.Many2one("res.company", string="Empresa activa", readonly=True)
    fiscal_mode_label = fields.Char(string="Modo", readonly=True)
    certificate_label = fields.Char(string="Certificado", readonly=True)
    dgii_label = fields.Char(string="Conexión DGII", readonly=True)
    queue_label = fields.Char(string="Cola", readonly=True)
    errors_label = fields.Char(string="Errores", readonly=True)
    last_tx_label = fields.Char(string="Última transmisión", readonly=True)
    recommended_html = fields.Html(readonly=True, sanitize=False)
    intro_html = fields.Html(readonly=True, sanitize=False)
    stats_html = fields.Html(readonly=True, sanitize=False)
    breadcrumb_html = fields.Html(readonly=True, sanitize=False)
    pending_count = fields.Integer(readonly=True)
    sent_count = fields.Integer(readonly=True)
    accepted_count = fields.Integer(readonly=True)
    rejected_count = fields.Integer(readonly=True)

    @api.model
    def action_open(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        hub = self.create({})
        hub._load_state()
        return {
            "type": "ir.actions.act_window",
            "name": _("1.3 Facturación electrónica e-CF"),
            "res_model": self._name,
            "res_id": hub.id,
            "view_mode": "form",
            "target": "current",
            "context": {"form_view_initial_mode": "readonly"},
        }

    def _load_state(self):
        self.ensure_one()
        company = self.env.company
        self.company_id = company.id
        cfg = self.env["justech.ecf.company.config"].search([("company_id", "=", company.id)], limit=1)
        mode_map = {
            "traditional_ncf": _("NCF tradicional"),
            "ecf_lab": _("Laboratorio"),
            "ecf_certification": _("Certificación"),
            "ecf_production": _("Producción"),
            False: _("No configurado"),
        }
        mode = cfg.fiscal_mode if cfg else False
        self.fiscal_mode_label = mode_map.get(mode, mode or _("No configurado"))
        cert = cfg.certificate_id if cfg else False
        self.certificate_label = (
            _("Asignado — %s") % (cert.name,)
            if cert
            else _("Sin certificado")
        )
        env_label = (cfg.dgii_environment if cfg else "mock") or "mock"
        self.dgii_label = {
            "mock": _("Simulación (mock)"),
            "test": _("Prueba DGII"),
            "certification": _("Certificación DGII"),
            "production": _("Producción DGII (Gate)"),
        }.get(env_label, env_label)
        Queue = self.env["justech.ecf.queue.job"]
        pending = Queue.search_count([("company_id", "=", company.id), ("state", "in", ["pending", "running"])]) if "justech.ecf.queue.job" in self.env else 0
        failed = Queue.search_count([("company_id", "=", company.id), ("state", "in", ["failed", "dead"])]) if "justech.ecf.queue.job" in self.env else 0
        self.queue_label = _("%s pendientes · %s fallidos") % (pending, failed)
        self.errors_label = _("Sin errores abiertos") if not failed else _("%s jobs fallidos") % failed
        Doc = self.env["justech.ecf.document"]
        last = Doc.search([("company_id", "=", company.id)], order="write_date desc", limit=1)
        self.last_tx_label = last.write_date.strftime("%Y-%m-%d %H:%M") if last else _("Sin transmisiones")

        recs = []
        if not self.env.user.has_group("justech_ecf_core.group_ecf_readonly") and not self.env.user.has_group(
            "justech_admin_center.group_justech_admin_center_manager"
        ):
            recs.append(
                _(
                    "<strong>Falta asignar un rol e-CF.</strong> "
                    "Vaya a Usuarios → Permisos Justech → e-CF."
                )
            )
        if not cfg or not cfg.certificate_id:
            recs.append(_("Falta asignar un certificado digital para esta empresa."))
        if mode in (False, "traditional_ncf"):
            recs.append(_("Esta empresa aún no está en modo e-CF de certificación."))
        if not recs:
            recs.append(_("Configuración básica presente. Continúe con pruebas de laboratorio o certificación."))
        self.recommended_html = (
            '<div class="o_jac_recommend"><h3>%s</h3><ul>%s</ul>'
            '<button type="object" class="btn btn-primary" name="action_open_permissions">%s</button></div>'
            % (
                _("Acciones recomendadas"),
                "".join("<li>%s</li>" % r for r in recs),
                _("Configurar permisos"),
            )
        )
        # button in HTML won't work as object — use field + real buttons in view
        self.recommended_html = (
            '<div class="o_jac_recommend"><h3>%s</h3><ul>%s</ul></div>'
            % (_("Acciones recomendadas"), "".join("<li>%s</li>" % r for r in recs))
        )
        accepted = Doc.search_count([("company_id", "=", company.id), ("state", "=", "accepted")])
        rejected = Doc.search_count([("company_id", "=", company.id), ("state", "=", "rejected")])
        sent = Doc.search_count([("company_id", "=", company.id), ("state", "in", ["sent", "signed"])])
        self.pending_count = pending
        self.sent_count = sent
        self.accepted_count = accepted
        self.rejected_count = rejected
        self.breadcrumb_html = (
            '<nav class="o_jac_breadcrumb" aria-label="breadcrumb">'
            '<span>%s</span> → <span>%s</span> → <span>%s</span></nav>'
        ) % (
            _("Administración Justech"),
            _("1. Justech Fiscal"),
            _("1.3 Facturación electrónica e-CF"),
        )
        self.stats_html = (
            '<div class="o_jac_ecf_stats">'
            "<span><strong>%s</strong><br/><span class=\"o_jac_muted\">%s</span></span>"
            "<span><strong>%s</strong><br/><span class=\"o_jac_muted\">%s</span></span>"
            "<span><strong>%s</strong><br/><span class=\"o_jac_muted\">%s</span></span>"
            "<span><strong>%s</strong><br/><span class=\"o_jac_muted\">%s</span></span>"
            "</div>"
        ) % (
            pending, _("Pendientes"),
            sent, _("Enviados"),
            accepted, _("Aceptados"),
            rejected, _("Rechazados"),
        )
        self.intro_html = (
            "<p>%s</p>"
            % _(
                "Emite, firma, envía y monitorea comprobantes electrónicos ante la DGII."
            )
        )

    def action_open_pending_kpi(self):
        return self.action_open_queue()

    def action_open_sent_kpi(self):
        return self.action_open_documents()

    def action_open_accepted_kpi(self):
        action = self.env.ref("justech_ecf_core.action_justech_ecf_document").read()[0]
        action["domain"] = [("company_id", "=", self.company_id.id), ("state", "=", "accepted")]
        return action

    def action_open_rejected_kpi(self):
        action = self.env.ref("justech_ecf_core.action_justech_ecf_document").read()[0]
        action["domain"] = [("company_id", "=", self.company_id.id), ("state", "=", "rejected")]
        return action

    def action_load_certificate(self):
        return self.action_open_certificates()

    def action_switch_certification(self):
        return self.action_open_config()

    def action_test_signature(self):
        return self.action_open_setup()

    def action_check_dgii(self):
        return self.action_diagnose()

    def action_open_dashboard(self):
        return self.env["justech.ecf.dashboard"].action_open()

    def action_open_setup(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Asistente de implementación e-CF"),
            "res_model": "justech.ecf.setup.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def action_open_config(self):
        return self.env.ref("justech_ecf_core.action_justech_ecf_company_config").read()[0]

    def action_open_certificates(self):
        return self.env.ref("justech_ecf_core.action_justech_ecf_certificate").read()[0]

    def action_open_documents(self):
        return self.env.ref("justech_ecf_core.action_justech_ecf_document").read()[0]

    def action_open_queue(self):
        return self.env.ref("justech_ecf_queue.action_justech_ecf_queue_job").read()[0]

    def action_open_inbound(self):
        try:
            return self.env.ref("justech_ecf_admin.action_justech_ecf_inbound").read()[0]
        except ValueError:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Recepción e-CF"),
                    "message": _("La recepción de proveedores aún no tiene menú publicado."),
                    "type": "warning",
                },
            }

    def action_open_permissions(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Usuarios — permisos Justech"),
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("share", "=", False)],
            "target": "current",
        }

    def action_diagnose(self):
        Finding = self.env["justech.admin.health.finding"].sudo()
        mod = self.env["justech.admin.module"].search([("technical_name", "=", "justech_ecf_admin")], limit=1)
        for tech in [
            "justech_ecf_core",
            "justech_ecf_xml",
            "justech_ecf_signature",
            "justech_ecf_dgii",
            "justech_ecf_queue",
            "justech_ecf_admin",
        ]:
            irm = self.env["ir.module.module"].search([("name", "=", tech)], limit=1)
            ok = irm and irm.state == "installed"
            Finding.create(
                {
                    "code": "ECF_MOD_%s" % tech,
                    "severity": "info" if ok else "error",
                    "name": _("Módulo %s") % tech,
                    "detail": _("Instalado") if ok else _("No instalado"),
                    "module_id": mod.id if mod else False,
                    "state": "open",
                }
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Diagnóstico e-CF"),
                "message": _("Comprobaciones registradas. Revise el estado del sistema en la consola."),
                "type": "success",
                "sticky": False,
            },
        }
