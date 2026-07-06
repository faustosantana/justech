# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JustechClientModuleControl(models.TransientModel):
    _name = "justech.client.module.control"
    _description = "Centro de Administración Justech"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
    )
    line_ids = fields.One2many("justech.client.module.line", "control_id")
    has_admin_key = fields.Boolean(compute="_compute_key_state")
    show_key_banner = fields.Boolean(compute="_compute_key_state")
    summary_contracted = fields.Integer(compute="_compute_summary")
    summary_active = fields.Integer(compute="_compute_summary")
    summary_pending = fields.Integer(compute="_compute_summary")
    summary_blocked = fields.Integer(compute="_compute_summary")
    summary_companies = fields.Integer(compute="_compute_summary")
    summary_plan = fields.Char(compute="_compute_summary")
    summary_html = fields.Html(compute="_compute_summary_html", sanitize=False)
    key_banner_html = fields.Html(compute="_compute_key_banner_html", sanitize=False)
    search_text = fields.Char(string="Buscar")
    filter_status = fields.Selection(
        [
            ("all", "Todos"),
            ("paid_active", "Pagado y activo"),
            ("paid_inactive", "Pagado pero inactivo"),
            ("not_paid", "No pagado"),
            ("blocked", "Bloqueado"),
            ("expired", "Expirado"),
            ("coming_soon", "Próximamente"),
        ],
        default="all",
        string="Estado",
    )
    filter_active_only = fields.Boolean(string="Solo activos")
    filter_contracted_only = fields.Boolean(string="Solo contratados")
    filter_pending_only = fields.Boolean(string="Solo pendientes")
    panel_open = fields.Boolean(default=False)
    panel_line_id = fields.Many2one("justech.client.module.line", ondelete="set null")
    panel_html = fields.Html(compute="_compute_panel_html", sanitize=False)

    @api.model
    def action_open(self):
        self.env["justech.admin.access.service"].require_justech_settings_access()
        rec = self.create({"company_id": self.env.company.id})
        rec._reload_lines()
        return {
            "type": "ir.actions.act_window",
            "name": _("Centro de Administración Justech"),
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends()
    def _compute_key_state(self):
        svc = self.env["justech.admin.access.service"]
        for rec in self:
            rec.has_admin_key = svc.user_has_key()
            rec.show_key_banner = not rec.has_admin_key

    @api.depends("line_ids.is_paid", "line_ids.is_active", "line_ids.status", "company_id")
    def _compute_summary(self):
        license_svc = self.env["justech.license.service"]
        for rec in self:
            lines = rec.line_ids
            rec.summary_contracted = len(lines.filtered("is_paid"))
            rec.summary_active = len(lines.filtered("is_active"))
            rec.summary_pending = len(
                lines.filtered(lambda l: not l.is_paid and l.status != "coming_soon")
            )
            rec.summary_blocked = len(lines.filtered(lambda l: l.status == "blocked"))
            license_rec = license_svc._get_active_license_for_company(rec.company_id)
            rec.summary_companies = (
                len(license_rec.company_line_ids) if license_rec else 1
            )
            rec.summary_plan = license_rec.tier if license_rec else "—"

    @api.depends(
        "summary_contracted",
        "summary_active",
        "summary_pending",
        "summary_blocked",
        "summary_companies",
        "summary_plan",
    )
    def _compute_summary_html(self):
        for rec in self:
            rec.summary_html = Markup(
                f"""
                <div class="justech-cc-dashboard">
                    <div class="justech-cc-hero">
                        <h1>Centro de Administración Justech</h1>
                        <p>Administre las personalizaciones, licencias y empresas habilitadas del ERP.</p>
                    </div>
                    <div class="justech-cc-section">
                        <div class="justech-cc-grid">
                            <div class="justech-cc-card justech-cc-green">
                                <div class="justech-cc-card-title">Módulos contratados</div>
                                <div class="justech-cc-card-value">{rec.summary_contracted}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-green">
                                <div class="justech-cc-card-title">Módulos activos</div>
                                <div class="justech-cc-card-value">{rec.summary_active}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-yellow">
                                <div class="justech-cc-card-title">Pendientes de pago</div>
                                <div class="justech-cc-card-value">{rec.summary_pending}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-red">
                                <div class="justech-cc-card-title">Bloqueados</div>
                                <div class="justech-cc-card-value">{rec.summary_blocked}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-gray">
                                <div class="justech-cc-card-title">Empresas habilitadas</div>
                                <div class="justech-cc-card-value">{rec.summary_companies}</div>
                            </div>
                            <div class="justech-cc-card justech-cc-blue">
                                <div class="justech-cc-card-title">Plan contratado</div>
                                <div class="justech-cc-card-value justech-cc-card-plan">{rec.summary_plan or '—'}</div>
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

    @api.depends("panel_line_id", "panel_open")
    def _compute_panel_html(self):
        Audit = self.env["justech.client.module.audit"].sudo()
        for rec in self:
            if not rec.panel_open or not rec.panel_line_id:
                rec.panel_html = False
                continue
            line = rec.panel_line_id
            license_rec = self.env["justech.license.service"]._get_active_license_for_company(
                rec.company_id
            )
            companies = (
                ", ".join(license_rec.company_line_ids.mapped("company_id.name"))
                if license_rec
                else rec.company_id.name
            )
            audits = Audit.search(
                [
                    ("product_code", "=", line.product_code),
                    ("company_id", "=", rec.company_id.id),
                ],
                order="create_date desc",
                limit=8,
            )
            history = "".join(
                f"<li><span>{a.create_date}</span> {a.user_id.name or '—'} — {a.action} ({a.result})</li>"
                for a in audits
            ) or "<li class='text-muted'>Sin historial reciente.</li>"
            includes = ", ".join(line.includes or []) or "—"
            rec.panel_html = Markup(
                f"""
                <div class="justech-cc-side-panel">
                    <div class="justech-cc-side-header">
                        <h2>{line.name}</h2>
                        <span class="justech-cc-status justech-cc-status-{line.status}">{line.status_label}</span>
                    </div>
                    <p class="justech-cc-side-desc">{line.description or '—'}</p>
                    <dl class="justech-cc-side-meta">
                        <dt>Licencia</dt><dd>{line.license_label or '—'}</dd>
                        <dt>Empresas habilitadas</dt><dd>{companies}</dd>
                        <dt>Fecha activación</dt><dd>{line.activated_at or '—'}</dd>
                        <dt>Activado por</dt><dd>{line.activated_by_name or '—'}</dd>
                        <dt>Origen</dt><dd>{line.origin_label or 'Justech'}</dd>
                        <dt>Qué incluye</dt><dd>{includes}</dd>
                    </dl>
                    <h3>Historial</h3>
                    <ul class="justech-cc-side-history">{history}</ul>
                </div>
                """
            )

    @api.onchange(
        "company_id",
        "search_text",
        "filter_status",
        "filter_active_only",
        "filter_contracted_only",
        "filter_pending_only",
    )
    def _onchange_filters(self):
        if self.company_id:
            self._reload_lines()

    def _reload_lines(self):
        rows = self.env["justech.license.service"].get_client_module_rows(
            company=self.company_id, view_only=True
        )
        commands = [(5, 0, 0)]
        search = (self.search_text or "").strip().lower()
        for row in rows:
            if search and search not in (row.get("name") or "").lower():
                if search not in (row.get("description") or "").lower():
                    continue
            if self.filter_status and self.filter_status != "all":
                if row.get("status") != self.filter_status:
                    continue
            if self.filter_active_only and not row.get("is_active"):
                continue
            if self.filter_contracted_only and not row.get("is_paid"):
                continue
            if self.filter_pending_only and (
                row.get("is_paid") or row.get("status") == "coming_soon"
            ):
                continue
            commands.append((0, 0, row))
        self.line_ids = commands
        if self.panel_line_id and self.panel_line_id not in self.line_ids:
            self.panel_open = False
            self.panel_line_id = False

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

    def action_close_panel(self):
        self.ensure_one()
        self.panel_open = False
        self.panel_line_id = False
        return True

    def action_add_company_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Agregar empresa"),
            "res_model": "justech.client.module.action.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_control_id": self.id,
                "default_action_type": "add_company",
                "default_product_code": "contabilidad_rd",
                "default_company_id": self.company_id.id,
            },
        }

    def _return_self_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Centro de Administración Justech"),
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
    product_code = fields.Char(required=True)
    name = fields.Char(string="Personalización", readonly=True)
    description = fields.Text(readonly=True)
    is_paid = fields.Boolean(string="Pagado", readonly=True)
    is_active = fields.Boolean(string="Activo", readonly=True)
    is_blocked = fields.Boolean(readonly=True)
    paid_label = fields.Char(string="Pagado", compute="_compute_labels", readonly=True)
    active_label = fields.Char(string="Activo", compute="_compute_labels", readonly=True)
    company_name = fields.Char(string="Empresa", readonly=True)
    plan_label = fields.Char(string="Plan", readonly=True)
    license_label = fields.Char(string="Licencia", readonly=True)
    activated_at = fields.Datetime(readonly=True)
    activated_by_name = fields.Char(readonly=True)
    last_modified_at = fields.Datetime(string="Última modificación", readonly=True)
    last_modified_by_name = fields.Char(string="Modificado por", readonly=True)
    status = fields.Char(readonly=True)
    status_label = fields.Char(string="Estado", readonly=True)
    origin = fields.Char(readonly=True)
    origin_label = fields.Char(string="Origen", readonly=True)
    configured = fields.Boolean(readonly=True)
    includes = fields.Json(readonly=True)

    @api.depends("is_paid", "is_active")
    def _compute_labels(self):
        for line in self:
            line.paid_label = _("Sí") if line.is_paid else _("No")
            line.active_label = _("Sí") if line.is_active else _("No")

    def _open_action_wizard(self, action_type):
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
            },
        }

    def action_open_manage_menu(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Administrar"),
            "res_model": "justech.client.module.manage.menu",
            "view_mode": "form",
            "target": "new",
            "context": {"default_line_id": self.id},
        }

    def action_view_details(self):
        self.ensure_one()
        self.control_id.write(
            {"panel_line_id": self.id, "panel_open": True}
        )
        return self.control_id._return_self_action()

    def action_request_activation(self):
        raise UserError(
            _(
                "Solicitud registrada. Contacte a Justech para activar esta personalización en su licencia."
            )
        )


class JustechClientModuleManageMenu(models.TransientModel):
    _name = "justech.client.module.manage.menu"
    _description = "Administration menu for a personalization"

    line_id = fields.Many2one("justech.client.module.line", required=True, ondelete="cascade")
    module_name = fields.Char(related="line_id.name", readonly=True)
    is_paid = fields.Boolean(related="line_id.is_paid", readonly=True)
    is_active = fields.Boolean(related="line_id.is_active", readonly=True)

    def action_view_details(self):
        return self.line_id.action_view_details()

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

    def action_add_company(self):
        return self.line_id._open_action_wizard("add_company")

    def action_view_audit(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría"),
            "res_model": "justech.client.module.audit",
            "view_mode": "list",
            "domain": [
                ("product_code", "=", self.line_id.product_code),
                ("company_id", "=", self.line_id.control_id.company_id.id),
            ],
            "target": "new",
        }


class JustechClientModuleActionWizard(models.TransientModel):
    _name = "justech.client.module.action.wizard"
    _description = "Client module action confirmation"

    control_id = fields.Many2one("justech.client.module.control")
    line_id = fields.Many2one("justech.client.module.line")
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
            ("remove_company", "Quitar empresa de licencia"),
        ],
        required=True,
    )
    company_id = fields.Many2one("res.company", string="Empresa")
    target_company_id = fields.Many2one("res.company", string="Empresa destino")
    admin_key = fields.Char(string="Clave Administrativa Justech", required=True)
    license_label = fields.Char(compute="_compute_license_info", readonly=True)
    companies_used = fields.Integer(compute="_compute_license_info", readonly=True)
    companies_available = fields.Integer(compute="_compute_license_info", readonly=True)
    license_info_html = fields.Html(compute="_compute_license_info", sanitize=False)

    @api.depends("company_id", "action_type")
    def _compute_license_info(self):
        license_svc = self.env["justech.license.service"]
        for wiz in self:
            if wiz.action_type != "add_company":
                wiz.license_label = False
                wiz.companies_used = 0
                wiz.companies_available = 0
                wiz.license_info_html = False
                continue
            license_rec = license_svc._get_active_license_for_company(wiz.company_id)
            if not license_rec:
                wiz.license_label = "—"
                wiz.companies_used = 0
                wiz.companies_available = 0
                wiz.license_info_html = Markup(
                    "<p class='text-muted'>No hay licencia activa para esta empresa.</p>"
                )
                continue
            used = len(license_rec.company_line_ids)
            max_c = license_rec.max_companies or 0
            available = max(max_c - used, 0) if max_c else 999
            wiz.license_label = license_rec.tier or "—"
            wiz.companies_used = used
            wiz.companies_available = available
            wiz.license_info_html = Markup(
                f"""
                <div class="justech-cc-license-box">
                    <p><strong>Licencia:</strong> {wiz.license_label}</p>
                    <p><strong>Empresas utilizadas:</strong> {used}</p>
                    <p><strong>Empresas disponibles:</strong> {available if max_c else 'Ilimitadas'}</p>
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
        license_svc.execute_client_module_action(
            self.action_type,
            self.product_code,
            company=self.company_id,
            target_company=self.target_company_id,
        )
        control = self.control_id
        if control:
            control._reload_lines()
            return control._return_self_action()
        return {"type": "ir.actions.act_window_close"}


class JustechClientModuleDetail(models.TransientModel):
    _name = "justech.client.module.detail"
    _description = "Client Module Detail"

    product_code = fields.Char(readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    name = fields.Char(readonly=True)
    description = fields.Text(readonly=True)
    includes_text = fields.Char(string="Qué incluye", readonly=True)
    is_paid = fields.Boolean(readonly=True)
    is_active = fields.Boolean(readonly=True)
    paid_label = fields.Char(compute="_compute_labels", readonly=True)
    active_label = fields.Char(compute="_compute_labels", readonly=True)
    status_label = fields.Char(string="Estado", readonly=True)
    plan_label = fields.Char(string="Licencia", readonly=True)
    origin_label = fields.Char(string="Origen", readonly=True)
    activated_at = fields.Datetime(string="Fecha activación", readonly=True)
    activated_by_name = fields.Char(string="Activado por", readonly=True)
    companies_text = fields.Char(string="Empresas habilitadas", readonly=True)
    detail_html = fields.Html(compute="_compute_detail_html", sanitize=False)
    audit_html = fields.Html(compute="_compute_audit_html", sanitize=False)

    @api.depends("is_paid", "is_active")
    def _compute_labels(self):
        for rec in self:
            rec.paid_label = _("Sí") if rec.is_paid else _("No")
            rec.active_label = _("Sí") if rec.is_active else _("No")

    @api.model
    def action_open(self, product_code, company=None):
        company = company or self.env.company
        rows = self.env["justech.license.service"].get_client_module_rows(
            company=company, view_only=True
        )
        row = next((r for r in rows if r["product_code"] == product_code), None)
        if not row:
            raise UserError(_("Personalización no encontrada."))
        license_rec = self.env["justech.license.service"]._get_active_license_for_company(
            company
        )
        companies = (
            license_rec.company_line_ids.mapped("company_id.name")
            if license_rec
            else [company.name]
        )
        rec = self.create(
            {
                "product_code": product_code,
                "company_id": company.id,
                "name": row["name"],
                "description": row["description"],
                "includes_text": ", ".join(row.get("includes") or []),
                "is_paid": row["is_paid"],
                "is_active": row["is_active"],
                "status_label": row["status_label"],
                "plan_label": row.get("license_label") or row["plan_label"],
                "origin_label": row.get("origin_label") or "Justech",
                "activated_at": row["activated_at"],
                "activated_by_name": row["activated_by_name"],
                "companies_text": ", ".join(companies),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": row["name"],
            "res_model": self._name,
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends("name", "status_label", "includes_text")
    def _compute_detail_html(self):
        for rec in self:
            rec.detail_html = Markup(
                f"""
                <div class="justech-cc-sheet-header">
                    <p><strong>Estado:</strong> {rec.status_label or '—'}</p>
                    <p><strong>Pagado:</strong> {rec.paid_label}</p>
                    <p><strong>Activo:</strong> {rec.active_label}</p>
                    <p><strong>Licencia:</strong> {rec.plan_label or '—'}</p>
                    <p><strong>Origen:</strong> {rec.origin_label or 'Justech'}</p>
                    <p><strong>Fecha activación:</strong> {rec.activated_at or '—'}</p>
                    <p><strong>Activado por:</strong> {rec.activated_by_name or '—'}</p>
                    <p><strong>Empresas habilitadas:</strong> {rec.companies_text or '—'}</p>
                    <p><strong>Qué incluye:</strong> {rec.includes_text or '—'}</p>
                </div>
                """
            )

    @api.depends("product_code", "company_id")
    def _compute_audit_html(self):
        Audit = self.env["justech.client.module.audit"].sudo()
        for rec in self:
            entries = Audit.search(
                [
                    ("product_code", "=", rec.product_code),
                    ("company_id", "=", rec.company_id.id),
                ],
                order="create_date desc",
                limit=5,
            )
            if not entries:
                rec.audit_html = Markup("<p class='text-muted'>Sin auditoría reciente.</p>")
                continue
            rows = "".join(
                f"<li>{e.create_date}: {e.user_id.name or '—'} — {e.action} ({e.result}) IP {e.ip_address or '—'}</li>"
                for e in entries
            )
            rec.audit_html = Markup(f"<ul class='mb-0'>{rows}</ul>")

    def _open_detail_wizard(self, action_type):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Clave Administrativa Justech"),
            "res_model": "justech.client.module.action.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_code": self.product_code,
                "default_action_type": action_type,
                "default_company_id": self.company_id.id,
            },
        }

    def action_mark_paid(self):
        return self._open_detail_wizard("mark_paid")

    def action_mark_unpaid(self):
        return self._open_detail_wizard("mark_unpaid")

    def action_activate(self):
        if not self.is_paid:
            raise UserError(
                _("Esta personalización no está incluida en la licencia contratada.")
            )
        return self._open_detail_wizard("activate")

    def action_deactivate(self):
        return self._open_detail_wizard("deactivate")

    def action_block(self):
        return self._open_detail_wizard("block")

    def action_unblock(self):
        return self._open_detail_wizard("unblock")

    def action_add_company(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Agregar empresa"),
            "res_model": "justech.client.module.action.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_code": self.product_code,
                "default_action_type": "add_company",
                "default_company_id": self.company_id.id,
            },
        }

    def action_view_audit(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría"),
            "res_model": "justech.client.module.audit",
            "view_mode": "list",
            "domain": [
                ("product_code", "=", self.product_code),
                ("company_id", "=", self.company_id.id),
            ],
            "target": "new",
        }
