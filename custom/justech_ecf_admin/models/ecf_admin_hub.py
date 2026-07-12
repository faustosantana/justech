from odoo import api, fields, models, _


class JustechEcfAdminHub(models.TransientModel):
    _name = "justech.ecf.admin.hub"
    _description = "Administración Justech e-CF"

    name = fields.Char(default="Justech e-CF", readonly=True)
    intro_html = fields.Html(readonly=True, sanitize=False)

    @api.model
    def action_open(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        hub = self.create({})
        hub.intro_html = (
            '<div class="o_jac_overview">'
            "<p><strong>%s</strong></p>"
            "<p>%s</p>"
            "<ul class='o_jac_func_list'>"
            "<li>%s</li><li>%s</li><li>%s</li><li>%s</li>"
            "</ul></div>"
        ) % (
            _("Facturación electrónica e-CF (DGII)"),
            _(
                "Administre por empresa el modo NCF tradicional, e-CF en certificación "
                "o e-CF en producción (Gate). No se realizan envíos a Producción DGII desde desarrollo."
            ),
            _("Qué es: motor electrónico oficial de comprobantes fiscales dominicanos."),
            _("Quién lo usa: Contabilidad, facturación y administradores fiscales."),
            _("Al activar: habilita XML, firma, cola y ambiente DGII configurado."),
            _("Al desactivar: conserva histórico; bloquea nuevos envíos e-CF."),
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Justech e-CF"),
            "res_model": self._name,
            "res_id": hub.id,
            "view_mode": "form",
            "target": "current",
        }

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
        return self.env.ref("justech_ecf_core.action_justech_ecf_company_config").sudo().read()[0]

    def action_open_certificates(self):
        return self.env.ref("justech_ecf_core.action_justech_ecf_certificate").sudo().read()[0]

    def action_open_documents(self):
        return self.env.ref("justech_ecf_core.action_justech_ecf_document").sudo().read()[0]

    def action_open_queue(self):
        return self.env.ref("justech_ecf_queue.action_justech_ecf_queue_job").sudo().read()[0]

    def action_diagnose(self):
        Finding = self.env["justech.admin.health.finding"].sudo()
        mod = self.env["justech.admin.module"].search([("technical_name", "=", "justech_ecf_admin")], limit=1)
        checks = []
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
            checks.append((tech, ok))
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
        # mock client smoke
        try:
            cat = self.env["justech.ecf.dgii.client"].service_catalog()
            Finding.create(
                {
                    "code": "ECF_DGII_CATALOG",
                    "severity": "info",
                    "name": _("Catálogo servicios DGII"),
                    "detail": _("%s servicios documentados; producción bloqueada por defecto.")
                    % len(cat.get("services", [])),
                    "module_id": mod.id if mod else False,
                    "state": "open",
                }
            )
        except Exception as exc:
            Finding.create(
                {
                    "code": "ECF_DGII_CATALOG",
                    "severity": "error",
                    "name": _("Catálogo servicios DGII"),
                    "detail": str(exc)[:300],
                    "module_id": mod.id if mod else False,
                    "state": "open",
                }
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Diagnóstico e-CF"),
            "res_model": "justech.admin.health.finding",
            "view_mode": "list,form",
            "domain": [("code", "like", "ECF_")],
        }
