# -*- coding: utf-8 -*-
from datetime import date, timedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import justech_control_renderer as cc


def _commercial_license_status(license_rec):
    today = date.today()
    if license_rec.state == "revoked":
        return "suspended", _("Suspendida"), "gray", "⚪"
    if license_rec.state == "expired" or (
        license_rec.expires_at and license_rec.expires_at < today
    ):
        return "expired", _("Expirada"), "red", "🔴"
    if license_rec.state != "active":
        return "draft", _("Borrador"), "gray", "⚪"
    if license_rec.expires_at and license_rec.expires_at <= today + timedelta(days=30):
        return "expiring", _("Próxima a vencer"), "yellow", "🟡"
    return "active", _("Activa"), "green", "🟢"


class JustechControlLicenseCard(models.TransientModel):
    _name = "justech.control.license.card"
    _description = "Commercial License Kanban Card"
    _order = "client_name, id"

    hub_id = fields.Many2one("justech.control.licenses", ondelete="cascade")
    license_ref = fields.Integer()
    client_name = fields.Char(string="Cliente")
    primary_company = fields.Char(string="Empresa principal")
    plan_label = fields.Char(string="Plan")
    status_code = fields.Char()
    status_label = fields.Char(string="Estado")
    status_icon = fields.Char()
    status_class = fields.Char()
    starts_at_display = fields.Char(string="Inicio")
    expires_at_display = fields.Char(string="Vencimiento")
    companies_used = fields.Integer()
    companies_available = fields.Char()
    modules_active = fields.Integer()
    last_modified_display = fields.Char(string="Última modificación")

    def action_administer(self):
        self.ensure_one()
        return self.env["justech.control.license.dashboard"].action_open(
            self.license_ref, hub_id=self.hub_id.id if self.hub_id else False
        )


class JustechControlLicenseProductLine(models.TransientModel):
    _name = "justech.control.license.product.line"
    _description = "License Dashboard Product Row"
    _order = "sequence, name"

    dashboard_id = fields.Many2one(
        "justech.control.license.dashboard", ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    product_code = fields.Char()
    customization_code = fields.Char()
    name = fields.Char(string="Personalización")
    status_label = fields.Char(string="Estado")
    paid_label = fields.Char(string="Pagado")
    active_label = fields.Char(string="Activo")

    def action_administer(self):
        self.ensure_one()
        return self.dashboard_id._open_product_panel(
            self.product_code, self.customization_code
        )


class JustechControlLicenseDashboard(models.TransientModel):
    _name = "justech.control.license.dashboard"
    _description = "Commercial License Dashboard"

    license_ref = fields.Integer()
    hub_id = fields.Many2one("justech.control.licenses")
    client_name = fields.Char(readonly=True)
    plan_label = fields.Char(readonly=True)
    status_label = fields.Char(readonly=True)
    status_class = fields.Char(readonly=True)
    license_state = fields.Char(readonly=True)
    general_html = fields.Html(compute="_compute_sections", sanitize=False)
    companies_html = fields.Html(compute="_compute_sections", sanitize=False)
    plan_html = fields.Html(compute="_compute_sections", sanitize=False)
    audit_html = fields.Html(compute="_compute_audit", sanitize=False)
    primary_company_id = fields.Integer()
    product_line_ids = fields.One2many(
        "justech.control.license.product.line", "dashboard_id"
    )

    @api.model
    def action_open(self, license_ref, hub_id=False):
        rec = self.create({"license_ref": license_ref, "hub_id": hub_id})
        rec._load_product_lines()
        return {
            "type": "ir.actions.act_window",
            "name": _("Administrar licencia"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    def _license_rec(self):
        self.ensure_one()
        return (
            self.env["justech.license.service"]
            ._sudo_internal()["justech.license"]
            .browse(self.license_ref)
        )

    def _open_wizard(self, mode, extra_context=None):
        self.ensure_one()
        lic = self._license_rec()
        primary = lic.company_line_ids[:1].company_id or self.env.company
        ctx = {
            "default_mode": mode,
            "default_license_id": lic.id,
            "default_company_id": primary.id,
            "default_control_id": self.hub_id.id if self.hub_id else False,
            "default_dashboard_id": self.id,
        }
        if extra_context:
            ctx.update(extra_context)
        return {
            "type": "ir.actions.act_window",
            "name": dict(
                self.env["justech.license.admin.wizard"]._fields["mode"].selection
            ).get(mode, _("Licencia")),
            "res_model": "justech.license.admin.wizard",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def _open_product_panel(self, product_code, customization_code=None):
        self.ensure_one()
        if not product_code:
            raise UserError(_("Personalización no disponible."))
        lic = self._license_rec()
        primary = lic.company_line_ids[:1].company_id or self.env.company
        control = self.env["justech.client.module.control"].create(
            {
                "license_id": lic.id,
                "company_id": primary.id,
            }
        )
        control._reload_lines()
        line = control.line_ids.filtered(
            lambda row: row.product_code == product_code
            or (
                customization_code
                and row.main_module_code == customization_code
            )
        )[:1]
        if not line:
            raise UserError(_("Personalización no encontrada en Módulos del Cliente."))
        return self.env["justech.client.module.admin.panel"].action_open_for_line(line)

    def action_change_plan(self):
        return self._open_wizard("change_plan")

    def action_activate(self):
        return self._open_wizard("activate")

    def action_renew(self):
        lic = self._license_rec()
        new_exp = (
            (lic.expires_at or date.today()) + timedelta(days=365)
            if lic.expires_at
            else date.today() + timedelta(days=365)
        )
        return self._open_wizard(
            "renew",
            {
                "default_expires_at": new_exp,
                "default_starts_at": lic.starts_at or date.today(),
            },
        )

    def action_suspend(self):
        return self._open_wizard("suspend")

    def action_reactivate(self):
        return self._open_wizard("reactivate")

    def action_add_company(self):
        return self._open_wizard("add_company")

    def action_remove_company(self):
        return self._open_wizard("remove_company")

    def action_set_primary_company(self):
        return self._open_wizard("set_primary_company")

    def action_back_to_hub(self):
        if self.hub_id:
            return self.hub_id.action_reopen()
        return self.env["justech.control.licenses"].action_open()

    def _load_product_lines(self):
        license_svc = self.env["justech.license.service"]
        for rec in self:
            lic = rec._license_rec()
            if not lic.exists():
                rec.product_line_ids = [(5, 0, 0)]
                continue
            primary = lic.company_line_ids[:1].company_id or self.env.company
            rows = license_svc.get_client_module_rows(
                company=primary, license_id=lic.id, view_only=True
            )
            commands = [(5, 0, 0)]
            seq = 10
            for row in rows:
                if row.get("internal_only"):
                    continue
                commands.append(
                    (
                        0,
                        0,
                        {
                            "sequence": seq,
                            "product_code": row.get("product_code"),
                            "customization_code": row.get("main_module_code"),
                            "name": row.get("display_name") or row.get("name"),
                            "status_label": row.get("status_label") or "—",
                            "paid_label": _("Sí")
                            if row.get("is_paid")
                            else _("No"),
                            "active_label": row.get("active_label")
                            or row.get("status_label")
                            or "—",
                        },
                    )
                )
                seq += 10
            rec.product_line_ids = commands

    @api.depends("license_ref")
    def _compute_sections(self):
        license_svc = self.env["justech.license.service"]
        internal = license_svc._sudo_internal()
        internal_group = self.env.ref("justech_modules.group_justech_internal_admin")
        for rec in self:
            lic = internal["justech.license"].browse(rec.license_ref)
            if not lic.exists():
                rec.general_html = Markup(
                    cc.alert("warning", _("Licencia no encontrada."))
                )
                rec.companies_html = False
                rec.plan_html = False
                continue
            _code, status_label, status_class, status_icon = _commercial_license_status(
                lic
            )
            rec.client_name = lic.name
            rec.plan_label = license_svc._tier_commercial_label(lic.tier)
            rec.license_state = lic.state
            rec.status_label = f"{status_icon} {status_label}"
            rec.status_class = status_class
            primary = lic.company_line_ids[:1].company_id
            rec.primary_company_id = primary.id if primary else self.env.company.id
            used = len(lic.company_line_ids)
            max_c = lic.max_companies or 0
            available = str(max(max_c - used, 0)) if max_c else _("Ilimitadas")
            admin_users = self.env["res.users"].search_count(
                [("share", "=", False), ("group_ids", "in", internal_group.id)]
            )
            rec.general_html = Markup(
                cc.grid(
                    cc.card(_("Cliente"), lic.name, "", "ok", "fa-building"),
                    cc.card(_("Plan"), rec.plan_label, "", "ok", "fa-certificate"),
                    cc.card(
                        _("Estado"), rec.status_label, "", status_class, "fa-flag"
                    ),
                    cc.card(
                        _("Inicio"),
                        str(lic.starts_at or "—"),
                        "",
                        "ok",
                        "fa-calendar-check-o",
                    ),
                    cc.card(
                        _("Vencimiento"),
                        str(lic.expires_at or "—"),
                        "",
                        status_class if status_class != "green" else "ok",
                        "fa-calendar",
                    ),
                    cc.card(_("Empresas usadas"), str(used), "", "ok", "fa-sitemap"),
                    cc.card(
                        _("Empresas disponibles"), available, "", "ok", "fa-plus-square"
                    ),
                    cc.card(
                        _("Administradores"),
                        str(admin_users),
                        _("usuarios internos"),
                        "ok",
                        "fa-user-secret",
                    ),
                )
            )
            company_lines = []
            for line in lic.company_line_ids:
                marker = _("Principal") if line.company_id == primary else ""
                company_lines.append(
                    cc.card(
                        line.company_id.name,
                        marker or _("Asociada"),
                        "",
                        "ok" if line.company_id == primary else "inactive",
                        "fa-building-o",
                    )
                )
            rec.companies_html = Markup(
                cc.section(
                    _("Empresas"),
                    cc.grid(*company_lines)
                    if company_lines
                    else cc.alert("info", _("Sin empresas asociadas.")),
                )
            )
            rec.plan_html = Markup(
                cc.section(
                    _("Plan"),
                    cc.grid(
                        cc.card(
                            _("Plan actual"), rec.plan_label, "", "ok", "fa-certificate"
                        ),
                        cc.card(
                            _("Renovación"),
                            str(lic.expires_at or "—"),
                            _("fecha de vencimiento"),
                            status_class if status_class != "green" else "ok",
                            "fa-refresh",
                        ),
                    ),
                )
            )

    @api.depends("license_ref")
    def _compute_audit(self):
        license_svc = self.env["justech.license.service"]
        Audit = license_svc._sudo_internal()["justech.license.audit"]
        action_map = {
            "activate": _("Activación"),
            "register": _("Registro"),
            "validate": _("Validación"),
            "deactivate": _("Desactivación"),
            "revoke": _("Revocación"),
            "expire": _("Expiración"),
        }
        for rec in self:
            events = []
            for row in Audit.search([("license_id", "=", rec.license_ref)], limit=12):
                detail = (row.details or {}) if isinstance(row.details, dict) else {}
                label = action_map.get(row.action, row.action)
                if detail.get("action") == "change_plan":
                    label = _("Cambio de plan")
                elif detail.get("action") == "add_company":
                    label = _("Empresa agregada")
                elif detail.get("action") == "remove_company":
                    label = _("Empresa removida")
                events.append(
                    f"<li><strong>{label}</strong> — {row.user_id.name or _('Sistema')} "
                    f"<span class='text-muted'>{row.create_date}</span></li>"
                )
            rec.audit_html = Markup(
                cc.section(
                    _("Auditoría reciente"),
                    f"<ul class='justech-cc-audit-list'>{''.join(events) or '<li>' + _('Sin eventos') + '</li>'}</ul>",
                )
            )
