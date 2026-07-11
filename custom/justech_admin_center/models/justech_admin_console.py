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
    session_ok = fields.Boolean(compute="_compute_session_ok")
    product_count = fields.Integer(compute="_compute_kpis")
    installed_count = fields.Integer(compute="_compute_kpis")
    active_count = fields.Integer(compute="_compute_kpis")
    warning_count = fields.Integer(compute="_compute_kpis")
    error_count = fields.Integer(compute="_compute_kpis")
    company_count = fields.Integer(compute="_compute_kpis")
    justech_user_count = fields.Integer(compute="_compute_kpis")
    open_finding_count = fields.Integer(compute="_compute_kpis")
    recent_audit_count = fields.Integer(compute="_compute_kpis")
    dashboard_html = fields.Html(compute="_compute_kpis", sanitize=False)
    product_ids = fields.Many2many("justech.admin.product", compute="_compute_products")
    last_sync_at = fields.Datetime(readonly=True)

    def _compute_session_ok(self):
        Auth = self.env["justech.admin.center.auth.service"]
        for rec in self:
            try:
                rec.session_ok = Auth.is_session_valid()
            except Exception:
                rec.session_ok = False

    def _compute_products(self):
        products = self.env["justech.admin.product"].search([("active", "=", True)])
        for rec in self:
            rec.product_ids = products

    def _compute_kpis(self):
        Module = self.env["justech.admin.module"]
        Product = self.env["justech.admin.product"]
        Finding = self.env["justech.admin.health.finding"]
        Audit = self.env["justech.admin.audit.log"]
        Line = self.env["justech.admin.module.company"]
        companies = self.env["res.company"].search_count([])
        try:
            mgr = self.env.ref("justech_admin_center.group_justech_admin_center_manager")
            justech_users = self.env["res.users"].sudo().search_count(
                [("share", "=", False), ("group_ids", "in", mgr.id)]
            )
        except ValueError:
            justech_users = 0
        for rec in self:
            products = Product.search([("active", "=", True)])
            mods = Module.search([])
            rec.product_count = len(products)
            rec.installed_count = len(mods.filtered(lambda m: m.technical_state == "installed"))
            rec.active_count = Line.search_count([("functional_state", "=", "active")])
            rec.warning_count = len(mods.filtered(lambda m: m.status_visual == "yellow"))
            rec.error_count = len(mods.filtered(lambda m: m.status_visual == "red"))
            rec.company_count = companies
            rec.justech_user_count = justech_users
            rec.open_finding_count = Finding.search_count([("state", "=", "open")])
            rec.recent_audit_count = Audit.search_count([])
            rec.dashboard_html = self._render_dashboard(rec, products)

    @api.model
    def _render_dashboard(self, rec, products):
        parts = [
            '<div class="o_jac_enterprise">',
            '<div class="o_jac_brand_row"><div class="o_jac_brand_mark">J</div>',
            '<div><h2 class="o_jac_brand_title">Administración Justech</h2>',
            '<p class="o_jac_brand_sub">Ecosistema organizado · multiempresa · seguro</p></div></div>',
            '<div class="o_jac_kpi_grid">',
        ]
        cards = [
            (_("Productos"), rec.product_count, "blue"),
            (_("Módulos instalados"), rec.installed_count, "green"),
            (_("Activaciones por empresa"), rec.active_count, "green"),
            (_("Advertencias"), rec.warning_count, "yellow"),
            (_("Errores"), rec.error_count, "red"),
            (_("Empresas"), rec.company_count, "blue"),
            (_("Usuarios Justech"), rec.justech_user_count, "blue"),
            (_("Health pendientes"), rec.open_finding_count, "yellow" if rec.open_finding_count else "green"),
        ]
        for label, value, tone in cards:
            parts.append(
                '<div class="o_jac_kpi_card o_jac_tone_%s"><div class="o_jac_kpi_value">%s</div>'
                '<div class="o_jac_kpi_label">%s</div></div>' % (tone, value, label)
            )
        parts.append('</div><div class="o_jac_product_grid">')
        for p in products:
            parts.append(
                '<div class="o_jac_product_card o_jac_tone_%s">'
                '<div class="o_jac_product_head"><i class="fa %s"></i><strong>%s</strong></div>'
                '<p class="o_jac_product_desc">%s</p>'
                '<div class="o_jac_product_meta"><span>%s submódulos</span>'
                '<span>%s instalados</span><span>%s activos empresa</span></div></div>'
                % (
                    p.status_visual or "grey",
                    p.icon or "fa-cube",
                    p.name,
                    (p.short_description or "")[:180],
                    p.module_count,
                    p.installed_count,
                    p.active_company_count,
                )
            )
        parts.append("</div></div>")
        return "".join(parts)

    @api.model
    def _ensure_singleton(self):
        console = self.search([], limit=1)
        if not console:
            console = self.create({"name": "Administración Justech"})
        return console

    @api.model
    def action_open_console(self):
        Auth = self.env["justech.admin.center.auth.service"]
        Auth.require_authorized_user()
        if not Auth.is_session_valid():
            return self.env["justech.admin.auth.wizard"].action_open()
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
        self.env["justech.admin.center.auth.service"].require_session()
        self.env["justech.admin.registry.service"].discover_and_sync()
        self.write({"last_sync_at": fields.Datetime.now()})
        return True

    def action_run_diagnostics(self):
        self.env["justech.admin.center.auth.service"].require_session()
        return self.env["justech.admin.health.service"].run_global_diagnostics()

    def action_open_products(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Productos Justech"),
            "res_model": "justech.admin.product",
            "view_mode": "kanban,list,form",
            "target": "current",
        }

    def action_open_modules(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Catálogo de submódulos"),
            "res_model": "justech.admin.module",
            "view_mode": "kanban,list,form",
            "target": "current",
        }

    def action_open_company_matrix(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Estados por empresa"),
            "res_model": "justech.admin.module.company",
            "view_mode": "list,form",
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
            {"mode": "matrix", "preview_html": html}
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Matriz de permisos"),
            "res_model": "justech.admin.role.assign.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_reauth(self):
        return self.env["justech.admin.auth.wizard"].action_open()
