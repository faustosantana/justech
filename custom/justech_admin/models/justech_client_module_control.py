# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JustechClientModuleControl(models.TransientModel):
    _name = "justech.client.module.control"
    _description = "Módulos del Cliente"

    license_id = fields.Many2one(
        "justech.license",
        string="Cliente",
        domain=[("state", "=", "active")],
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa contexto",
    )
    client_name = fields.Char(compute="_compute_client_context", readonly=True)
    show_client_selector = fields.Boolean(compute="_compute_client_context", readonly=True)
    line_ids = fields.One2many("justech.client.module.line", "control_id")
    has_admin_key = fields.Boolean(compute="_compute_key_state")
    show_key_banner = fields.Boolean(compute="_compute_key_state")
    summary_plan = fields.Char(compute="_compute_client_context", readonly=True)
    summary_total = fields.Integer(compute="_compute_summary")
    summary_active = fields.Integer(compute="_compute_summary")
    header_html = fields.Html(compute="_compute_header_html", sanitize=False)
    key_banner_html = fields.Html(compute="_compute_key_banner_html", sanitize=False)
    search_text = fields.Char(string="Buscar")
    filter_mode = fields.Selection(
        [
            ("all", "Todos"),
            ("active", "Activos"),
            ("inactive", "Inactivos"),
            ("pending", "Pendientes"),
        ],
        default="all",
        string="Estado",
    )

    @api.model
    def action_open(self):
        self.env["justech.admin.access.service"].require_justech_settings_access()
        license_svc = self.env["justech.license.service"]
        clients = license_svc.get_commercial_clients()
        client = clients[0] if clients else {}
        rec = self.create(
            {
                "license_id": client.get("license_id") or False,
                "company_id": client.get("primary_company_id") or self.env.company.id,
            }
        )
        rec._reload_lines()
        return {
            "type": "ir.actions.act_window",
            "name": _("Módulos del Cliente"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends("license_id")
    def _compute_client_context(self):
        license_svc = self.env["justech.license.service"]
        clients = license_svc.get_commercial_clients()
        for rec in self:
            rec.show_client_selector = len(clients) > 1
            if not rec.license_id:
                rec.client_name = rec.env.company.name
                rec.company_id = rec.env.company
                rec.summary_plan = "—"
                continue
            dashboard = license_svc.get_client_dashboard(license_id=rec.license_id.id)
            rec.client_name = dashboard.get("client_name") or rec.license_id.name
            rec.summary_plan = dashboard.get("plan_label") or "—"
            primary_id = dashboard.get("primary_company_id")
            rec.company_id = (
                self.env["res.company"].browse(primary_id)
                if primary_id
                else rec.env.company
            )

    @api.depends()
    def _compute_key_state(self):
        svc = self.env["justech.admin.access.service"]
        for rec in self:
            rec.has_admin_key = svc.user_has_key()
            rec.show_key_banner = not rec.has_admin_key

    @api.depends("line_ids.is_paid", "line_ids.is_active", "line_ids.status")
    def _compute_summary(self):
        for rec in self:
            lines = rec.line_ids
            rec.summary_total = len(lines)
            rec.summary_active = len(lines.filtered("is_active"))

    @api.depends("client_name", "summary_plan", "summary_total", "summary_active")
    def _compute_header_html(self):
        for rec in self:
            rec.header_html = Markup(
                f"""
                <div class="justech-cc-compact-header">
                    <h1>Módulos del Cliente</h1>
                    <p class="justech-cc-client-line">
                        <strong>Cliente:</strong> {rec.client_name or '—'}
                        · <strong>Plan:</strong> {rec.summary_plan or '—'}
                        · <strong>{rec.summary_total}</strong> personalizaciones
                        · <strong>{rec.summary_active}</strong> activas
                    </p>
                </div>
                """
            )

    @api.depends("show_key_banner")
    def _compute_key_banner_html(self):
        for rec in self:
            if not rec.show_key_banner:
                rec.key_banner_html = False
                continue
            rec.key_banner_html = Markup(
                """
                <div class="alert alert-warning mb-2 py-2" role="alert">
                    <strong>No existe una Clave Administrativa Justech.</strong>
                </div>
                """
            )

    @api.onchange("license_id", "search_text", "filter_mode")
    def _onchange_reload(self):
        if self.license_id:
            self._reload_lines()

    def _reload_lines(self):
        license_svc = self.env["justech.license.service"]
        company = self.company_id
        license_id = self.license_id.id if self.license_id else False
        if self.license_id and not company:
            dashboard = license_svc.get_client_dashboard(license_id=self.license_id.id)
            primary_id = dashboard.get("primary_company_id")
            if primary_id:
                company = self.env["res.company"].browse(primary_id)
        company = company or self.env.company
        rows = license_svc.get_client_module_rows(
            company=company,
            license_id=license_id,
            view_only=True,
        )
        search = (self.search_text or "").strip().lower()
        filtered = []
        for row in rows:
            haystack = " ".join(
                [
                    row.get("name") or "",
                    row.get("includes_summary") or "",
                    " ".join(row.get("includes") or []),
                ]
            ).lower()
            if search and search not in haystack:
                continue
            mode = self.filter_mode or "all"
            if mode == "active" and not row.get("is_active"):
                continue
            if mode == "inactive" and row.get("is_active"):
                continue
            if mode == "pending" and row.get("is_paid"):
                continue
            filtered.append(row)
        filtered.sort(key=lambda r: r.get("name") or "")
        line_fields = set(self.env["justech.client.module.line"]._fields)
        commands = [(5, 0, 0)]
        for row in filtered:
            payload = {k: v for k, v in row.items() if k in line_fields}
            commands.append((0, 0, payload))
        self.line_ids = commands

    def action_refresh(self):
        self.ensure_one()
        self._reload_lines()
        return True

    def action_apply_filters(self):
        self.ensure_one()
        self._reload_lines()
        return True

    def action_create_admin_key(self):
        self.ensure_one()
        svc = self.env["justech.admin.access.service"]
        return svc._action_setup_key_required(
            "justech_admin.action_justech_client_module_control_open",
            svc.SCOPE_ADMIN,
        )

    def _return_self_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Módulos del Cliente"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }


class JustechClientModuleLine(models.TransientModel):
    _name = "justech.client.module.line"
    _description = "Client Module Line"
    _order = "name"

    control_id = fields.Many2one("justech.client.module.control", ondelete="cascade")
    main_module_code = fields.Char(string="Categoría", readonly=True)
    product_code = fields.Char(required=True)
    section = fields.Selection(
        [("available", "Disponible"), ("development", "En desarrollo")],
        readonly=True,
    )
    is_development = fields.Boolean(readonly=True)
    name = fields.Char(string="Categoría", readonly=True)
    display_name = fields.Char(string="Categoría", readonly=True)
    description = fields.Text(readonly=True)
    includes = fields.Json(readonly=True)
    includes_summary = fields.Char(string="Incluye", readonly=True)
    technical_status_text = fields.Char(readonly=True)
    allow_license_actions = fields.Boolean(readonly=True)
    is_paid = fields.Boolean(readonly=True)
    is_active = fields.Boolean(readonly=True)
    is_blocked = fields.Boolean(readonly=True)
    paid_label = fields.Char(string="Pagado", compute="_compute_labels", readonly=True)
    active_label = fields.Char(string="Activo", compute="_compute_labels", readonly=True)
    companies_enabled_text = fields.Char(string="Empresas habilitadas", readonly=True)
    license_label = fields.Char(string="Licencia", readonly=True)
    last_modified_at = fields.Datetime(readonly=True)
    last_modified_display = fields.Char(string="Última modificación", readonly=True)
    last_modified_by_name = fields.Char(readonly=True)
    status = fields.Char(readonly=True)
    status_label = fields.Char(readonly=True)
    configured = fields.Boolean(readonly=True)

    @api.depends("is_paid", "is_active")
    def _compute_labels(self):
        for line in self:
            line.paid_label = _("Sí") if line.is_paid else _("No")
            line.active_label = _("Sí") if line.is_active else _("No")

    def _open_action_wizard(self, action_type, **ctx):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Clave Administrativa Justech"),
            "res_model": "justech.client.module.action.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_control_id": self.control_id.id,
                "default_line_id": self.id,
                "default_product_code": self.product_code,
                "default_action_type": action_type,
                "default_company_id": self.control_id.company_id.id,
                "default_license_id": self.control_id.license_id.id,
                **ctx,
            },
        }

    def action_open_administrar(self):
        self.ensure_one()
        return self.env["justech.client.module.admin.panel"].action_open_for_line(self)

    def get_formview_action(self, access_uid=None):
        """Never open the technical line form — redirect to commercial admin panel."""
        self.ensure_one()
        return self.action_open_administrar()


class JustechClientModuleAdminPanel(models.TransientModel):
    _name = "justech.client.module.admin.panel"
    _description = "Commercial administration panel for a personalization"

    control_id = fields.Many2one("justech.client.module.control", ondelete="cascade")
    line_id = fields.Many2one("justech.client.module.line", ondelete="cascade")
    customization_code = fields.Char(readonly=True)
    product_code = fields.Char(readonly=True)
    module_name = fields.Char(string="Personalización", readonly=True)
    description = fields.Text(readonly=True)
    status_label = fields.Char(string="Estado", readonly=True)
    paid_label = fields.Char(string="Pagado", readonly=True)
    active_label = fields.Char(string="Activo", readonly=True)
    license_label = fields.Char(string="Licencia", readonly=True)
    companies_enabled_text = fields.Char(string="Empresas habilitadas", readonly=True)
    is_paid = fields.Boolean(readonly=True)
    is_active = fields.Boolean(readonly=True)
    is_blocked = fields.Boolean(readonly=True)
    allow_license_actions = fields.Boolean(readonly=True)
    license_id = fields.Many2one("justech.license", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    feature_line_ids = fields.One2many(
        "justech.client.module.admin.feature.line", "panel_id", string="Funciones"
    )
    company_line_ids = fields.One2many(
        "justech.client.module.admin.company.line", "panel_id", string="Empresas"
    )
    last_modified_display = fields.Char(string="Última modificación", readonly=True)
    last_modified_by_name = fields.Char(string="Modificado por", readonly=True)
    active_features_count = fields.Integer(compute="_compute_feature_stats")
    total_features_count = fields.Integer(compute="_compute_feature_stats")
    features_summary = fields.Char(compute="_compute_feature_stats")
    dashboard_header_html = fields.Html(
        compute="_compute_dashboard_html", sanitize=False
    )
    companies_dashboard_html = fields.Html(
        compute="_compute_dashboard_html", sanitize=False
    )
    audit_html = fields.Html(compute="_compute_audit_html", sanitize=False)
    has_pending_changes = fields.Boolean(compute="_compute_pending_changes")

    @api.model
    def action_open_for_line(self, line):
        line.ensure_one()
        panel = self.create(
            {
                "control_id": line.control_id.id,
                "line_id": line.id,
                "customization_code": line.main_module_code,
                "product_code": line.product_code,
                "module_name": line.display_name or line.name,
                "description": line.description,
                "status_label": line.status_label,
                "paid_label": line.paid_label,
                "active_label": line.active_label,
                "license_label": line.license_label,
                "companies_enabled_text": line.companies_enabled_text,
                "is_paid": line.is_paid,
                "is_active": line.is_active,
                "is_blocked": line.is_blocked,
                "allow_license_actions": line.allow_license_actions,
                "license_id": line.control_id.license_id.id,
                "company_id": line.control_id.company_id.id,
                "last_modified_display": line.last_modified_display or "—",
                "last_modified_by_name": line.last_modified_by_name or "—",
            }
        )
        panel._load_feature_lines()
        panel._load_company_lines()
        view = self.env.ref(
            "justech_admin.view_justech_client_module_admin_panel_form",
            raise_if_not_found=False,
        )
        action = {
            "type": "ir.actions.act_window",
            "name": _("Administrar personalización"),
            "res_model": self._name,
            "res_id": panel.id,
            "view_mode": "form",
            "target": "new",
        }
        if view:
            action["views"] = [(view.id, "form")]
            action["view_id"] = view.id
        return action

    def _load_feature_lines(self):
        license_svc = self.env["justech.license.service"]
        commands = [(5, 0, 0)]
        for row in license_svc.get_commercial_feature_rows(
            self.customization_code, company=self.company_id
        ):
            commands.append(
                (
                    0,
                    0,
                    {
                        "feature_key": row["feature_key"],
                        "label": row["label"],
                        "description": row.get("description") or "",
                        "section": row.get("section") or "general",
                        "section_label": row.get("section_label") or "GENERAL",
                        "section_sequence": row.get("section_sequence", 99),
                        "sequence": row.get("sequence", 99),
                        "is_active": row["is_active"],
                        "initial_active": row["initial_active"],
                        "control_type": row["control_type"],
                    },
                )
            )
        self.feature_line_ids = commands

    def _load_company_lines(self):
        license_svc = self.env["justech.license.service"]
        internal = license_svc._sudo_internal()
        product = internal["justech.commercial.product"].search(
            [("code", "=", self.product_code)], limit=1
        )
        lic = self.license_id
        commands = [(5, 0, 0)]
        if lic and product:
            for row in license_svc._product_companies_checklist(product, lic):
                commands.append(
                    (
                        0,
                        0,
                        {
                            "company_id": row["company_id"],
                            "company_name": row["company_name"],
                            "enabled": row["enabled"],
                        },
                    )
                )
        elif self.companies_enabled_text and self.companies_enabled_text != "—":
            for name in [
                part.strip()
                for part in self.companies_enabled_text.split(",")
                if part.strip()
            ]:
                company = self.env["res.company"].search(
                    [("name", "=", name)], limit=1
                )
                commands.append(
                    (
                        0,
                        0,
                        {
                            "company_id": company.id if company else False,
                            "company_name": name,
                            "enabled": True,
                        },
                    )
                )
        self.company_line_ids = commands

    @api.depends("feature_line_ids.is_active")
    def _compute_feature_stats(self):
        for panel in self:
            lines = panel.feature_line_ids
            total = len(lines)
            active = len(lines.filtered("is_active"))
            panel.total_features_count = total
            panel.active_features_count = active
            panel.features_summary = f"{active}/{total} activas" if total else "—"

    @api.depends(
        "status_label",
        "paid_label",
        "active_label",
        "license_label",
        "companies_enabled_text",
        "features_summary",
        "last_modified_display",
        "last_modified_by_name",
        "is_active",
        "is_paid",
        "is_blocked",
        "company_line_ids",
    )
    def _compute_dashboard_html(self):
        for panel in self:
            if panel.is_blocked:
                status_class = "blocked"
                status_icon = "🔴"
            elif panel.is_active:
                status_class = "active"
                status_icon = "🟢"
            else:
                status_class = "inactive"
                status_icon = "🟡"
            paid_icon = "🟢" if panel.is_paid else "🔴"
            enabled = panel.company_line_ids.filtered("enabled")
            company_count = len(enabled) if panel.company_line_ids else (
                1 if panel.companies_enabled_text and panel.companies_enabled_text != "—" else 0
            )
            panel.dashboard_header_html = Markup(
                f"""
                <div class="justech-dash-header">
                    <div class="justech-dash-kpi justech-dash-kpi-{status_class}">
                        <span class="justech-dash-kpi-label">Estado</span>
                        <span class="justech-dash-kpi-value">{status_icon} {panel.status_label or '—'}</span>
                    </div>
                    <div class="justech-dash-kpi">
                        <span class="justech-dash-kpi-label">Pagado</span>
                        <span class="justech-dash-kpi-value">{paid_icon} {panel.paid_label or '—'}</span>
                    </div>
                    <div class="justech-dash-kpi">
                        <span class="justech-dash-kpi-label">Licencia</span>
                        <span class="justech-dash-kpi-value">{panel.license_label or 'Pendiente'}</span>
                    </div>
                    <div class="justech-dash-kpi">
                        <span class="justech-dash-kpi-label">Empresas</span>
                        <span class="justech-dash-kpi-value">{company_count}</span>
                    </div>
                    <div class="justech-dash-kpi">
                        <span class="justech-dash-kpi-label">Funciones</span>
                        <span class="justech-dash-kpi-value">{panel.features_summary or '—'}</span>
                    </div>
                    <div class="justech-dash-kpi">
                        <span class="justech-dash-kpi-label">Última modificación</span>
                        <span class="justech-dash-kpi-value">{panel.last_modified_display or '—'}</span>
                    </div>
                    <div class="justech-dash-kpi">
                        <span class="justech-dash-kpi-label">Modificado por</span>
                        <span class="justech-dash-kpi-value">{panel.last_modified_by_name or '—'}</span>
                    </div>
                </div>
                """
            )
            if panel.company_line_ids:
                items = "".join(
                    f'<div class="justech-dash-company-chip {"enabled" if row.enabled else "disabled"}">'
                    f'{"☑" if row.enabled else "☐"} {row.company_name}</div>'
                    for row in panel.company_line_ids
                )
            elif panel.companies_enabled_text and panel.companies_enabled_text != "—":
                items = "".join(
                    f'<div class="justech-dash-company-chip enabled">☑ {name.strip()}</div>'
                    for name in panel.companies_enabled_text.split(",")
                    if name.strip()
                )
            else:
                items = (
                    '<p class="justech-dash-empty">'
                    "No hay empresas habilitadas para esta personalización."
                    "</p>"
                )
            panel.companies_dashboard_html = Markup(
                f'<div class="justech-dash-companies">{items}</div>'
            )

    @api.depends("feature_line_ids.is_active", "feature_line_ids.initial_active")
    def _compute_pending_changes(self):
        for panel in self:
            panel.has_pending_changes = any(
                line.is_active != line.initial_active for line in panel.feature_line_ids
            )

    def _audit_timeline_message(self, audit):
        user = audit.user_id.name if audit.user_id else _("Sistema")
        details = audit.details or {}
        feature = details.get("feature_label")
        action = audit.action or ""
        if action == "feature_toggle" and feature:
            verb = _("activó") if audit.state_after == "ON" else _("desactivó")
            return f"{user} {verb} {feature}"
        action_labels = {
            "mark_paid": _("marcó como pagado"),
            "mark_unpaid": _("marcó como no pagado"),
            "activate": _("activó la personalización"),
            "deactivate": _("desactivó la personalización"),
            "add_company": _("agregó empresa"),
            "remove_company": _("quitó empresa"),
            "block": _("bloqueó"),
            "unblock": _("desbloqueó"),
        }
        verb = action_labels.get(action, action)
        return f"{user} {verb}"

    @api.depends("product_code", "customization_code", "control_id.client_name")
    def _compute_audit_html(self):
        license_svc = self.env["justech.license.service"]
        Audit = self.env["justech.client.module.audit"].sudo()
        for panel in self:
            domain = [("product_code", "=", panel.product_code)]
            if panel.control_id.client_name:
                domain.append(("client_name", "=", panel.control_id.client_name))
            audits = Audit.search(domain, order="create_date desc", limit=8)
            if not audits:
                panel.audit_html = Markup(
                    '<p class="justech-dash-empty">No hay movimientos recientes.</p>'
                )
                continue
            items = []
            for audit in audits:
                when = license_svc._format_client_datetime(audit.create_date)
                msg = panel._audit_timeline_message(audit)
                items.append(
                    f'<li class="justech-dash-timeline-item">'
                    f'<span class="justech-dash-timeline-dot"></span>'
                    f'<div class="justech-dash-timeline-body">'
                    f'<strong>{msg}</strong>'
                    f'<span class="justech-dash-timeline-when">{when}</span>'
                    f"</div></li>"
                )
            panel.audit_html = Markup(
                f'<ul class="justech-dash-timeline">{"".join(items)}</ul>'
            )

    def _open_key_wizard(self, action_type, **ctx):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Clave Administrativa Justech"),
            "res_model": "justech.client.module.action.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_panel_id": self.id,
                "default_control_id": self.control_id.id,
                "default_line_id": self.line_id.id,
                "default_product_code": self.product_code,
                "default_customization_code": self.customization_code,
                "default_action_type": action_type,
                "default_company_id": self.company_id.id,
                "default_license_id": self.license_id.id,
                **ctx,
            },
        }

    def action_save_changes(self):
        self.ensure_one()
        changes = []
        for line in self.feature_line_ids:
            if line.is_active == line.initial_active:
                continue
            changes.append(
                {
                    "key": line.feature_key,
                    "active": line.is_active,
                    "label": line.label,
                }
            )
        if not changes:
            raise UserError(_("No hay cambios pendientes en las funciones."))
        return self._open_key_wizard("save_features", default_feature_changes=changes)

    def action_activate(self):
        if not self.is_paid:
            raise UserError(
                _("Esta personalización no está incluida en la licencia contratada.")
            )
        return self._open_key_wizard("activate")

    def action_deactivate(self):
        return self._open_key_wizard("deactivate")

    def action_mark_paid(self):
        return self._open_key_wizard("mark_paid")

    def action_mark_unpaid(self):
        return self._open_key_wizard("mark_unpaid")

    def action_add_company(self):
        return self._open_key_wizard("add_company")

    def action_remove_company(self):
        return self._open_key_wizard("remove_company")

    def action_view_audit(self):
        self.ensure_one()
        domain = [("product_code", "=", self.product_code)]
        if self.control_id.client_name:
            domain.append(("client_name", "=", self.control_id.client_name))
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría"),
            "res_model": "justech.client.module.audit",
            "view_mode": "list",
            "domain": domain,
            "target": "new",
        }

    def action_refresh_panel(self):
        self.ensure_one()
        self.line_id.control_id._reload_lines()
        refreshed = self.line_id.control_id.line_ids.filtered(
            lambda line: line.main_module_code == self.customization_code
        )[:1]
        if refreshed:
            self.write(
                {
                    "line_id": refreshed.id,
                    "status_label": refreshed.status_label,
                    "paid_label": refreshed.paid_label,
                    "active_label": refreshed.active_label,
                    "license_label": refreshed.license_label,
                    "companies_enabled_text": refreshed.companies_enabled_text,
                    "is_paid": refreshed.is_paid,
                    "is_active": refreshed.is_active,
                    "is_blocked": refreshed.is_blocked,
                    "last_modified_display": refreshed.last_modified_display or "—",
                    "last_modified_by_name": refreshed.last_modified_by_name or "—",
                }
            )
        self._load_feature_lines()
        self._load_company_lines()
        return {
            "type": "ir.actions.act_window",
            "name": _("Administrar personalización"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "view_id": self.env.ref(
                "justech_admin.view_justech_client_module_admin_panel_form"
            ).id,
        }


class JustechClientModuleAdminFeatureLine(models.TransientModel):
    _name = "justech.client.module.admin.feature.line"
    _description = "Commercial feature toggle line"
    _order = "section_sequence, sequence, label"

    panel_id = fields.Many2one(
        "justech.client.module.admin.panel", required=True, ondelete="cascade"
    )
    feature_key = fields.Char(required=True)
    label = fields.Char(string="Función", readonly=True)
    description = fields.Text(string="Descripción", readonly=True)
    section = fields.Char(readonly=True)
    section_label = fields.Char(string="Sección", readonly=True)
    section_sequence = fields.Integer(default=99, readonly=True)
    sequence = fields.Integer(default=99, readonly=True)
    is_active = fields.Boolean(string="Activa")
    initial_active = fields.Boolean(readonly=True)
    control_type = fields.Char(default="commercial", readonly=True)


class JustechClientModuleAdminCompanyLine(models.TransientModel):
    _name = "justech.client.module.admin.company.line"
    _description = "Enabled company line for admin panel"

    panel_id = fields.Many2one(
        "justech.client.module.admin.panel", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one("res.company", readonly=True)
    company_name = fields.Char(readonly=True)
    enabled = fields.Boolean(string="Habilitada", readonly=True)


class JustechClientModuleManageMenu(models.TransientModel):
    """Legacy model kept for DB compatibility; use admin.panel instead."""

    _name = "justech.client.module.manage.menu"
    _description = "Administration panel for a personalization (legacy)"

    line_id = fields.Many2one("justech.client.module.line", ondelete="cascade")


class JustechClientModuleActionWizard(models.TransientModel):
    _name = "justech.client.module.action.wizard"
    _description = "Client module action confirmation"

    control_id = fields.Many2one("justech.client.module.control")
    panel_id = fields.Many2one("justech.client.module.admin.panel")
    line_id = fields.Many2one("justech.client.module.line")
    license_id = fields.Many2one("justech.license", string="Cliente")
    product_code = fields.Char(required=True)
    customization_code = fields.Char()
    action_type = fields.Selection(
        [
            ("mark_paid", "Marcar como pagado"),
            ("mark_unpaid", "Marcar como no pagado"),
            ("activate", "Activar"),
            ("deactivate", "Desactivar"),
            ("block", "Bloquear"),
            ("unblock", "Desbloquear"),
            ("add_company", "Agregar empresa"),
            ("remove_company", "Quitar empresa"),
            ("change_license", "Cambiar licencia"),
            ("save_features", "Guardar cambios de funciones"),
        ],
        required=True,
    )
    company_id = fields.Many2one("res.company", string="Empresa")
    target_company_id = fields.Many2one("res.company", string="Empresa")
    feature_changes = fields.Json(default=list)
    action_summary_html = fields.Html(compute="_compute_action_summary", sanitize=False)
    new_tier = fields.Selection(
        [
            ("TRIAL", "Trial"),
            ("STD", "Standard"),
            ("PRO", "Professional"),
            ("ENT", "Enterprise"),
        ],
        string="Nuevo plan",
    )
    admin_key = fields.Char(string="Clave Administrativa Justech", required=True)
    license_info_html = fields.Html(compute="_compute_license_info", sanitize=False)

    @api.depends("action_type", "feature_changes")
    def _compute_action_summary(self):
        for wiz in self:
            if wiz.action_type != "save_features":
                wiz.action_summary_html = False
                continue
            changes = wiz.feature_changes or []
            if not changes:
                wiz.action_summary_html = Markup(
                    "<p class='text-muted'>Sin cambios de funciones.</p>"
                )
                continue
            items = "".join(
                f"<li>{change.get('label') or change.get('key')}: "
                f"{'ON' if change.get('active') else 'OFF'}</li>"
                for change in changes
            )
            wiz.action_summary_html = Markup(
                f"<ul class='justech-cc-checklist'>{items}</ul>"
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        changes = self.env.context.get("default_feature_changes")
        if changes and "feature_changes" in fields_list:
            res["feature_changes"] = changes
        return res

    @api.depends("license_id", "company_id", "action_type")
    def _compute_license_info(self):
        license_svc = self.env["justech.license.service"]
        for wiz in self:
            if wiz.action_type not in ("add_company", "remove_company", "change_license"):
                wiz.license_info_html = False
                continue
            lic = wiz.license_id or license_svc._get_active_license_for_company(wiz.company_id)
            if not lic:
                wiz.license_info_html = Markup(
                    "<p class='text-muted'>No hay licencia activa.</p>"
                )
                continue
            used = len(lic.company_line_ids)
            max_c = lic.max_companies or 0
            quota = f"{used} de {max_c}" if max_c else f"{used} (ilimitadas)"
            wiz.license_info_html = Markup(
                f"""
                <div class="justech-cc-license-box">
                    <p><strong>Cliente:</strong> {lic.name}</p>
                    <p><strong>Plan:</strong> {license_svc._tier_commercial_label(lic.tier)}</p>
                    <p><strong>Empresas utilizadas:</strong> {quota}</p>
                    <p><strong>Empresas disponibles:</strong> {max(max_c - used, 0) if max_c else 'Ilimitadas'}</p>
                </div>
                """
            )

    def action_confirm(self):
        self.ensure_one()
        svc = self.env["justech.admin.access.service"]
        if not svc.user_has_key():
            return svc._action_setup_key_required(
                "justech_admin.action_justech_client_module_control_open",
                svc.SCOPE_ADMIN,
            )
        svc.verify_key_only(self.admin_key, action=svc.CRITICAL_PLATFORM_MUTATION)

        token = svc.issue_critical_grant(svc.CRITICAL_PLATFORM_MUTATION)
        license_svc = self.env["justech.license.service"].with_context(
            justech_critical_token=token
        )
        reason = self.new_tier if self.action_type == "change_license" else None
        if self.action_type == "save_features":
            license_svc.apply_commercial_feature_changes(
                self.customization_code,
                self.company_id,
                self.feature_changes or [],
            )
        else:
            license_svc.execute_client_module_action(
                self.action_type,
                self.product_code,
                company=self.company_id,
                target_company=self.target_company_id,
                reason=reason,
            )
        control = self.control_id
        panel = self.panel_id
        if control:
            control._reload_lines()
        if panel:
            return panel.action_refresh_panel()
        if control:
            return control._return_self_action()
        return {"type": "ir.actions.act_window_close"}


class JustechClientModuleDetail(models.TransientModel):
    """Legacy model kept for compatibility; F31.6 uses Administrar panel."""

    _name = "justech.client.module.detail"
    _description = "Client Module Detail (legacy)"
