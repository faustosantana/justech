from odoo import api, fields, models, _


class JustechEcfDashboard(models.TransientModel):
    _name = "justech.ecf.dashboard"
    _description = "Dashboard Justech e-CF"

    name = fields.Char(default="Justech e-CF", readonly=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    environment_label = fields.Char(readonly=True)
    cert_label = fields.Char(readonly=True)
    count_accepted = fields.Integer(readonly=True)
    count_rejected = fields.Integer(readonly=True)
    count_pending = fields.Integer(readonly=True)
    count_contingency = fields.Integer(readonly=True)
    count_queue = fields.Integer(readonly=True)
    count_retry = fields.Integer(readonly=True)
    summary_html = fields.Html(readonly=True, sanitize=False)

    @api.model
    def action_open(self):
        dash = self.create({})
        dash._load()
        return {
            "type": "ir.actions.act_window",
            "name": _("Dashboard e-CF"),
            "res_model": self._name,
            "res_id": dash.id,
            "view_mode": "form",
            "target": "current",
        }

    def _load(self):
        self.ensure_one()
        Doc = self.env["justech.ecf.document"]
        company = self.company_id
        cfg = self.env["justech.ecf.company.config"].search([("company_id", "=", company.id)], limit=1)
        domain = [("company_id", "=", company.id)]
        self.environment_label = (cfg.dgii_environment if cfg else "mock")
        self.cert_label = (
            _("Válido hasta %s") % cfg.certificate_id.date_end
            if cfg and cfg.certificate_id
            else _("Sin certificado")
        )
        self.count_accepted = Doc.search_count(domain + [("state", "=", "accepted")])
        self.count_rejected = Doc.search_count(domain + [("state", "=", "rejected")])
        self.count_pending = Doc.search_count(domain + [("state", "in", ["queued", "sent", "pending", "received_dgii"])])
        self.count_contingency = Doc.search_count(domain + [("contingency", "=", True)])
        self.count_retry = Doc.search_count(domain + [("state", "=", "retry")])
        self.count_queue = self.env["justech.ecf.queue.job"].search_count(
            [("company_id", "=", company.id), ("state", "in", ["pending", "running"])]
        ) if "justech.ecf.queue.job" in self.env else 0
        self.summary_html = (
            '<div class="o_jac_overview"><p>%s</p>'
            "<ul>"
            "<li>%s: <strong>%s</strong></li>"
            "<li>%s: <strong>%s</strong></li>"
            "</ul></div>"
        ) % (
            _("Indicadores accionables de e-CF para la empresa activa. Sin llamadas a Producción DGII."),
            _("Ambiente"),
            self.environment_label,
            _("Certificado"),
            self.cert_label,
        )

    def action_open_accepted(self):
        return self._open_docs([("state", "=", "accepted")], _("Aceptados"))

    def action_open_rejected(self):
        return self._open_docs([("state", "=", "rejected")], _("Rechazados"))

    def action_open_pending(self):
        return self._open_docs([("state", "in", ["queued", "sent", "pending", "received_dgii"])], _("Pendientes"))

    def action_open_contingency(self):
        return self._open_docs([("contingency", "=", True)], _("Contingencia"))

    def action_open_queue(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Cola e-CF"),
            "res_model": "justech.ecf.queue.job",
            "view_mode": "list,form",
            "domain": [("company_id", "=", self.company_id.id)],
        }

    def _open_docs(self, extra, name):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "justech.ecf.document",
            "view_mode": "list,form",
            "domain": [("company_id", "=", self.company_id.id)] + extra,
        }
