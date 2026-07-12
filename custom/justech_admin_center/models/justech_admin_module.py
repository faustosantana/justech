from odoo import api, fields, models, _
from odoo.exceptions import UserError


# Acciones administrativas dedicadas por submódulo (nunca abrir pantallas ajenas)
ADMIN_ACTIONS = {
    "justech_l10n_do_base": {
        "admin": "justech_admin_center.action_justech_admin_padron_hub",
        "configure": "justech_l10n_do_base.action_justech_do_rnc_padron_config_server",
        "operation": "justech_l10n_do_base.action_justech_do_rnc_padron_import",
        "status": "justech_l10n_do_base.action_justech_do_rnc_padron",
    },
    "justech_l10n_do_ncf": {
        "admin": "justech_l10n_do_ncf.action_justech_do_ncf_range",
        "configure": "justech_l10n_do_ncf.action_justech_do_ncf_range",
        "operation": "justech_l10n_do_ncf.action_justech_do_ncf_consumption",
        "status": "justech_l10n_do_ncf.action_justech_do_fiscal_diagnostic",
    },
    "justech_l10n_do_reports": {
        "admin": "justech_l10n_do_reports.action_justech_do_fiscal_report",
        "configure": "justech_l10n_do_reports.action_justech_do_fiscal_report_wizard",
        "operation": "justech_l10n_do_reports.action_justech_do_report_606",
        "status": "justech_l10n_do_reports.action_justech_do_fiscal_review_pending",
    },
    "justech_l10n_do_adel_freeze": {
        "admin": "justech_fiscal_admin.action_justech_fiscal_admin_center_server",
        "configure": "justech_fiscal_admin.action_justech_fiscal_feature_flags",
        "operation": "justech_fiscal_admin.action_justech_fiscal_admin_center_server",
        "status": "justech_admin_center.action_justech_admin_health",
    },
    "justech_fiscal_admin": {
        # Hub propio de la consola — no la pantalla antigua mezclada
        "admin": "justech_admin_center.action_justech_admin_fiscal_hub",
        "configure": "justech_fiscal_admin.action_justech_fiscal_feature_flags",
        "operation": "justech_fiscal_admin.action_justech_fiscal_admin_center_server",
        "status": "justech_admin_center.action_justech_admin_fiscal_hub",
    },
    "justech_l10n_do_payments_withholding": {
        "admin": "justech_l10n_do_reports.action_justech_do_withholding_catalog",
        "configure": "justech_l10n_do_reports.action_justech_do_withholding_catalog",
        "operation": "justech_l10n_do_payments_withholding.action_justech_register_customer_payment",
        "status": "justech_l10n_do_reports.action_justech_do_report_623",
    },
    "justech_l10n_do_treasury": {
        "admin": "justech_admin_center.action_justech_admin_treasury_hub",
        "configure": "justech_l10n_do_treasury.action_justech_bank_reconciliation",
        "operation": "justech_l10n_do_treasury.action_treasury_open_payments_customer",
        "status": "justech_l10n_do_treasury.action_treasury_open_payments_vendor",
    },
    "justech_warranty": {
        "admin": "justech_warranty.action_justech_warranty_dashboard",
        "configure": "justech_warranty.action_justech_warranty_config_settings",
        "operation": "justech_warranty.action_justech_warranty",
        "status": "justech_warranty.action_justech_warranty_claim",
    },
    "justech_admin_center": {
        "admin": "justech_admin_center.action_justech_admin_console",
        "configure": "justech_admin_center.action_justech_admin_console",
        "operation": "justech_admin_center.action_justech_admin_health",
        "status": "justech_admin_center.action_justech_admin_health",
    },
    "justech_global_audit_log": {
        "admin": "justech_global_audit_log.action_justech_audit_dashboard",
        "configure": "justech_global_audit_log.action_justech_audit_rule",
        "operation": "justech_global_audit_log.action_justech_audit_log",
        "status": "justech_global_audit_log.action_justech_audit_dashboard",
    },
    "justech_ecf_admin": {
        "admin": "justech_ecf_admin.action_justech_ecf_admin_hub",
        "configure": "justech_ecf_core.action_justech_ecf_company_config",
        "operation": "justech_ecf_admin.action_justech_ecf_dashboard",
        "status": "justech_ecf_admin.action_justech_ecf_dashboard",
    },
    "justech_ecf_core": {
        "admin": "justech_ecf_admin.action_justech_ecf_admin_hub",
        "configure": "justech_ecf_core.action_justech_ecf_company_config",
        "operation": "justech_ecf_core.action_justech_ecf_document",
        "status": "justech_ecf_admin.action_justech_ecf_dashboard",
    },
}

GLOBAL_TECH = {
    "justech_admin_center",
    "justech_modules",
    "justech_core",
    "justech_l10n_do_base",
    "justech_global_audit_log",
}


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
        string="Alcance",
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
        string="Categoría",
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
        string="Estado técnico",
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
        string="Estado funcional",
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
    has_operation_action = fields.Boolean(
        string="Tiene operación",
        compute="_compute_has_operation_action",
    )
    company_active_count = fields.Integer(compute="_compute_company_stats")
    company_ids_display = fields.Char(compute="_compute_company_stats")
    coverage_label = fields.Char(compute="_compute_company_stats", string="Cobertura")
    ir_module_id = fields.Many2one("ir.module.module", string="Módulo Odoo", ondelete="set null")
    operation_ids = fields.One2many("justech.admin.operation", "module_id")
    audit_ids = fields.One2many("justech.admin.audit.log", "module_id")
    finding_ids = fields.One2many("justech.admin.health.finding", "module_id")
    active_finding_count = fields.Integer(compute="_compute_finding_count")
    overview_html = fields.Html(compute="_compute_overview_html", sanitize=False)
    estado_general = fields.Char(compute="_compute_overview_html", string="Estado general")
    dependency_help = fields.Text(compute="_compute_overview_html", string="Dependencias")
    functions_help = fields.Html(compute="_compute_overview_html", sanitize=False, string="Funciones incluidas")
    is_global = fields.Boolean(compute="_compute_is_global")

    _sql_constraints = [
        ("technical_name_uniq", "unique(technical_name)", "El módulo técnico ya está registrado."),
    ]

    @api.depends("activation_scope")
    def _compute_is_global(self):
        for rec in self:
            rec.is_global = rec.activation_scope == "global"

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
        company_total = self.env["res.company"].search_count([])
        for rec in self:
            if rec.activation_scope == "global":
                rec.company_active_count = company_total
                rec.company_ids_display = _("Todas")
                rec.coverage_label = _("Global — disponible para las %s empresas") % company_total
                continue
            lines = Line.search([("module_id", "=", rec.id), ("functional_state", "=", "active")])
            rec.company_active_count = len(lines)
            rec.company_ids_display = ", ".join(lines.mapped("company_id.name")[:6])
            rec.coverage_label = _("Activo en %s empresas") % len(lines)

    def _compute_finding_count(self):
        Finding = self.env["justech.admin.health.finding"]
        for rec in self:
            rec.active_finding_count = Finding.search_count(
                [("module_id", "=", rec.id), ("state", "=", "open")]
            )

    def _compute_overview_html(self):
        for rec in self:
            if rec.technical_state == "not_installed":
                estado = _("No instalado")
            elif rec.functional_state == "error" or rec.active_finding_count:
                estado = _("Error") if rec.functional_state == "error" else _("Requiere atención")
            elif rec.activation_scope == "global" and rec.technical_state == "installed":
                estado = _("Activo (global)")
            elif rec.functional_state == "active":
                estado = _("Activo")
            elif rec.functional_state == "unconfigured":
                estado = _("No configurado")
            elif rec.technical_state == "installed":
                estado = _("Instalado / inactivo")
            else:
                estado = _("Requiere atención")
            rec.estado_general = estado

            deps = [d.strip() for d in (rec.dependency_names or "").split(",") if d.strip()]
            Module = self.env["justech.admin.module"]
            labels = []
            for d in deps:
                other = Module.search([("technical_name", "=", d)], limit=1)
                labels.append(
                    other.functional_name
                    if other
                    else d.replace("justech_", "").replace("_", " ").title()
                )
            if labels:
                rec.dependency_help = _(
                    "Este producto necesita: %s. Si falta alguna dependencia, "
                    "no podrá activarse de forma segura hasta instalarla."
                ) % (", ".join(labels))
            else:
                rec.dependency_help = _("No declara dependencias Justech adicionales.")

            bullets = []
            if rec.what_it_does:
                bullets.append(rec.what_it_does)
            if rec.processes_affected:
                bullets.append(_("Procesos: %s") % rec.processes_affected)
            if rec.users_who_use_it:
                bullets.append(_("Usuarios: %s") % rec.users_who_use_it)
            if rec.fiscal_engine_capable:
                bullets.append(
                    _("Permite seleccionar motor fiscal por empresa (NCF tradicional o electrónico).")
                )
            if rec.is_critical:
                bullets.append(_("Es crítico para la operación: desactivarlo requiere alternativa."))
            if not bullets:
                bullets.append(rec.short_description or _("Sin descripción funcional."))
            funcs = "".join("<li>%s</li>" % b for b in bullets)
            rec.functions_help = "<ul class='o_jac_func_list'>%s</ul>" % funcs

            crit = _("Sí") if rec.is_critical else _("No")
            scope = _("Global") if rec.activation_scope == "global" else _("Por empresa")
            rec.overview_html = (
                '<div class="o_jac_overview">'
                "<p><strong>%(what)s</strong></p>"
                "<p>%(desc)s</p>"
                '<div class="o_jac_overview_meta">'
                "<span>%(estado_l)s: <strong>%(estado)s</strong></span>"
                "<span>%(crit_l)s: <strong>%(crit)s</strong></span>"
                "<span>%(scope_l)s: <strong>%(scope)s</strong></span>"
                "<span>%(co_l)s: <strong>%(co)s</strong></span>"
                "</div></div>"
            ) % {
                "what": rec.functional_name,
                "desc": rec.short_description
                or _("Complete la descripción funcional de este módulo."),
                "estado_l": _("Estado general"),
                "estado": estado,
                "crit_l": _("¿Es crítico?"),
                "crit": crit,
                "scope_l": _("Alcance"),
                "scope": scope,
                "co_l": _("Cobertura"),
                "co": rec.coverage_label,
            }

    def _resolve_action(self, key):
        self.ensure_one()
        cfg = ADMIN_ACTIONS.get(self.technical_name) or {}
        xmlid = cfg.get(key) or (self.open_action_xmlid if key == "admin" else False)
        if not xmlid:
            return False
        try:
            return self.env.ref(xmlid).sudo()
        except ValueError:
            return False

    def _run_action(self, key):
        act = self._resolve_action(key)
        if not act:
            return False
        if act._name == "ir.actions.server":
            return act.run()
        data = act.read()[0]
        data.pop("id", None)
        return data

    def check_access(self, operation):
        res = super().check_access(operation)
        if self.env.su or not self.env.registry.ready:
            return res
        try:
            Auth = self.env["justech.admin.center.auth.service"]
        except KeyError:
            return res
        if Auth.user_is_authorized() and not Auth.is_session_valid():
            from odoo.exceptions import AccessError

            raise AccessError(
                _("Debe abrir Administración Justech e introducir la clave maestra antes de continuar.")
            )
        return res


    @api.depends("technical_name", "open_action_xmlid")
    def _compute_has_operation_action(self):
        for rec in self:
            cfg = ADMIN_ACTIONS.get(rec.technical_name) or {}
            rec.has_operation_action = bool(cfg.get("operation") or False)

    def action_open_detail(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": self.functional_name,
            "res_model": "justech.admin.module",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_admin(self):
        """Administrar: pantalla dedicada del submódulo."""
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        action = self._run_action("admin")
        if action:
            return action
        return self.action_open_detail()

    def action_configure(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        action = self._run_action("configure")
        if action:
            return action
        return self.action_open_detail()

    def action_open_operation(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        action = self._run_action("operation")
        if action:
            return action
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sin operación directa"),
                "message": _("Use Administrar o Configurar para este submódulo."),
                "type": "info",
            },
        }

    def action_view_status(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        action = self._run_action("status")
        if action:
            return action
        return self.action_run_health()

    # Compatibilidad: no abrir pantallas genéricas mezcladas
    def action_open_module(self):
        return self.action_open_admin()

    def action_prepare_install(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return self.env["justech.admin.module.operation.wizard"].action_open_for_module(
            self, "install"
        )

    def action_prepare_activate(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        if self.activation_scope == "global":
            raise UserError(
                _("%s es global. No se activa por empresa desde este asistente.")
                % self.functional_name
            )
        return self.env["justech.admin.module.operation.wizard"].action_open_for_module(
            self, "activate"
        )

    def action_prepare_deactivate(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return self.env["justech.admin.module.operation.wizard"].action_open_for_module(
            self, "deactivate"
        )

    def action_run_health(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return self.env["justech.admin.health.service"].run_module_health(self, open_findings=True)

    def action_diagnose(self):
        """Alias explícito: Diagnosticar siempre ejecuta controles reales."""
        return self.action_run_health()

    def action_open_users(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Usuarios y roles"),
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("share", "=", False), ("justech_is_test_user", "=", False)],
            "target": "current",
        }

    def action_open_audit(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría"),
            "res_model": "justech.admin.audit.log",
            "view_mode": "list,form",
            "domain": [("module_id", "=", self.id)],
            "target": "current",
        }

    def action_show_dependencies(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Dependencias"),
                "message": self.dependency_help or _("Sin dependencias declaradas."),
                "type": "info",
                "sticky": False,
            },
        }
