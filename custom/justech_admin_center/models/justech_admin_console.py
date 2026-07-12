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
    product_count = fields.Integer(compute="_compute_kpis", string="Productos")
    installed_count = fields.Integer(compute="_compute_kpis", string="Módulos instalados")
    active_count = fields.Integer(compute="_compute_kpis", string="Activaciones por empresa")
    warning_count = fields.Integer(compute="_compute_kpis", string="Advertencias")
    error_count = fields.Integer(compute="_compute_kpis", string="Errores")
    company_count = fields.Integer(compute="_compute_kpis", string="Empresas")
    justech_user_count = fields.Integer(compute="_compute_kpis", string="Usuarios Justech")
    open_finding_count = fields.Integer(compute="_compute_kpis", string="Revisiones pendientes")
    recent_audit_count = fields.Integer(compute="_compute_kpis", string="Cambios recientes")
    header_html = fields.Html(compute="_compute_kpis", sanitize=False)
    product_ids = fields.Many2many("justech.admin.product", compute="_compute_products")
    last_sync_at = fields.Datetime(readonly=True, string="Última sincronización")
    search_text = fields.Char(string="Buscar")
    filter_company_id = fields.Many2one("res.company", string="Filtrar por empresa")
    uat_user_count = fields.Integer(compute="_compute_uat", string="Usuarios de prueba")
    uat_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_uat",
        string="Usuarios de prueba",
    )
    real_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_uat",
        string="Usuarios reales",
    )

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
            domain_products = products
            if rec.search_text:
                text = rec.search_text.strip().lower()
                domain_products = products.filtered(
                    lambda p: text in (p.name or "").lower()
                    or text in (p.short_description or "").lower()
                    or any(text in (m.functional_name or "").lower() for m in p.module_ids)
                )
            rec.product_ids = domain_products

    def _compute_uat(self):
        users = self.env["res.users"].sudo().search([("share", "=", False)])
        uat = users.filtered(lambda u: u.justech_is_test_user)
        real = users.filtered(lambda u: not u.justech_is_test_user and u.active)
        for rec in self:
            rec.uat_user_ids = uat
            rec.real_user_ids = real
            rec.uat_user_count = len(uat.filtered("active"))

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
                [
                    ("share", "=", False),
                    ("group_ids", "in", mgr.id),
                    ("justech_is_test_user", "=", False),
                ]
            )
        except ValueError:
            justech_users = 0
        for rec in self:
            products = Product.search([("active", "=", True)])
            mods = Module.search([])
            rec.product_count = len(products)
            rec.installed_count = len(mods.filtered(lambda m: m.technical_state == "installed"))
            # Solo activaciones por empresa (excluye líneas de módulos globales)
            rec.active_count = Line.search_count(
                [
                    ("functional_state", "=", "active"),
                    ("module_id.activation_scope", "=", "company"),
                ]
            )
            rec.warning_count = len(mods.filtered(lambda m: m.status_visual == "yellow"))
            rec.error_count = len(mods.filtered(lambda m: m.status_visual == "red"))
            rec.company_count = companies
            rec.justech_user_count = justech_users
            rec.open_finding_count = Finding.search_count([("state", "=", "open")])
            rec.recent_audit_count = Audit.search_count([])
            rec.header_html = (
                '<div class="o_jac_enterprise">'
                '<div class="o_jac_brand_row"><div class="o_jac_brand_mark" aria-hidden="true">J</div>'
                "<div><h2 class=\"o_jac_brand_title\">%s</h2>"
                '<p class="o_jac_brand_sub">%s</p></div></div></div>'
            ) % (
                _("Administración Justech"),
                _("Ecosistema organizado · multiempresa · seguro"),
            )

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
        wizard = Auth.gate_or_wizard()
        if wizard:
            return wizard
        console = self._ensure_singleton()
        self.env["justech.admin.product"].dedupe_by_code()
        self.env["justech.admin.registry.service"].discover_and_sync()
        self.env["justech.admin.product"].refresh_blurbs()
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
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        self.env["justech.admin.registry.service"].discover_and_sync()
        self.env["justech.admin.product"].refresh_blurbs()
        self.write({"last_sync_at": fields.Datetime.now()})
        return True

    def action_run_diagnostics(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return self.env["justech.admin.health.service"].run_global_diagnostics()

    def action_open_products(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Productos Justech"),
            "res_model": "justech.admin.product",
            "view_mode": "kanban,list,form",
            "target": "current",
        }

    def action_open_modules(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Catálogo de submódulos"),
            "res_model": "justech.admin.module",
            "view_mode": "kanban,list,form",
            "target": "current",
        }

    def action_open_warnings(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Advertencias"),
            "res_model": "justech.admin.module",
            "view_mode": "list,form",
            "domain": [("status_visual", "=", "yellow")],
            "target": "current",
        }

    def action_open_errors(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Errores"),
            "res_model": "justech.admin.module",
            "view_mode": "list,form",
            "domain": [("status_visual", "=", "red")],
            "target": "current",
        }

    def action_open_company_matrix(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Estados por empresa"),
            "res_model": "justech.admin.module.company",
            "view_mode": "list,form",
            "target": "current",
        }

    def action_open_users(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Usuarios y roles Justech"),
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("share", "=", False), ("justech_is_test_user", "=", False)],
            "target": "current",
        }

    def action_open_uat_users(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Usuarios de prueba"),
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("share", "=", False), ("justech_is_test_user", "=", True)],
            "context": {"search_default_active": 1},
            "target": "current",
        }

    def action_archive_uat_users(self):
        return self.env["justech.admin.uat.archive.wizard"].action_open()

    def action_open_companies(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Empresas"),
            "res_model": "res.company",
            "view_mode": "list,form",
            "target": "current",
        }

    def action_open_audit(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría de cambios"),
            "res_model": "justech.admin.audit.log",
            "view_mode": "list,form",
            "target": "current",
        }

    def action_open_health(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Estado del sistema"),
            "res_model": "justech.admin.health.finding",
            "view_mode": "list,form",
            "domain": [("state", "=", "open")],
            "target": "current",
        }

    def action_open_permission_matrix(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
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
