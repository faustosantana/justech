# -*- coding: utf-8 -*-
from datetime import datetime

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import justech_control_renderer as cc
from .justech_control_license_commercial import _commercial_license_status


class JustechControlModuleCatalog(models.TransientModel):
    _name = "justech.control.module.catalog"
    _description = "Commercial Module Catalog"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    card_ids = fields.One2many("justech.control.module.card", "catalog_id")
    catalog_html = fields.Html(compute="_compute_catalog_html", sanitize=False)

    @api.model
    def action_open(self):
        self._require_admin_session()
        rec = self.create({"company_id": self.env.company.id})
        rec._load_cards()
        return {
            "type": "ir.actions.act_window",
            "name": _("Módulos"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends("card_ids", "card_ids.status")
    def _compute_catalog_html(self):
        for rec in self:
            cards = []
            for line in rec.card_ids:
                cards.append(
                    cc.card(
                        line.name,
                        line.status_label,
                        line.category_label,
                        line.status,
                        line.icon or "fa-cube",
                    )
                )
            rec.catalog_html = Markup(cc.grid(*cards) if cards else "<p>Sin módulos.</p>")

    def _load_cards(self):
        license_svc = self.env["justech.license.service"]
        rows = license_svc.get_client_module_rows(
            company=self.company_id, view_only=True
        )
        status_map = {
            "paid_active": "active",
            "partial": "partial",
            "paid_inactive": "inactive",
            "not_paid": "inactive",
            "blocked": "inactive",
            "expired": "inactive",
            "coming_soon": "unavailable",
        }
        status_labels = {
            "active": _("Activo"),
            "partial": _("Parcial"),
            "inactive": _("Inactivo"),
            "unavailable": _("No disponible"),
        }
        commands = [(5, 0, 0)]
        for row in rows:
            status = status_map.get(row.get("status"), "inactive")
            commands.append(
                (
                    0,
                    0,
                    {
                        "product_code": row.get("product_code") or row.get("main_module_code"),
                        "name": row["name"],
                        "description": row.get("description") or "",
                        "icon": "fa-cube",
                        "category_label": _("Personalización Justech"),
                        "status": status,
                        "status_label": status_labels.get(status, status),
                        "license_tier_label": row.get("license_label") or "—",
                        "version": "—",
                    },
                )
            )
        self.card_ids = commands

    def action_open_product(self):
        self.ensure_one()
        card = self.card_ids.filtered(lambda c: c.id == self.env.context.get("active_card_id"))
        if not card:
            card = self.card_ids[:1]
        if not card:
            raise UserError(_("No hay módulos en el catálogo."))
        return self.env["justech.control.module.sheet"].action_open(
            card.product_code, company=self.company_id
        )

    @api.model
    def _require_admin_session(self):
        self.env["justech.admin.access.service"].require_session(
            self.env["justech.admin.access.service"].SCOPE_ADMIN
        )


class JustechControlModuleCard(models.TransientModel):
    _name = "justech.control.module.card"
    _description = "Commercial Module Card"
    _order = "sequence, name"

    catalog_id = fields.Many2one("justech.control.module.catalog", ondelete="cascade")
    sequence = fields.Integer(default=10)
    product_code = fields.Char(required=True)
    name = fields.Char(required=True)
    description = fields.Text()
    icon = fields.Char()
    category_label = fields.Char()
    status = fields.Char()
    status_label = fields.Char()
    license_tier_label = fields.Char()
    version = fields.Char()

    def action_open_sheet(self):
        self.ensure_one()
        return self.env["justech.control.module.sheet"].action_open(
            self.product_code, company=self.catalog_id.company_id
        )


class JustechControlModuleSheet(models.TransientModel):
    _name = "justech.control.module.sheet"
    _description = "Commercial Module Detail Sheet"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    product_code = fields.Char(required=True)
    name = fields.Char(readonly=True)
    description = fields.Text(readonly=True)
    status = fields.Char(readonly=True)
    status_label = fields.Char(readonly=True)
    license_tier_label = fields.Char(readonly=True)
    version = fields.Char(readonly=True)
    category_label = fields.Char(readonly=True)
    dependencies_text = fields.Char(readonly=True)
    company_name = fields.Char(readonly=True)
    header_html = fields.Html(compute="_compute_header_html", sanitize=False)
    feature_ids = fields.One2many("justech.control.module.feature", "sheet_id")

    @api.model
    def action_open(self, product_code, company=None):
        JustechControlModuleCatalog._require_admin_session(self)
        company = company or self.env.company
        rec = self.create({"product_code": product_code, "company_id": company.id})
        rec._load_from_catalog()
        return {
            "type": "ir.actions.act_window",
            "name": rec.name or _("Módulo"),
            "res_model": rec._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends("name", "status_label", "license_tier_label", "version", "dependencies_text")
    def _compute_header_html(self):
        status_labels = {"active": "Activo", "partial": "Parcial", "inactive": "Inactivo", "unavailable": "Próximamente"}
        for rec in self:
            st = status_labels.get(rec.status, rec.status_label or "—")
            deps = rec.dependencies_text or "—"
            rec.header_html = Markup(
                f"""
                <div class="justech-cc-sheet-header">
                    <div class="justech-cc-sheet-meta">
                        <span class="justech-cc-pill {cc.status_class(rec.status)}">{st}</span>
                        <span class="justech-cc-pill">Licencia: {rec.license_tier_label or '—'}</span>
                        <span class="justech-cc-pill">Versión: {rec.version or '—'}</span>
                    </div>
                    <p class="justech-cc-sheet-desc">{rec.description or ''}</p>
                    <p class="justech-cc-sheet-deps"><strong>Dependencias:</strong> {deps}</p>
                    <p class="justech-cc-sheet-deps"><strong>Empresa:</strong> {rec.company_name or '—'}</p>
                </div>
                """
            )

    def _load_from_catalog(self):
        catalog = self.env["justech.license.service"].get_commercial_catalog(
            company=self.company_id
        )
        row = next((r for r in catalog if r["product_code"] == self.product_code), None)
        if not row:
            raise UserError(_("Módulo comercial no encontrado."))
        status_labels = {
            "active": _("Activo"),
            "partial": _("Parcial"),
            "inactive": _("Inactivo"),
            "unavailable": _("Próximamente"),
        }
        self.write(
            {
                "name": row["name"],
                "description": row["description"],
                "status": row["status"],
                "status_label": status_labels.get(row["status"], row["status"]),
                "license_tier_label": row["license_tier_label"],
                "version": row["version"],
                "category_label": row["category_label"],
                "dependencies_text": ", ".join(row["dependencies"]) or "—",
                "company_name": row["company_name"],
            }
        )
        commands = [(5, 0, 0)]
        seq = 10
        for feat in row["features"]:
            commands.append(
                (
                    0,
                    0,
                    {
                        "commercial_name": feat["commercial_name"],
                        "description": feat["description"],
                        "feature_code": feat["feature_code"],
                        "is_active": feat["is_active"],
                        "always_on": feat["always_on"],
                        "configured": feat["configured"],
                        "sequence": seq,
                    },
                )
            )
            seq += 10
        self.feature_ids = commands

    def action_refresh(self):
        self.ensure_one()
        self._load_from_catalog()
        return True

    def action_back_to_catalog(self):
        return self.env["justech.control.module.catalog"].action_open()


class JustechControlModuleFeature(models.TransientModel):
    _name = "justech.control.module.feature"
    _description = "Commercial Module Feature Switch"
    _order = "sequence, commercial_name"

    sheet_id = fields.Many2one("justech.control.module.sheet", ondelete="cascade")
    sequence = fields.Integer(default=10)
    commercial_name = fields.Char(readonly=True)
    description = fields.Char(readonly=True)
    feature_code = fields.Char(readonly=True)
    is_active = fields.Boolean(readonly=True)
    always_on = fields.Boolean(readonly=True)
    configured = fields.Boolean(readonly=True)
    switch_label = fields.Char(compute="_compute_switch_label")

    @api.depends("is_active", "configured", "always_on")
    def _compute_switch_label(self):
        for rec in self:
            if rec.always_on:
                rec.switch_label = _("Siempre activo")
            elif not rec.configured:
                rec.switch_label = _("Próximamente")
            elif rec.is_active:
                rec.switch_label = "ON"
            else:
                rec.switch_label = "OFF"

    def action_toggle(self):
        self.ensure_one()
        if self.always_on:
            raise UserError(_("Esta función es obligatoria del sistema."))
        if not self.configured:
            raise UserError(_("Esta función aún no está disponible."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Clave Administrativa Justech"),
            "res_model": "justech.control.toggle.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sheet_id": self.sheet_id.id,
                "default_feature_code": self.feature_code,
                "default_commercial_name": self.commercial_name,
                "default_target_active": not self.is_active,
            },
        }


class JustechControlToggleWizard(models.TransientModel):
    _name = "justech.control.toggle.wizard"
    _description = "Confirm feature toggle with admin key"

    sheet_id = fields.Many2one("justech.control.module.sheet", required=True)
    feature_code = fields.Char(required=True)
    commercial_name = fields.Char(readonly=True)
    target_active = fields.Boolean(readonly=True)
    admin_key = fields.Char(string="Clave Administrativa Justech", required=True)

    def action_confirm(self):
        self.ensure_one()
        svc = self.env["justech.admin.access.service"]
        svc.verify_key_only(self.admin_key, action=svc.CRITICAL_PLATFORM_MUTATION)
        token = svc.issue_critical_grant(svc.CRITICAL_PLATFORM_MUTATION)
        license_svc = self.env["justech.license.service"].with_context(
            justech_critical_token=token
        )
        if self.target_active:
            license_svc.activate_feature(
                self.feature_code, company=self.sheet_id.company_id
            )
        else:
            license_svc.deactivate_feature(
                self.feature_code, company=self.sheet_id.company_id
            )
        sheet = self.sheet_id
        sheet._load_from_catalog()
        return {
            "type": "ir.actions.act_window",
            "name": sheet.name,
            "res_model": "justech.control.module.sheet",
            "res_id": sheet.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}


class JustechControlLicenses(models.TransientModel):
    _name = "justech.control.licenses"
    _description = "Commercial License Administration Center"

    card_ids = fields.One2many("justech.control.license.card", "hub_id")
    hero_html = fields.Html(compute="_compute_hero_html", sanitize=False)
    empty_html = fields.Html(compute="_compute_empty_html", sanitize=False)
    has_cards = fields.Boolean(compute="_compute_has_cards")

    @api.depends("card_ids")
    def _compute_has_cards(self):
        for rec in self:
            rec.has_cards = bool(rec.card_ids)

    @api.depends()
    def _compute_hero_html(self):
        body = """
        <div class="justech-cc-hero justech-cc-license-hero">
            <h1>Centro de Licencias</h1>
            <p>Administre contratos, empresas y personalizaciones de cada cliente.</p>
        </div>
        """
        for rec in self:
            rec.hero_html = Markup(body)

    @api.depends("card_ids")
    def _compute_empty_html(self):
        for rec in self:
            if rec.card_ids:
                rec.empty_html = False
            else:
                rec.empty_html = Markup(
                    cc.alert(
                        "info",
                        _(
                            "No hay licencias registradas. "
                            "Use <strong>Crear licencia</strong> para comenzar."
                        ),
                    )
                )

    def _open_license_wizard(self, mode, license_ref=False):
        self.ensure_one()
        ctx = {
            "default_mode": mode,
            "default_control_id": self.id,
            "default_company_id": self.env.company.id,
        }
        if license_ref:
            ctx["default_license_id"] = license_ref
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

    def action_create_license(self):
        return self._open_license_wizard("create")

    def action_reopen(self):
        self.ensure_one()
        self._load_cards()
        return {
            "type": "ir.actions.act_window",
            "name": _("Centro de Licencias"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def action_open(self):
        self.env["justech.admin.access.service"].require_justech_settings_access()
        rec = self.create({})
        rec._load_cards()
        return {
            "type": "ir.actions.act_window",
            "name": _("Centro de Licencias"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    def _load_cards(self):
        license_svc = self.env["justech.license.service"]
        internal = license_svc._sudo_internal()
        License = internal["justech.license"]
        licenses = License.search([], order="write_date desc, id desc")
        commands = [(5, 0, 0)]
        for lic in licenses:
            primary = lic.company_line_ids[:1].company_id
            used = len(lic.company_line_ids)
            max_c = lic.max_companies or 0
            available = (
                str(max(max_c - used, 0))
                if max_c
                else _("Ilimitadas")
            )
            _code, status_label, status_class, status_icon = _commercial_license_status(
                lic
            )
            active_modules = 0
            if primary:
                rows = license_svc.get_client_module_rows(
                    company=primary, license_id=lic.id, view_only=True
                )
                active_modules = len(
                    [
                        row
                        for row in rows
                        if row.get("is_active") and not row.get("internal_only")
                    ]
                )
            commands.append(
                (
                    0,
                    0,
                    {
                        "license_ref": lic.id,
                        "client_name": lic.name,
                        "primary_company": primary.name if primary else "—",
                        "plan_label": license_svc._tier_commercial_label(lic.tier),
                        "status_code": _code,
                        "status_label": status_label,
                        "status_icon": status_icon,
                        "status_class": status_class,
                        "starts_at_display": str(lic.starts_at or "—"),
                        "expires_at_display": str(lic.expires_at or "—"),
                        "companies_used": used,
                        "companies_available": available,
                        "modules_active": active_modules,
                        "last_modified_display": fields.Datetime.to_string(
                            lic.write_date
                        )
                        if lic.write_date
                        else "—",
                    },
                )
            )
        self.card_ids = commands


class JustechControlSecurity(models.TransientModel):
    _name = "justech.control.security"
    _description = "Security Control Center"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    content_html = fields.Html(compute="_compute_content_html", sanitize=False)

    @api.model
    def action_open(self):
        JustechControlModuleCatalog._require_admin_session(self)
        rec = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": _("Seguridad"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends("company_id")
    def _compute_content_html(self):
        Access = self.env["justech.admin.access"].sudo()
        Session = self.env["justech.admin.session"].sudo()
        Audit = self.env["justech.admin.access.audit"].sudo()
        internal_group = self.env.ref("justech_modules.group_justech_internal_admin")
        for rec in self:
            access_rows = Access.search([("company_id", "=", rec.company_id.id)])
            internal_users = self.env["res.users"].search(
                [("group_ids", "in", internal_group.id)]
            )
            active_sessions = Session.search_count([("active", "=", True)])
            failed = sum(access_rows.mapped("failed_attempts"))
            locked = access_rows.filtered(lambda a: a.locked_until)
            cards = cc.grid(
                cc.card(_("Usuarios internos"), str(len(internal_users)), "", "ok", "fa-user-secret"),
                cc.card(_("Claves configuradas"), str(len(access_rows.filtered(lambda a: a.has_key))), "", "ok", "fa-key"),
                cc.card(_("Sesiones activas"), str(active_sessions), "", "warn" if active_sessions else "ok", "fa-sign-in"),
                cc.card(_("Intentos fallidos"), str(failed), "", "fail" if failed > 5 else "ok", "fa-exclamation"),
                cc.card(_("Usuarios bloqueados"), str(len(locked)), "", "fail" if locked else "ok", "fa-lock"),
                cc.card(_("Eventos auditoría"), str(Audit.search_count([])), "", "ok", "fa-shield"),
            )
            rec.content_html = Markup(cc.section(_("Seguridad"), cards))

    def action_rotate_key(self):
        access = self.env["justech.admin.access.service"].get_user_access(
            company=self.company_id
        )
        if not access:
            raise UserError(_("No hay registro de acceso administrativo."))
        return access.action_open_rotate_wizard()

    def action_revoke_sessions(self):
        self.env["justech.admin.access.service"].revoke_all_sessions()
        return self.action_open()

    def action_open_policies(self):
        return self.env["justech.admin.access.service"].action_open_governance_feature_policies()


class JustechControlAudit(models.TransientModel):
    _name = "justech.control.audit"
    _description = "Audit Timeline"

    content_html = fields.Html(compute="_compute_content_html", sanitize=False)

    @api.model
    def action_open(self):
        JustechControlModuleCatalog._require_admin_session(self)
        rec = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends()
    def _compute_content_html(self):
        license_svc = self.env["justech.license.service"]
        events = []
        for row in license_svc._sudo_internal()["justech.license.audit"].search([], limit=30):
            name = license_svc.commercial_name_for_feature(row.feature_id.code) if row.feature_id else _("Sistema")
            action_map = {
                "activate": _("Activó"),
                "deactivate": _("Desactivó"),
                "validate": _("Validó"),
                "register": _("Registró"),
                "revoke": _("Revocó"),
            }
            events.append(
                {
                    "dt": row.create_date,
                    "user": row.user_id.name or _("Sistema"),
                    "action": action_map.get(row.action, row.action),
                    "target": name,
                }
            )
        for row in self.env["justech.admin.access.audit"].sudo().search([], limit=20):
            events.append(
                {
                    "dt": row.create_date,
                    "user": row.user_id.name or _("Sistema"),
                    "action": row.action,
                    "target": row.scope or "",
                }
            )
        for row in self.env["hellenia.governance.audit"].sudo().search([], limit=20):
            events.append(
                {
                    "dt": row.create_date,
                    "user": row.user_id.name or _("Sistema"),
                    "action": row.action or _("Evento"),
                    "target": row.model or "",
                }
            )
        events.sort(key=lambda e: e["dt"] or datetime.min, reverse=True)
        items = []
        for ev in events[:40]:
            ts = fields.Datetime.to_string(ev["dt"]) if ev["dt"] else "—"
            items.append(
                f"""
                <div class="justech-cc-timeline-item">
                    <div class="justech-cc-timeline-time">{ts}</div>
                    <div class="justech-cc-timeline-body">
                        <strong>{ev['user']}</strong> {ev['action']} <em>{ev['target']}</em>
                    </div>
                </div>
                """
            )
        body = "".join(items) or "<p>Sin eventos recientes.</p>"
        for rec in self:
            rec.content_html = Markup(f'<div class="justech-cc-timeline">{body}</div>')


class JustechControlIntegrations(models.TransientModel):
    _name = "justech.control.integrations"
    _description = "Integrations Hub"

    content_html = fields.Html(compute="_compute_content_html", sanitize=False)

    @api.model
    def action_open(self):
        JustechControlModuleCatalog._require_admin_session(self)
        rec = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": _("Integraciones"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends()
    def _compute_content_html(self):
        icp = self.env["ir.config_parameter"].sudo()
        mail_server = self.env["ir.mail_server"].sudo().search([], limit=1)
        integrations = [
            ("Microsoft 365", "fa-windows", "inactive", "—"),
            ("Huawei", "fa-cloud", "inactive", "—"),
            ("DGII", "fa-institution", "active" if self.env["justech.license.service"].is_active("l10n_do_reports") else "inactive", "—"),
            ("WhatsApp", "fa-whatsapp", "inactive", "—"),
            ("SMTP", "fa-envelope", "active" if mail_server else "inactive", mail_server.name if mail_server else "—"),
            ("API Justech", "fa-plug", "active", "v1"),
            ("Marketplace", "fa-shopping-bag", "inactive", "—"),
        ]
        cards = []
        for name, icon, status, detail in integrations:
            cards.append(cc.card(name, detail or status.title(), _("Última sync: —"), status, icon))
        for rec in self:
            rec.content_html = Markup(cc.section(_("Integraciones"), cc.grid(*cards)))


class JustechControlSystem(models.TransientModel):
    _name = "justech.control.system"
    _description = "System Information"

    content_html = fields.Html(compute="_compute_content_html", sanitize=False)

    @api.model
    def action_open(self):
        JustechControlModuleCatalog._require_admin_session(self)
        rec = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": _("Sistema"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends()
    def _compute_content_html(self):
        license_svc = self.env["justech.license.service"]
        db = self.env.cr.dbname
        cron_count = self.env["ir.cron"].sudo().search_count([("active", "=", True)])
        mail_server = self.env["ir.mail_server"].sudo().search([], limit=1)
        cards = cc.grid(
            cc.card(_("Versión ERP"), "Justech 2026.1", "Odoo 19", "ok", "fa-code-fork"),
            cc.card(_("API"), f"v{license_svc.get_api_version()}", "", "ok", "fa-plug"),
            cc.card(_("Build"), "F31.5", "", "ok", "fa-cog"),
            cc.card(_("Healthcheck"), _("OK"), "", "ok", "fa-heartbeat"),
            cc.card(_("Base de datos"), db, "", "ok", "fa-database"),
            cc.card(_("Cron activos"), str(cron_count), "", "ok", "fa-clock-o"),
            cc.card(_("SMTP"), mail_server.name if mail_server else _("No configurado"), "", "active" if mail_server else "inactive", "fa-envelope"),
            cc.card(_("Servidor"), _("Operacional"), "", "ok", "fa-server"),
        )
        for rec in self:
            rec.content_html = Markup(cc.section(_("Sistema"), cards))


class JustechControlInternalUsers(models.TransientModel):
    _name = "justech.control.internal.users"
    _description = "Internal Users Overview"

    content_html = fields.Html(compute="_compute_content_html", sanitize=False)

    @api.model
    def action_open(self):
        JustechControlModuleCatalog._require_admin_session(self)
        rec = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": _("Usuarios Internos"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends()
    def _compute_content_html(self):
        internal_group = self.env.ref("justech_modules.group_justech_internal_admin")
        admin_group = self.env.ref("justech_admin.group_justech_admin_user")
        gov_group = self.env.ref("hellenia_governance.group_governance_manager")
        users = self.env["res.users"].search(
            ["|", "|", ("group_ids", "in", internal_group.id), ("group_ids", "in", admin_group.id), ("group_ids", "in", gov_group.id)]
        )
        cards = []
        for user in users:
            access = self.env["justech.admin.access"].sudo().search(
                [("user_id", "=", user.id)], limit=1
            )
            key_status = _("Configurada") if access and access.has_key else _("Pendiente")
            cards.append(
                cc.card(user.name, user.login, key_status, "active" if access and access.has_key else "warn", "fa-user")
            )
        for rec in self:
            rec.content_html = Markup(
                cc.section(_("Usuarios Internos Justech"), cc.grid(*cards) if cards else "<p>—</p>")
            )

    def action_open_profiles(self):
        return self.env["justech.admin.access.service"].action_open_governance_user_profiles()
