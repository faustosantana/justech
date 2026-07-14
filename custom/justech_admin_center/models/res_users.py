from odoo import api, fields, models
import re


UAT_PATTERN = re.compile(
    r"(uat|test|ux\s*shot|shot_admin|padr[oó]n|std\b|prueba)",
    re.IGNORECASE,
)

ROLE_HINTS = {
    "uat_admin_fiscal": "Administrador Fiscal",
    "uat_responsable_fiscal": "Responsable Fiscal",
    "uat_usuario_fiscal": "Usuario Fiscal",
    "uat_contador": "Contador / reportes",
    "uat_compras": "Compras / padrón",
    "uat_ventas": "Ventas / padrón",
    "shot_admin": "Administrador (capturas UX)",
}


class ResUsers(models.Model):
    _inherit = "res.users"

    justech_is_test_user = fields.Boolean(
        string="Usuario de prueba Justech",
        compute="_compute_justech_test_flags",
        search="_search_justech_is_test_user",
    )
    justech_test_classification = fields.Selection(
        selection=[
            ("required_temp", "Cuenta de prueba requerida temporalmente"),
            ("evidence", "Cuenta de evidencia"),
            ("obsolete", "Cuenta obsoleta"),
            ("real", "Usuario real"),
        ],
        compute="_compute_justech_test_flags",
        string="Clasificación",
    )
    justech_test_role_label = fields.Char(
        compute="_compute_justech_test_flags",
        string="Rol probado",
    )

    justech_admin_center_role = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("justech_admin", "Administrador Justech"),
        ],
        string="Administración Justech",
        compute="_compute_justech_admin_center_role",
        inverse="_inverse_justech_admin_center_role",
        store=False,
        groups="base.group_system,justech_admin_center.group_justech_admin_center_manager",
    )
    justech_role_explanation = fields.Char(
        compute="_compute_justech_admin_center_role",
        string="Este rol permite",
    )
    justech_fiscal_role_explanation = fields.Char(
        compute="_compute_justech_fiscal_role_explanation",
        string="Este rol permite",
    )
    justech_ecf_role = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("ecf_readonly", "Solo lectura e-CF"),
            ("ecf_operator", "Operador e-CF"),
            ("ecf_responsible", "Responsable e-CF"),
            ("ecf_admin", "Administrador e-CF"),
        ],
        string="Rol e-CF",
        compute="_compute_justech_ecf_role",
        inverse="_inverse_justech_ecf_role",
        store=False,
        groups="base.group_system,justech_admin_center.group_justech_admin_center_manager",
    )
    justech_ecf_role_explanation = fields.Char(
        compute="_compute_justech_ecf_role",
        string="Este rol permite",
    )
    justech_finance_role = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("finance_user", "Usuario Finanzas"),
            ("finance_admin", "Administrador Finanzas"),
        ],
        string="Rol finanzas",
        compute="_compute_justech_finance_role",
        inverse="_inverse_justech_finance_role",
        store=False,
        groups="base.group_system,justech_admin_center.group_justech_admin_center_manager",
    )
    justech_finance_role_explanation = fields.Char(
        compute="_compute_justech_finance_role",
        string="Este rol permite",
    )
    justech_warranty_role = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("warranty_user", "Usuario Garantías"),
            ("warranty_manager", "Administrador Garantías"),
        ],
        string="Rol garantías",
        compute="_compute_justech_warranty_role",
        inverse="_inverse_justech_warranty_role",
        store=False,
        groups="base.group_system,justech_admin_center.group_justech_admin_center_manager",
    )
    justech_warranty_role_explanation = fields.Char(
        compute="_compute_justech_warranty_role",
        string="Este rol permite",
    )
    justech_cap_admin_console = fields.Boolean(
        string="Administrar consola Justech",
        compute="_compute_justech_caps",
        inverse="_inverse_cap_admin_console",
        groups="base.group_system,justech_admin_center.group_justech_admin_center_manager",
    )
    justech_cap_install_modules = fields.Boolean(
        string="Instalar módulos Justech",
        compute="_compute_justech_caps",
        inverse="_inverse_cap_install",
        groups="base.group_system,justech_admin_center.group_justech_admin_center_manager",
    )

    def _compute_justech_test_flags(self):
        for user in self:
            blob = "%s %s" % (user.login or "", user.name or "")
            is_test = bool(UAT_PATTERN.search(blob))
            user.justech_is_test_user = is_test
            if not is_test:
                user.justech_test_classification = "real"
                user.justech_test_role_label = False
                continue
            login = (user.login or "").lower()
            role = "Prueba controlada"
            for key, label in ROLE_HINTS.items():
                if key in login:
                    role = label
                    break
            user.justech_test_role_label = role
            if not user.active:
                user.justech_test_classification = "obsolete"
            elif "shot" in login or "ux" in login:
                user.justech_test_classification = "evidence"
            else:
                user.justech_test_classification = "required_temp"

    def _search_justech_is_test_user(self, operator, value):
        """Dominio estable por login/nombre — evita inconsistencias del compute en search."""
        test_domain = [
            "|",
            "|",
            "|",
            ("login", "ilike", "uat"),
            ("login", "ilike", "shot_"),
            ("name", "ilike", "UAT"),
            ("name", "ilike", "UX Shot"),
        ]
        # Odoo puede usar '=', '!=', 'in', 'not in' sobre booleanos
        truthy = {True, 1, "1", "true", "True"}
        if operator in ("=", "=="):
            want_test = value in truthy
        elif operator in ("!=", "<>"):
            want_test = value not in truthy
        elif operator == "in":
            want_test = bool(set(value or []) & truthy)
        elif operator == "not in":
            want_test = not bool(set(value or []) & truthy)
        else:
            want_test = bool(value)
        if want_test:
            return test_domain
        return ["!"] + test_domain

    def _role_from_groups(self, order):
        """order: list of (code, xmlid, explain) highest privilege first."""
        for code, xmlid, text in order:
            try:
                group = self.env.ref(xmlid)
            except ValueError:
                continue
            if group in self.all_group_ids:
                return code, text
        return "none", "Sin acceso."

    @api.depends_context("uid")
    def _compute_justech_admin_center_role(self):
        for user in self:
            role, explain = user._role_from_groups(
                [
                    (
                        "justech_admin",
                        "justech_admin_center.group_justech_admin_center_manager",
                        "Administrar la consola Justech, productos, empresas autorizadas y diagnósticos.",
                    ),
                ]
            )
            if role == "none":
                explain = "Sin acceso a Administración Justech."
            user.justech_admin_center_role = role
            user.justech_role_explanation = explain

    @api.depends_context("uid")
    def _compute_justech_fiscal_role_explanation(self):
        explanations = {
            "admin": "Administrar Centro Fiscal, NCF, e-CF, padrón, reportes y retenciones.",
            "officer": "Revisar, aprobar y diagnosticar sin cambiar secretos críticos.",
            "user": "Operar y consultar funciones fiscales cotidianas.",
            "none": "Sin acceso fiscal Justech.",
        }
        for user in self:
            role = "none"
            if "justech_fiscal_role" in user._fields:
                role = user.justech_fiscal_role or "none"
            else:
                if user.has_group("justech_fiscal_admin.group_justech_fiscal_admin_manager"):
                    role = "admin"
                elif user.has_group("justech_l10n_do_base.group_justech_do_fiscal_manager"):
                    role = "officer"
                elif user.has_group("justech_l10n_do_base.group_justech_do_fiscal_user"):
                    role = "user"
            user.justech_fiscal_role_explanation = explanations.get(role, explanations["none"])

    @api.depends_context("uid")
    def _compute_justech_ecf_role(self):
        for user in self:
            role, explain = user._role_from_groups(
                [
                    (
                        "ecf_admin",
                        "justech_ecf_core.group_ecf_admin",
                        "Configurar empresas e-CF, certificados, ambientes, asistentes y colas.",
                    ),
                    (
                        "ecf_responsible",
                        "justech_ecf_core.group_ecf_responsible",
                        "Operar y supervisar e-CF; validar sin cambiar secretos críticos.",
                    ),
                    (
                        "ecf_operator",
                        "justech_ecf_core.group_ecf_operator",
                        "Emitir y gestionar documentos e-CF.",
                    ),
                    (
                        "ecf_readonly",
                        "justech_ecf_core.group_ecf_readonly",
                        "Consultar e-CF sin modificar.",
                    ),
                ]
            )
            if role == "none":
                explain = "Sin acceso e-CF."
            user.justech_ecf_role = role
            user.justech_ecf_role_explanation = explain

    @api.depends_context("uid")
    def _compute_justech_finance_role(self):
        for user in self:
            # Finanzas: marcar vía account groups si no hay grupo Justech dedicado.
            role = "none"
            explain = "Sin acceso finanzas Justech (próximo módulo)."
            if user.has_group("account.group_account_manager"):
                role = "finance_admin"
                explain = "Administrar cobros, pagos, tesorería y conciliación."
            elif user.has_group("account.group_account_invoice") or user.has_group(
                "account.group_account_user"
            ):
                role = "finance_user"
                explain = "Operar cobros, pagos y tesorería según permisos contables."
            user.justech_finance_role = role
            user.justech_finance_role_explanation = explain

    @api.depends_context("uid")
    def _compute_justech_warranty_role(self):
        for user in self:
            role, explain = user._role_from_groups(
                [
                    (
                        "warranty_manager",
                        "justech_warranty.group_warranty_manager",
                        "Administrar garantías, roles y parámetros.",
                    ),
                    (
                        "warranty_user",
                        "justech_warranty.group_warranty_user",
                        "Registrar y dar seguimiento a garantías.",
                    ),
                ]
            )
            if role == "none":
                explain = "Sin acceso a Garantías."
            user.justech_warranty_role = role
            user.justech_warranty_role_explanation = explain

    def _write_exclusive_groups(self, xml_map, selected_code):
        group_ids = []
        for xid in xml_map.values():
            try:
                group_ids.append(self.env.ref(xid).id)
            except ValueError:
                pass
        for user in self:
            cmds = [(3, gid) for gid in group_ids]
            xid = xml_map.get(selected_code)
            if xid:
                try:
                    cmds.append((4, self.env.ref(xid).id))
                except ValueError:
                    pass
            if cmds:
                user.sudo().write({"group_ids": cmds})

    def _inverse_justech_ecf_role(self):
        xml_map = {
            "ecf_admin": "justech_ecf_core.group_ecf_admin",
            "ecf_responsible": "justech_ecf_core.group_ecf_responsible",
            "ecf_operator": "justech_ecf_core.group_ecf_operator",
            "ecf_readonly": "justech_ecf_core.group_ecf_readonly",
        }
        for user in self:
            user._write_exclusive_groups(xml_map, user.justech_ecf_role)

    def _inverse_justech_warranty_role(self):
        xml_map = {
            "warranty_manager": "justech_warranty.group_warranty_manager",
            "warranty_user": "justech_warranty.group_warranty_user",
        }
        for user in self:
            user._write_exclusive_groups(xml_map, user.justech_warranty_role)

    def _inverse_justech_finance_role(self):
        # Sin grupo Justech dedicado aún: no mutar account.* automáticamente.
        return

    def _inverse_justech_admin_center_role(self):
        xml_map = {
            "justech_admin": "justech_admin_center.group_justech_admin_center_manager",
        }
        for user in self:
            user._write_exclusive_groups(xml_map, user.justech_admin_center_role)

    def _compute_justech_caps(self):
        try:
            mgr = self.env.ref("justech_admin_center.group_justech_admin_center_manager")
        except ValueError:
            mgr = self.env["res.groups"]
        for user in self:
            user.justech_cap_admin_console = bool(mgr and mgr in user.all_group_ids) or user.has_group(
                "base.group_system"
            )
            user.justech_cap_install_modules = user.has_group("base.group_system") or user.justech_cap_admin_console

    def _inverse_cap_admin_console(self):
        try:
            mgr = self.env.ref("justech_admin_center.group_justech_admin_center_manager")
        except ValueError:
            return
        for user in self:
            if user.justech_cap_admin_console:
                user.sudo().write({"group_ids": [(4, mgr.id)]})
            elif mgr in user.group_ids:
                others = self.env["res.users"].sudo().search(
                    [("group_ids", "in", mgr.id), ("id", "!=", user.id)]
                )
                if others or user.has_group("base.group_system"):
                    user.sudo().write({"group_ids": [(3, mgr.id)]})

    def _inverse_cap_install(self):
        self._inverse_cap_admin_console()
