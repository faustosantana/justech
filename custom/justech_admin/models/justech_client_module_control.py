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
    line_ids = fields.One2many("justech.client.module.line", "control_id")
    has_admin_key = fields.Boolean(compute="_compute_key_state")
    show_key_banner = fields.Boolean(compute="_compute_key_state")
    summary_plan = fields.Char(compute="_compute_client_context", readonly=True)
    summary_total = fields.Integer(compute="_compute_summary")
    summary_active = fields.Integer(compute="_compute_summary")
    summary_pending = fields.Integer(compute="_compute_summary")
    summary_companies = fields.Integer(compute="_compute_client_context", readonly=True)
    summary_last_modified = fields.Datetime(compute="_compute_summary")
    summary_html = fields.Html(compute="_compute_summary_html", sanitize=False)
    key_banner_html = fields.Html(compute="_compute_key_banner_html", sanitize=False)
    search_text = fields.Char(string="Buscar")
    filter_mode = fields.Selection(
        [
            ("all", "Todos"),
            ("active", "Activos"),
            ("inactive", "Inactivos"),
            ("paid", "Pagados"),
            ("unpaid", "No pagados"),
            ("blocked", "Bloqueados"),
        ],
        default="all",
        string="Filtro",
    )
    sort_order = fields.Selection(
        [
            ("name", "Nombre"),
            ("status", "Estado"),
            ("modified", "Última modificación"),
        ],
        default="name",
        string="Ordenar por",
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
        for rec in self:
            if not rec.license_id:
                rec.client_name = rec.env.company.name
                rec.company_id = rec.env.company
                rec.summary_plan = "—"
                rec.summary_companies = 1
                continue
            dashboard = license_svc.get_client_dashboard(license_id=rec.license_id.id)
            rec.client_name = dashboard.get("client_name") or rec.license_id.name
            rec.summary_plan = dashboard.get("plan_label") or "—"
            rec.summary_companies = dashboard.get("company_count") or 0
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

    @api.depends("line_ids.is_paid", "line_ids.is_active", "line_ids.status", "line_ids.last_modified_at", "line_ids.section")
    def _compute_summary(self):
        for rec in self:
            lines = rec.line_ids.filtered(lambda l: l.section == "available")
            rec.summary_total = len(lines)
            rec.summary_active = len(lines.filtered("is_active"))
            rec.summary_pending = len(
                lines.filtered(lambda l: not l.is_paid and l.status != "coming_soon")
            )
            modified = [l.last_modified_at for l in lines if l.last_modified_at]
            rec.summary_last_modified = max(modified) if modified else False

    @api.depends(
        "client_name",
        "summary_plan",
        "summary_total",
        "summary_active",
        "summary_pending",
        "summary_companies",
        "summary_last_modified",
    )
    def _compute_summary_html(self):
        for rec in self:
            last_mod = rec.summary_last_modified or "—"
            rec.summary_html = Markup(
                f"""
                <div class="justech-cc-dashboard">
                    <div class="justech-cc-hero">
                        <h1>Módulos del Cliente</h1>
                        <p>Panel comercial para administrar personalizaciones, licencias y empresas habilitadas.</p>
                    </div>
                    <div class="justech-cc-section">
                        <div class="justech-cc-grid">
                            <div class="justech-cc-card justech-cc-blue">
                                <div class="justech-cc-card-title">Cliente</div>
                                <div class="justech-cc-card-value justech-cc-card-plan">{rec.client_name or '—'}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-blue">
                                <div class="justech-cc-card-title">Plan contratado</div>
                                <div class="justech-cc-card-value justech-cc-card-plan">{rec.summary_plan or '—'}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-gray">
                                <div class="justech-cc-card-title">Módulos principales</div>
                                <div class="justech-cc-card-value">{rec.summary_total}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-green">
                                <div class="justech-cc-card-title">Activas</div>
                                <div class="justech-cc-card-value">{rec.summary_active}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-yellow">
                                <div class="justech-cc-card-title">Pendientes</div>
                                <div class="justech-cc-card-value">{rec.summary_pending}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-gray">
                                <div class="justech-cc-card-title">Empresas habilitadas</div>
                                <div class="justech-cc-card-value">{rec.summary_companies}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-gray">
                                <div class="justech-cc-card-title">Última modificación</div>
                                <div class="justech-cc-card-value justech-cc-card-plan">{last_mod}</div>
                            </div>
                        </div>
                    </div>
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
                <div class="alert alert-warning mb-3" role="alert">
                    <strong>No existe una Clave Administrativa Justech.</strong>
                </div>
                """
            )

    @api.onchange("license_id", "search_text", "filter_mode", "sort_order")
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
            if search:
                haystack = f"{row.get('name') or ''} {row.get('description') or ''}".lower()
                if search not in haystack:
                    continue
            mode = self.filter_mode or "all"
            if mode == "active" and not row.get("is_active"):
                continue
            if mode == "inactive" and row.get("is_active"):
                continue
            if mode == "paid" and not row.get("is_paid"):
                continue
            if mode == "unpaid" and row.get("is_paid"):
                continue
            if mode == "blocked" and row.get("status") != "blocked":
                continue
            filtered.append(row)
        sort_key = self.sort_order or "name"
        if sort_key == "status":
            filtered.sort(key=lambda r: (r.get("status_label") or "", r.get("name") or ""))
        elif sort_key == "modified":
            filtered.sort(
                key=lambda r: r.get("last_modified_at") or "",
                reverse=True,
            )
        else:
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
    _order = "section, name"

    control_id = fields.Many2one("justech.client.module.control", ondelete="cascade")
    main_module_code = fields.Char(string="Módulo principal", readonly=True)
    product_code = fields.Char(required=True)
    section = fields.Selection(
        [("available", "Disponible"), ("development", "En desarrollo")],
        readonly=True,
    )
    is_development = fields.Boolean(readonly=True)
    name = fields.Char(string="Módulo", readonly=True)
    display_name = fields.Char(string="Módulo", readonly=True)
    description = fields.Text(readonly=True)
    includes = fields.Json(readonly=True)
    is_paid = fields.Boolean(readonly=True)
    is_active = fields.Boolean(readonly=True)
    is_blocked = fields.Boolean(readonly=True)
    paid_label = fields.Char(string="Pagado", compute="_compute_labels", readonly=True)
    active_label = fields.Char(string="Activo", compute="_compute_labels", readonly=True)
    companies_enabled_text = fields.Char(string="Empresas habilitadas", readonly=True)
    license_label = fields.Char(string="Licencia", readonly=True)
    last_modified_at = fields.Datetime(string="Última modificación", readonly=True)
    last_modified_by_name = fields.Char(string="Modificado por", readonly=True)
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
        return self._open_manage_panel(_("Administrar"))

    def action_view_information(self):
        self.ensure_one()
        return self._open_manage_panel(_("Ver información"))

    def _open_manage_panel(self, title):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": "justech.client.module.manage.menu",
            "view_mode": "form",
            "target": "new",
            "context": {"default_line_id": self.id},
        }


class JustechClientModuleManageMenu(models.TransientModel):
    _name = "justech.client.module.manage.menu"
    _description = "Administration panel for a personalization"

    line_id = fields.Many2one("justech.client.module.line", required=True, ondelete="cascade")
    is_development = fields.Boolean(related="line_id.is_development", readonly=True)
    module_name = fields.Char(related="line_id.display_name", readonly=True)
    description = fields.Text(related="line_id.description", readonly=True)
    is_paid = fields.Boolean(related="line_id.is_paid", readonly=True)
    is_active = fields.Boolean(related="line_id.is_active", readonly=True)
    is_blocked = fields.Boolean(related="line_id.is_blocked", readonly=True)
    status_label = fields.Char(related="line_id.status_label", readonly=True)
    license_id = fields.Many2one(related="line_id.control_id.license_id", readonly=True)
    company_id = fields.Many2one(related="line_id.control_id.company_id", readonly=True)
    license_html = fields.Html(compute="_compute_panels", sanitize=False)
    companies_html = fields.Html(compute="_compute_panels", sanitize=False)
    includes_html = fields.Html(compute="_compute_panels", sanitize=False)

    @api.depends("line_id", "license_id")
    def _compute_panels(self):
        license_svc = self.env["justech.license.service"]
        internal = license_svc._sudo_internal()
        for rec in self:
            includes = rec.line_id.includes or []
            if includes:
                include_items = "".join(f"<li>{name}</li>" for name in includes)
                rec.includes_html = Markup(
                    f"<ul class='justech-cc-checklist justech-cc-includes'>{include_items}</ul>"
                )
            else:
                rec.includes_html = Markup("<p class='text-muted'>—</p>")
            lic = rec.license_id
            product = internal["justech.commercial.product"].search(
                [("code", "=", rec.line_id.product_code)], limit=1
            )
            if not lic:
                rec.license_html = Markup("<p class='text-muted'>Sin licencia activa.</p>")
                rec.companies_html = False
                continue
            used = len(lic.company_line_ids)
            max_c = lic.max_companies or 0
            quota = f"{used} de {max_c}" if max_c else f"{used} (ilimitadas)"
            expires = lic.expires_at or "—"
            rec.license_html = Markup(
                f"""
                <div class="justech-cc-license-box">
                    <p><strong>Plan:</strong> {license_svc._tier_commercial_label(lic.tier)}</p>
                    <p><strong>Empresas utilizadas:</strong> {quota}</p>
                    <p><strong>Fecha activación:</strong> {rec.line_id.last_modified_at or '—'}</p>
                    <p><strong>Fecha expiración:</strong> {expires}</p>
                </div>
                """
            )
            checklist = license_svc._product_companies_checklist(product, lic)
            items = "".join(
                f"<li>{'☑' if row['enabled'] else '☐'} {row['company_name']}</li>"
                for row in checklist
            ) or "<li class='text-muted'>Sin empresas en licencia.</li>"
            rec.companies_html = Markup(
                f"<p><strong>Empresas habilitadas</strong></p><ul class='justech-cc-checklist'>{items}</ul>"
            )

    def action_activate(self):
        if not self.is_paid:
            raise UserError(
                _("Esta personalización no está incluida en la licencia contratada.")
            )
        return self.line_id._open_action_wizard("activate")

    def action_deactivate(self):
        return self.line_id._open_action_wizard("deactivate")

    def action_mark_paid(self):
        return self.line_id._open_action_wizard("mark_paid")

    def action_mark_unpaid(self):
        return self.line_id._open_action_wizard("mark_unpaid")

    def action_block(self):
        return self.line_id._open_action_wizard("block")

    def action_unblock(self):
        return self.line_id._open_action_wizard("unblock")

    def action_add_company(self):
        return self.line_id._open_action_wizard("add_company")

    def action_remove_company(self):
        return self.line_id._open_action_wizard("remove_company")

    def action_change_license(self):
        return self.line_id._open_action_wizard("change_license")

    def action_view_audit(self):
        self.ensure_one()
        domain = [("product_code", "=", self.line_id.product_code)]
        if self.line_id.control_id.client_name:
            domain.append(("client_name", "=", self.line_id.control_id.client_name))
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría"),
            "res_model": "justech.client.module.audit",
            "view_mode": "list",
            "domain": domain,
            "target": "new",
        }


class JustechClientModuleActionWizard(models.TransientModel):
    _name = "justech.client.module.action.wizard"
    _description = "Client module action confirmation"

    control_id = fields.Many2one("justech.client.module.control")
    line_id = fields.Many2one("justech.client.module.line")
    license_id = fields.Many2one("justech.license", string="Cliente")
    product_code = fields.Char(required=True)
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
        ],
        required=True,
    )
    company_id = fields.Many2one("res.company", string="Empresa")
    target_company_id = fields.Many2one("res.company", string="Empresa")
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
        license_svc.execute_client_module_action(
            self.action_type,
            self.product_code,
            company=self.company_id,
            target_company=self.target_company_id,
            reason=reason,
        )
        control = self.control_id
        if control:
            control._reload_lines()
            return control._return_self_action()
        return {"type": "ir.actions.act_window_close"}


class JustechClientModuleDetail(models.TransientModel):
    """Legacy model kept for compatibility; F31.6 uses Administrar panel."""

    _name = "justech.client.module.detail"
    _description = "Client Module Detail (legacy)"
