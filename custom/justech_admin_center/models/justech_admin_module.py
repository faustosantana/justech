from odoo import api, fields, models, _


class JustechAdminModule(models.Model):
    _name = "justech.admin.module"
    _description = "Catálogo de módulo Justech"
    _order = "sequence, functional_name"

    name = fields.Char(related="functional_name", store=True)
    technical_name = fields.Char(required=True, index=True)
    functional_name = fields.Char(required=True)
    short_description = fields.Text(required=False)
    long_description = fields.Html(
        string="Descripción funcional",
        help="Qué es, para qué sirve, procesos, criticidad, activar/desactivar.",
    )
    what_it_does = fields.Text(string="Para qué se utiliza")
    processes_affected = fields.Text(string="Procesos que afecta")
    users_who_use_it = fields.Text(string="Usuarios típicos")
    risk_activate = fields.Text(string="Riesgo al activar")
    risk_deactivate = fields.Text(string="Riesgo al desactivar")
    product_id = fields.Many2one("justech.admin.product", string="Producto", ondelete="set null", index=True)
    activation_scope = fields.Selection(
        selection=[("global", "Global"), ("company", "Por empresa")],
        default="company",
        required=True,
    )
    fiscal_engine_capable = fields.Boolean(default=False)
    company_line_ids = fields.One2many("justech.admin.module.company", "module_id", string="Empresas")
    category = fields.Selection(
        selection=[
            ("platform", "Plataforma"),
            ("fiscal", "Fiscal"),
            ("payments", "Pagos"),
            ("treasury", "Tesorería"),
            ("audit", "Auditoría"),
            ("reports", "Reportes"),
            ("ux", "Experiencia"),
            ("integrations", "Integraciones"),
            ("other", "Otros"),
        ],
        default="other",
        required=True,
    )
    icon = fields.Char(default="fa-cube")
    sequence = fields.Integer(default=100)
    version = fields.Char()
    technical_state = fields.Selection(
        selection=[
            ("not_installed", "No instalado"),
            ("installed", "Instalado"),
            ("to_upgrade", "Por actualizar"),
            ("unavailable", "No disponible"),
        ],
        default="not_installed",
        required=True,
    )
    functional_state = fields.Selection(
        selection=[
            ("inactive", "Inactivo"),
            ("active", "Activo"),
            ("attention", "Requiere atención"),
            ("error", "Error"),
            ("unconfigured", "No configurado"),
        ],
        default="inactive",
        required=True,
    )
    status_visual = fields.Selection(
        selection=[
            ("green", "Correcto"),
            ("yellow", "Atención"),
            ("red", "Error"),
            ("blue", "Informativo"),
            ("grey", "No configurado"),
        ],
        compute="_compute_status_visual",
        store=True,
    )
    dependency_names = fields.Char(string="Dependencias")
    optional_dependency_names = fields.Char()
    open_action_xmlid = fields.Char()
    health_method = fields.Char()
    feature_flag_codes = fields.Char(help="Códigos separados por coma")
    supports_activate = fields.Boolean(default=True)
    supports_deactivate = fields.Boolean(default=True)
    is_critical = fields.Boolean(default=False)
    is_installable = fields.Boolean(default=True)
    last_sync_at = fields.Datetime()
    last_health_at = fields.Datetime()
    last_health_summary = fields.Char()
    company_active_count = fields.Integer(compute="_compute_company_stats")
    company_ids_display = fields.Char(compute="_compute_company_stats")
    ir_module_id = fields.Many2one("ir.module.module", string="Módulo Odoo", ondelete="set null")
    operation_ids = fields.One2many("justech.admin.operation", "module_id")
    audit_ids = fields.One2many("justech.admin.audit.log", "module_id")
    finding_ids = fields.One2many("justech.admin.health.finding", "module_id")
    active_finding_count = fields.Integer(compute="_compute_finding_count")

    _sql_constraints = [
        ("technical_name_uniq", "unique(technical_name)", "El módulo técnico ya está registrado."),
    ]

    @api.depends("technical_state", "functional_state", "active_finding_count")
    def _compute_status_visual(self):
        for rec in self:
            if rec.technical_state == "unavailable":
                rec.status_visual = "grey"
            elif rec.functional_state == "error" or rec.active_finding_count:
                rec.status_visual = "red" if rec.functional_state == "error" else "yellow"
            elif rec.technical_state == "not_installed":
                rec.status_visual = "grey"
            elif rec.functional_state == "attention":
                rec.status_visual = "yellow"
            elif rec.functional_state == "unconfigured":
                rec.status_visual = "blue"
            elif rec.functional_state == "active" and rec.technical_state == "installed":
                rec.status_visual = "green"
            else:
                rec.status_visual = "blue"

    def _compute_company_stats(self):
        Line = self.env["justech.admin.module.company"]
        for rec in self:
            lines = Line.search([("module_id", "=", rec.id), ("functional_state", "=", "active")])
            rec.company_active_count = len(lines)
            rec.company_ids_display = ", ".join(lines.mapped("company_id.name")[:6])

    def _compute_finding_count(self):
        Finding = self.env["justech.admin.health.finding"]
        for rec in self:
            rec.active_finding_count = Finding.search_count(
                [("module_id", "=", rec.id), ("state", "=", "open")]
            )

    def action_open_detail(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.functional_name,
            "res_model": "justech.admin.module",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_module(self):
        self.ensure_one()
        if self.open_action_xmlid:
            try:
                return self.env.ref(self.open_action_xmlid).sudo().read()[0]
            except ValueError:
                pass
        return self.action_open_detail()

    def action_prepare_install(self):
        self.ensure_one()
        return self.env["justech.admin.module.operation.wizard"].action_open_for_module(
            self, "install"
        )

    def action_prepare_activate(self):
        self.ensure_one()
        return self.env["justech.admin.module.operation.wizard"].action_open_for_module(
            self, "activate"
        )

    def action_prepare_deactivate(self):
        self.ensure_one()
        return self.env["justech.admin.module.operation.wizard"].action_open_for_module(
            self, "deactivate"
        )

    def action_run_health(self):
        self.ensure_one()
        return self.env["justech.admin.health.service"].run_module_health(self)

    def action_show_dependencies(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Dependencias"),
                "message": self.dependency_names or _("Sin dependencias declaradas."),
                "type": "info",
                "sticky": False,
            },
        }
