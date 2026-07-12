from odoo import api, fields, models, _


PRODUCT_BLURBS = {
    "core": {
        "name": "Justech Core",
        "short": (
            "Núcleo común de la plataforma Justech. Administra la integración entre productos, "
            "permisos, empresas, auditoría, diagnósticos y servicios compartidos. "
            "Este producto es requerido por otros productos Justech y normalmente debe permanecer activo."
        ),
        "capabilities": (
            "Administración Justech; Seguridad y roles; Configuración multiempresa; "
            "Auditoría global; Estado del sistema; Diagnóstico"
        ),
    },
    "fiscal": {
        "name": "Justech Fiscal",
        "short": (
            "Centraliza la gestión fiscal dominicana: comprobantes, NCF, padrón DGII, "
            "reportes, retenciones, auditoría y salud fiscal."
        ),
        "capabilities": (
            "Motor Fiscal NCF; Tipos de comprobante; Rangos y secuencias NCF; Padrón DGII; "
            "Centro Fiscal; Reportes 606/607/608/609/623; Retenciones fiscales (capacidad compartida); "
            "Auditoría Fiscal; Salud Fiscal"
        ),
    },
    "finance": {
        "name": "Justech Finanzas",
        "short": (
            "Centraliza cobros, pagos, pagos abiertos, tesorería, bancos, conciliación "
            "y control financiero."
        ),
        "capabilities": (
            "Cobros de clientes; Pagos a proveedores; Pagos abiertos; Tesorería; Bancos; "
            "Conciliación; Retenciones operativas (capacidad compartida); Auditoría financiera"
        ),
    },
    "warranty": {
        "name": "Justech Garantías",
        "short": (
            "Permite registrar, consultar y dar seguimiento a las garantías de productos "
            "vendidos a clientes."
        ),
        "capabilities": (
            "Registro de garantías; Seguimiento; Reclamaciones; Aprobaciones; Cierre; "
            "Reportes; Configuración"
        ),
    },
    "integrations": {
        "name": "Integraciones",
        "short": (
            "Administra conexiones con DGII, bancos, proveedores, APIs y servicios externos."
        ),
        "capabilities": "DGII; Bancos; Microsoft; APIs; Proveedores; Servicios externos",
    },
    "audit": {
        "name": "Auditoría y cumplimiento",
        "short": (
            "Centraliza trazabilidad, diagnósticos, alertas, controles y registros de cambios "
            "de la plataforma Justech."
        ),
        "capabilities": (
            "Auditoría global; Logs funcionales; Diagnóstico; Estado del sistema; "
            "Historial de cambios; Alertas"
        ),
    },
}


class JustechAdminProduct(models.Model):
    _name = "justech.admin.product"
    _description = "Producto funcional Justech"
    _order = "sequence, name"

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    short_description = fields.Text(required=True, translate=True)
    long_description = fields.Html(translate=True)
    capabilities_text = fields.Text(
        string="Capacidades incluidas",
        help="Lista funcional de capacidades (no nombres técnicos).",
    )
    icon = fields.Char(default="fa-cube")
    sequence = fields.Integer(default=100)
    active = fields.Boolean(default=True)
    module_ids = fields.One2many("justech.admin.module", "product_id", string="Submódulos")
    company_line_ids = fields.One2many(
        "justech.admin.module.company",
        "product_id",
        string="Estados por empresa",
    )
    module_count = fields.Integer(compute="_compute_counts", string="Submódulos")
    installed_count = fields.Integer(compute="_compute_counts", string="Instalados")
    active_company_count = fields.Integer(compute="_compute_counts", string="Activaciones")
    meta_label = fields.Char(compute="_compute_counts", string="Resumen")
    empty_modules_html = fields.Html(compute="_compute_counts", sanitize=False)
    status_visual = fields.Selection(
        selection=[
            ("green", "Correcto"),
            ("yellow", "Atención"),
            ("red", "Error"),
            ("blue", "Informativo"),
            ("grey", "No configurado"),
        ],
        compute="_compute_counts",
    )
    estado_general = fields.Char(compute="_compute_counts", string="Estado general")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "El código de producto debe ser único."),
    ]

    @api.model
    def dedupe_by_code(self):
        Data = self.env["ir.model.data"].sudo()
        Module = self.env["justech.admin.module"].sudo()
        for code in ["core", "fiscal", "finance", "warranty", "integrations", "audit"]:
            products = self.sudo().search([("code", "=", code)], order="id")
            if len(products) <= 1:
                continue
            keeper = self.env["justech.admin.product"]
            for p in products:
                if Data.search(
                    [
                        ("model", "=", "justech.admin.product"),
                        ("res_id", "=", p.id),
                        ("module", "=", "justech_admin_center"),
                    ],
                    limit=1,
                ):
                    keeper = p
                    break
            if not keeper:
                keeper = products.filtered(lambda p: p.module_ids)[:1] or products[:1]
            for p in products - keeper:
                Module.search([("product_id", "=", p.id)]).write({"product_id": keeper.id})
                p.unlink()
        return True

    def _compute_counts(self):
        CompanyLine = self.env["justech.admin.module.company"]
        for rec in self:
            mods = rec.module_ids
            rec.module_count = len(mods)
            rec.installed_count = len(mods.filtered(lambda m: m.technical_state == "installed"))
            active_lines = CompanyLine.search_count(
                [("module_id", "in", mods.ids), ("functional_state", "=", "active")]
            )
            rec.active_company_count = active_lines
            companies_active = len(
                set(
                    CompanyLine.search(
                        [("module_id", "in", mods.ids), ("functional_state", "=", "active")]
                    ).mapped("company_id").ids
                )
            )
            rec.meta_label = _(
                "%(subs)s submódulos · %(inst)s instalados · Activo en %(cos)s empresas"
            ) % {
                "subs": rec.module_count,
                "inst": rec.installed_count,
                "cos": companies_active,
            }
            if mods.filtered(lambda m: m.status_visual == "red"):
                rec.status_visual = "red"
                rec.estado_general = _("Error")
            elif mods.filtered(lambda m: m.status_visual == "yellow"):
                rec.status_visual = "yellow"
                rec.estado_general = _("Requiere atención")
            elif rec.installed_count:
                rec.status_visual = "green"
                rec.estado_general = _("Activo")
            else:
                rec.status_visual = "grey"
                rec.estado_general = _("No configurado")
            if not mods:
                rec.empty_modules_html = (
                    '<div class="o_jac_empty">'
                    "<p>%s</p></div>"
                ) % (
                    _("No hay submódulos Justech disponibles actualmente para este producto.")
                    if rec.code != "integrations"
                    else _("No hay integraciones Justech disponibles actualmente.")
                )
            else:
                rec.empty_modules_html = False

    @api.model
    def refresh_blurbs(self):
        """Update functional copy from catalog without touching auth."""
        for code, blurb in PRODUCT_BLURBS.items():
            product = self.search([("code", "=", code)], limit=1)
            if not product:
                continue
            product.write(
                {
                    "name": blurb["name"],
                    "short_description": blurb["short"],
                    "capabilities_text": blurb["capabilities"],
                    "long_description": (
                        "<p>%s</p><p><strong>%s</strong> %s</p>"
                        % (
                            blurb["short"],
                            _("Capacidades:"),
                            blurb["capabilities"],
                        )
                    ),
                }
            )
        return True

    def action_open_detail(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "justech.admin.product",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_run_diagnostics(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        for mod in self.module_ids.filtered(lambda m: m.technical_state == "installed"):
            self.env["justech.admin.health.service"].run_module_health(mod)
        return self.env["justech.admin.console"].action_open_health()

    def action_open_users(self):
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Usuarios y roles"),
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("share", "=", False)],
            "target": "current",
        }

    def action_open_audit(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Auditoría — %s") % self.name,
            "res_model": "justech.admin.audit.log",
            "view_mode": "list,form",
            "domain": [("module_id", "in", self.module_ids.ids)],
            "target": "current",
        }

    def action_open_company_matrix(self):
        self.ensure_one()
        gate = self.env["justech.admin.center.auth.service"].gate_or_wizard()
        if gate:
            return gate
        return {
            "type": "ir.actions.act_window",
            "name": _("Empresas — %s") % self.name,
            "res_model": "justech.admin.module.company",
            "view_mode": "list,form",
            "domain": [("product_id", "=", self.id)],
            "context": {"search_default_group_company": 1},
            "target": "current",
        }
