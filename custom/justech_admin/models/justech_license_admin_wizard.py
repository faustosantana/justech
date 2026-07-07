# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.justech_modules.exceptions import JustechLicenseError


class JustechLicenseAdminModuleLine(models.TransientModel):
    _name = "justech.license.admin.module.line"
    _description = "License Admin Module Selection"
    _order = "sequence, product_name"

    wizard_id = fields.Many2one(
        "justech.license.admin.wizard", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    customization_code = fields.Char()
    product_code = fields.Char()
    product_name = fields.Char(required=True)
    description = fields.Text()
    selected = fields.Boolean(default=True)


class JustechLicenseAdminWizard(models.TransientModel):
    _name = "justech.license.admin.wizard"
    _description = "Justech License Administration Wizard"

    mode = fields.Selection(
        [
            ("create", "Crear licencia"),
            ("activate", "Activar licencia"),
            ("change_plan", "Cambiar plan"),
            ("add_company", "Agregar empresa"),
            ("remove_company", "Quitar empresa"),
            ("set_primary_company", "Cambiar empresa principal"),
            ("suspend", "Suspender licencia"),
            ("reactivate", "Reactivar licencia"),
            ("renew", "Renovar licencia"),
        ],
        required=True,
        default="create",
    )
    control_id = fields.Many2one("justech.control.licenses")
    dashboard_id = fields.Many2one("justech.control.license.dashboard")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    license_id = fields.Many2one("justech.license", string="Licencia")
    license_name = fields.Char(string="Nombre del cliente")
    tier = fields.Selection(
        [
            ("TRIAL", "Trial"),
            ("STD", "Standard"),
            ("PRO", "Professional"),
            ("ENT", "Enterprise"),
        ],
        default="STD",
        required=True,
    )
    target_state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("active", "Activa"),
        ],
        default="active",
        required=True,
    )
    max_companies = fields.Integer(string="Empresas permitidas", default=1)
    company_ids = fields.Many2many(
        "res.company",
        "justech_license_admin_wizard_company_rel",
        "wizard_id",
        "company_id",
        string="Empresas incluidas",
    )
    starts_at = fields.Date(string="Fecha inicio", default=fields.Date.context_today)
    expires_at = fields.Date(string="Fecha fin")
    module_line_ids = fields.One2many(
        "justech.license.admin.module.line", "wizard_id", string="Módulos incluidos"
    )
    target_company_id = fields.Many2one("res.company", string="Empresa a agregar")
    admin_key = fields.Char(string="Clave Administrativa Justech", required=True)

    @api.model
    def _build_catalog_commands(self, license_rec=None):
        rows = self.env["justech.license.service"].get_license_wizard_catalog(
            license_rec=license_rec
        )
        commands = []
        for row in rows:
            name = (row.get("product_name") or "").strip()
            if not name:
                continue
            commands.append(
                (
                    0,
                    0,
                    {
                        "customization_code": row.get("customization_code"),
                        "product_code": row.get("product_code") or False,
                        "product_name": name,
                        "description": row.get("description") or "",
                        "sequence": row.get("sequence", 10),
                        "selected": row.get("selected", True),
                    },
                )
            )
        return commands

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.setdefault("dashboard_id", self.env.context.get("default_dashboard_id"))
        company = self.env["res.company"].browse(
            res.get("company_id") or self.env.company.id
        )
        license_svc = self.env["justech.license.service"]
        license_rec = license_svc._get_active_license_for_company(company)
        if not license_rec:
            license_rec = license_svc._sudo_internal()["justech.license"].search(
                [
                    ("company_line_ids.company_id", "=", company.id),
                    ("state", "in", ("draft", "active")),
                ],
                limit=1,
                order="id desc",
            )
        if license_rec:
            res.setdefault("license_id", license_rec.id)
            res.setdefault("license_name", license_rec.name)
            res.setdefault("tier", license_rec.tier)
            res.setdefault("max_companies", license_rec.max_companies or 1)
            res.setdefault("starts_at", license_rec.starts_at)
            res.setdefault("expires_at", license_rec.expires_at)
            res.setdefault(
                "company_ids",
                [(6, 0, license_rec.company_line_ids.mapped("company_id").ids)],
            )
            if license_rec.state == "active":
                res.setdefault("target_state", "active")
        else:
            res.setdefault("license_name", company.name)
            res.setdefault("company_ids", [(6, 0, [company.id])])
        if "module_line_ids" in fields_list and not res.get("module_line_ids"):
            lic = license_rec
            if res.get("license_id"):
                lic = license_svc._sudo_internal()["justech.license"].browse(
                    res["license_id"]
                )
            res["module_line_ids"] = self._build_catalog_commands(license_rec=lic)
        return res

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if not self.company_id:
            return
        license_svc = self.env["justech.license.service"]
        license_rec = license_svc._get_active_license_for_company(self.company_id)
        if not license_rec:
            license_rec = license_svc._sudo_internal()["justech.license"].search(
                [
                    ("company_line_ids.company_id", "=", self.company_id.id),
                    ("state", "in", ("draft", "active")),
                ],
                limit=1,
                order="id desc",
            )
        if license_rec:
            self.license_id = license_rec
            self.license_name = license_rec.name
            self.tier = license_rec.tier
            self.max_companies = license_rec.max_companies or 1
            self.starts_at = license_rec.starts_at
            self.expires_at = license_rec.expires_at
            self.company_ids = license_rec.company_line_ids.mapped("company_id")
        else:
            self.license_id = False
            self.license_name = self.company_id.name
            self.company_ids = self.company_id

    def _selected_product_codes(self):
        Product = self.env["justech.license.service"]._sudo_internal()[
            "justech.commercial.product"
        ]
        codes = []
        for line in self.module_line_ids.filtered("selected"):
            if not line.product_code:
                continue
            if not Product.search([("code", "=", line.product_code)], limit=1):
                continue
            codes.append(line.product_code)
        return codes

    def _verify_admin_key(self):
        svc = self.env["justech.admin.access.service"]
        if not svc.user_has_key():
            raise UserError(
                _("Debe crear una Clave Administrativa Justech antes de continuar.")
            )
        svc.verify_key_only(self.admin_key, action=svc.CRITICAL_LICENSE_CHANGE)
        return svc.issue_critical_grant(svc.CRITICAL_LICENSE_CHANGE)

    def _default_product_code(self):
        codes = self._selected_product_codes()
        if codes:
            return codes[0]
        return "contabilidad_rd"

    def _return_after_success(self):
        self.ensure_one()
        if self.dashboard_id:
            return self.dashboard_id.action_open(
                self.license_id.id,
                hub_id=self.control_id.id if self.control_id else False,
            )
        if self.control_id:
            return self.control_id.action_reopen()
        return self.env["justech.control.licenses"].action_open()

    def action_confirm(self):
        self.ensure_one()
        if self.mode in ("create", "activate") and not self._selected_product_codes():
            raise UserError(_("Seleccione al menos un módulo incluido."))
        token = self._verify_admin_key()
        license_svc = self.env["justech.license.service"].with_context(
            justech_critical_token=token
        )
        try:
            if self.mode == "create":
                license_svc.admin_upsert_license(
                    self.company_id,
                    tier=self.tier,
                    target_state=self.target_state,
                    company_ids=self.company_ids.ids,
                    starts_at=self.starts_at,
                    expires_at=self.expires_at,
                    max_companies=self.max_companies,
                    product_codes=self._selected_product_codes(),
                    license_id=self.license_id.id if self.license_id else False,
                    name=self.license_name or self.company_id.name,
                )
            elif self.mode == "activate":
                if not self.license_id:
                    license_svc.admin_upsert_license(
                        self.company_id,
                        tier=self.tier,
                        target_state="active",
                        company_ids=self.company_ids.ids or [self.company_id.id],
                        starts_at=self.starts_at,
                        expires_at=self.expires_at,
                        max_companies=self.max_companies,
                        product_codes=self._selected_product_codes(),
                        name=self.license_name or self.company_id.name,
                    )
                else:
                    license_svc.admin_activate_license(
                        self.license_id.id, company=self.company_id
                    )
            elif self.mode == "change_plan":
                if not self.license_id:
                    raise UserError(_("No hay licencia para cambiar el plan."))
                license_svc.admin_change_plan(
                    self.license_id.id, self.tier, company=self.company_id
                )
            elif self.mode == "add_company":
                if not self.license_id:
                    raise UserError(_("No hay licencia activa."))
                license_svc.admin_add_company_to_license(
                    self.license_id.id,
                    self.target_company_id,
                    company=self.company_id,
                )
            elif self.mode == "remove_company":
                if not self.license_id or not self.target_company_id:
                    raise UserError(_("Seleccione la licencia y la empresa."))
                svc = self.env["justech.admin.access.service"]
                platform_token = svc.issue_critical_grant(
                    svc.CRITICAL_PLATFORM_MUTATION
                )
                license_svc.with_context(
                    justech_critical_token=platform_token,
                    justech_skip_critical_step_up=True,
                ).execute_client_module_action(
                    "remove_company",
                    self._default_product_code(),
                    company=self.company_id,
                    target_company=self.target_company_id,
                )
            elif self.mode == "set_primary_company":
                if not self.license_id or not self.target_company_id:
                    raise UserError(_("Seleccione la empresa principal."))
                primary = self.license_id.company_line_ids[:1].company_id
                if self.target_company_id == primary:
                    return self._return_after_success()
                company_ids = self.license_id.company_line_ids.mapped(
                    "company_id"
                ).ids
                if self.target_company_id.id not in company_ids:
                    raise UserError(_("La empresa no está asociada a esta licencia."))
                if len(company_ids) > 1:
                    raise UserError(
                        _(
                            "Con varias empresas asociadas, la empresa principal "
                            "permanece fijada por el contrato. Retire las demás "
                            "empresas o contacte a Justech para reasignar la principal."
                        )
                    )
            elif self.mode == "suspend":
                if not self.license_id:
                    raise UserError(_("No hay licencia para suspender."))
                license_svc.admin_upsert_license(
                    self.company_id,
                    tier=self.license_id.tier,
                    target_state="revoked",
                    license_id=self.license_id.id,
                    company_ids=self.license_id.company_line_ids.mapped(
                        "company_id"
                    ).ids,
                    starts_at=self.license_id.starts_at,
                    expires_at=self.license_id.expires_at,
                    max_companies=self.license_id.max_companies,
                    name=self.license_id.name,
                )
            elif self.mode == "reactivate":
                if not self.license_id:
                    raise UserError(_("No hay licencia para reactivar."))
                license_svc.admin_activate_license(
                    self.license_id.id, company=self.company_id
                )
            elif self.mode == "renew":
                if not self.license_id:
                    raise UserError(_("No hay licencia para renovar."))
                license_svc.admin_upsert_license(
                    self.company_id,
                    tier=self.license_id.tier,
                    target_state="active"
                    if self.license_id.state in ("active", "revoked", "expired")
                    else self.license_id.state,
                    license_id=self.license_id.id,
                    company_ids=self.license_id.company_line_ids.mapped(
                        "company_id"
                    ).ids,
                    starts_at=self.starts_at or self.license_id.starts_at,
                    expires_at=self.expires_at,
                    max_companies=self.license_id.max_companies,
                    name=self.license_id.name,
                )
        except JustechLicenseError as exc:
            raise UserError(str(exc.args[0])) from None

        return self._return_after_success()
