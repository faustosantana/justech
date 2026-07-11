from odoo import api, fields, models, _


class JustechAdminConsole(models.Model):
    _name = "justech.admin.console"
    _description = "Consola Administración Justech"

    name = fields.Char(default="Administración Justech", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa de contexto",
        default=lambda self: self.env.company,
    )
    module_count = fields.Integer(compute="_compute_kpis")
    installed_count = fields.Integer(compute="_compute_kpis")
    active_count = fields.Integer(compute="_compute_kpis")
    warning_count = fields.Integer(compute="_compute_kpis")
    error_count = fields.Integer(compute="_compute_kpis")
    company_count = fields.Integer(compute="_compute_kpis")
    justech_user_count = fields.Integer(compute="_compute_kpis")
    open_finding_count = fields.Integer(compute="_compute_kpis")
    recent_audit_count = fields.Integer(compute="_compute_kpis")
    kpi_summary = fields.Html(compute="_compute_kpis")
    module_ids = fields.Many2many(
        "justech.admin.module",
        compute="_compute_module_ids",
        string="Módulos",
    )
    last_sync_at = fields.Datetime(readonly=True)

    def _compute_module_ids(self):
        modules = self.env["justech.admin.module"].search([])
        for rec in self:
            rec.module_ids = modules

    def _compute_kpis(self):
        Module = self.env["justech.admin.module"]
        Finding = self.env["justech.admin.health.finding"]
        Audit = self.env["justech.admin.audit.log"]
        companies = self.env["res.company"].search_count([])
        try:
            mgr = self.env.ref("justech_admin_center.group_justech_admin_center_manager")
            justech_users = self.env["res.users"].sudo().search_count(
                [("share", "=", False), ("group_ids", "in", mgr.id)]
            )
        except ValueError:
            justech_users = 0
        for rec in self:
            mods = Module.search([])
            rec.module_count = len(mods)
            rec.installed_count = len(mods.filtered(lambda m: m.technical_state == "installed"))
            rec.active_count = len(mods.filtered(lambda m: m.functional_state == "active"))
            rec.warning_count = len(mods.filtered(lambda m: m.status_visual == "yellow"))
            rec.error_count = len(mods.filtered(lambda m: m.status_visual == "red"))
            rec.company_count = companies
            rec.justech_user_count = justech_users
            rec.open_finding_count = Finding.search_count([("state", "=", "open")])
            rec.recent_audit_count = Audit.search_count([])
            rec.kpi_summary = self._render_kpi_html(rec)

    @api.model
    def _render_kpi_html(self, rec):
        cards = [
            (_("Módulos instalados"), rec.installed_count, "green"),
            (_("Módulos activos"), rec.active_count, "green"),
            (_("Con advertencias"), rec.warning_count, "yellow"),
            (_("Con errores"), rec.error_count, "red"),
            (_("Empresas"), rec.company_count, "blue"),
            (_("Usuarios con roles Justech"), rec.justech_user_count, "blue"),
            (_("Health pendientes"), rec.open_finding_count, "yellow" if rec.open_finding_count else "green"),
            (_("Cambios auditados"), rec.recent_audit_count, "blue"),
        ]
        parts = ['<div class="o_jac_kpi_grid">']
        for label, value, tone in cards:
            parts.append(
                '<div class="o_jac_kpi_card o_jac_tone_%s"><div class="o_jac_kpi_value">%s</div>'
                '<div class="o_jac_kpi_label">%s</div></div>' % (tone, value, label)
            )
        parts.append("</div>")
        return "".join(parts)

    @api.model
    def _ensure_singleton(self):
        console = self.search([], limit=1)
        if not console:
            console = self.create({"name": "Administración Justech"})
        return console

    @api.model
    def action_open_console(self):
        console = self._ensure_singleton()
        self.env["justech.admin.registry.service"].discover_and_sync()
        console.write({"last_sync_at": fields.Datetime.now()})
        return {
            "type": "ir.actions.act_window",
            "name": _("Administración Justech"),
            "res_model": "justech.admin.console",
            "res_id": console.id,
            "view_mode": "form",
            "target": "current",
            "context": {"form_view_initial_mode": "readonly"},
        }

    def action_sync_catalog(self):
        self.env["justech.admin.registry.service"].discover_and_sync()
        self.write({"last_sync_at": fields.Datetime.now()})
        return True

    def action_run_diagnostics(self):
        return self.env["justech.admin.health.service"].run_global_diagnostics()

    def action_open_modules(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Catálogo de módulos"),
            "res_model": "justech.admin.module",
            "view_mode": "kanban,list,form",
            "target": "current",
        }

    def action_open_users(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Usuarios y roles Justech"),
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("share", "=", False)],
            "target": "current",
            "context": {"justech_admin_center_users": True},
        }

    def action_open_companies(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Empresas"),
            "res_model": "res.company",
            "view_mode": "list,form",
            "target": "current",
        }

    def action_open_audit(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría de cambios"),
            "res_model": "justech.admin.audit.log",
            "view_mode": "list,form",
            "target": "current",
        }

    def action_open_health(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Diagnóstico / Health Check"),
            "res_model": "justech.admin.health.finding",
            "view_mode": "list,form",
            "domain": [("state", "=", "open")],
            "target": "current",
        }

    def action_open_permission_matrix(self):
        html = self.env["justech.admin.permission.matrix.service"].render_html()
        wizard = self.env["justech.admin.role.assign.wizard"].create(
            {
                "mode": "matrix",
                "preview_html": html,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Matriz de permisos"),
            "res_model": "justech.admin.role.assign.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
