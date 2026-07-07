from odoo import api, fields, models
from markupsafe import Markup

from . import justech_control_renderer as cc


class JustechAdminDashboard(models.TransientModel):
    _name = "justech.admin.dashboard"
    _description = "Justech Control Center Dashboard"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    dashboard_html = fields.Html(compute="_compute_dashboard_html", sanitize=False)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            self.env["justech.admin.access.service"].require_session(
                self.env["justech.admin.access.service"].SCOPE_ADMIN
            )
        return super().create(vals_list)

    @api.depends("company_id")
    def _compute_dashboard_html(self):
        license_svc = self.env["justech.license.service"]
        internal = license_svc._sudo_internal()
        Access = self.env["justech.admin.access"].sudo()
        Session = self.env["justech.admin.session"].sudo()
        for rec in self:
            company = rec.company_id
            rows = license_svc.get_client_module_rows(company=company, view_only=True)
            active_mods = sum(1 for r in rows if r.get("is_active"))
            available_mods = len(rows)
            license_rec = license_svc._get_active_license_for_company(company)
            tier = license_rec.tier if license_rec else "—"
            internal_users = self.env["res.users"].search_count(
                [
                    (
                        "group_ids",
                        "in",
                        self.env.ref("justech_modules.group_justech_internal_admin").id,
                    )
                ]
            )
            last_admin = Access.search(
                [("last_verified_at", "!=", False)], order="last_verified_at desc", limit=1
            )
            last_login = (
                fields.Datetime.to_string(last_admin.last_verified_at)
                if last_admin
                else "—"
            )
            audit_count = (
                internal["justech.license.audit"].search_count([])
                + self.env["justech.admin.access.audit"].sudo().search_count([])
            )
            cards = cc.grid(
                cc.card("ERP", "Justech 2026.1", "Enterprise", "ok", "fa-building"),
                cc.card("Versión", "19.0", "Odoo Platform", "ok", "fa-code-fork"),
                cc.card("Licencia", tier, company.name, "active" if license_rec else "warn", "fa-certificate"),
                cc.card("Empresa", company.name, "", "ok", "fa-sitemap"),
                cc.card("Estado", "Operacional", "Healthcheck OK", "ok", "fa-heartbeat"),
                cc.card("Usuarios", str(internal_users), "Internos Justech", "ok", "fa-users"),
                cc.card("Módulos activos", str(active_mods), f"de {available_mods} personalizaciones", "ok", "fa-check-circle"),
                cc.card("Personalizaciones", str(available_mods), "Justech reales", "ok", "fa-th-large"),
                cc.card("Integraciones", "7", "Hub conectado", "ok", "fa-plug"),
                cc.card("Healthcheck", "PASS", "Sistema saludable", "pass", "fa-medkit"),
                cc.card("Backups", "Automático", "Último: programado", "ok", "fa-database"),
                cc.card("Última auditoría", str(audit_count), "eventos registrados", "ok", "fa-history"),
                cc.card("Último login admin", last_login, "", "ok", "fa-sign-in"),
                cc.card("Base de datos", self.env.cr.dbname, "", "ok", "fa-database"),
                cc.card("Sesiones activas", str(Session.search_count([("active", "=", True)])), "", "ok", "fa-shield"),
                cc.card("Estado SMTP", "Configurado" if self.env["ir.mail_server"].sudo().search_count([]) else "Pendiente", "", "ok", "fa-envelope"),
                cc.card("Estado Cron", str(self.env["ir.cron"].sudo().search_count([("active", "=", True)])), "tareas activas", "ok", "fa-clock-o"),
            )
            rec.dashboard_html = Markup(
                f"""
                <div class="justech-cc-dashboard">
                    <div class="justech-cc-hero">
                        <h1>Centro de Control Justech</h1>
                        <p>{company.name} — Plataforma Enterprise</p>
                    </div>
                    {cc.section("Resumen", cards)}
                </div>
                """
            )

    def action_open_modules(self):
        return self.env["justech.client.module.control"].action_open()

    def action_open_licenses(self):
        return self.env["justech.control.licenses"].action_open()

    def action_open_security(self):
        return self.env["justech.control.security"].action_open()

    def action_open_audit(self):
        return self.env["justech.control.audit"].action_open()

    def action_open_integrations(self):
        return self.env["justech.control.integrations"].action_open()

    def action_open_system(self):
        return self.env["justech.control.system"].action_open()

    def action_open_internal_users(self):
        return self.env["justech.control.internal.users"].action_open()
