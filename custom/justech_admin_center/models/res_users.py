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
            ("none", "Sin rol consola"),
            ("justech_admin", "Administrador Justech"),
            ("fiscal_admin", "Administrador Fiscal"),
            ("fiscal_manager", "Responsable Fiscal"),
            ("fiscal_user", "Usuario Fiscal"),
            ("finance_admin", "Administrador Finanzas"),
            ("finance_user", "Usuario Finanzas"),
            ("warranty_manager", "Administrador Garantías"),
            ("warranty_user", "Usuario Garantías"),
            ("auditor", "Auditor"),
            ("readonly", "Solo lectura"),
        ],
        string="Rol Justech (consola)",
        compute="_compute_justech_admin_center_role",
        inverse="_inverse_justech_admin_center_role",
        store=False,
    )
    justech_role_explanation = fields.Char(
        compute="_compute_justech_admin_center_role",
        string="Este rol permite",
    )
    justech_cap_admin_console = fields.Boolean(
        string="Administrar consola Justech",
        compute="_compute_justech_caps",
        inverse="_inverse_cap_admin_console",
    )
    justech_cap_install_modules = fields.Boolean(
        string="Instalar módulos Justech",
        compute="_compute_justech_caps",
        inverse="_inverse_cap_install",
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

    @api.depends_context("uid")
    def _compute_justech_admin_center_role(self):
        Matrix = self.env["justech.admin.permission.matrix.service"]
        explanations = {
            "justech_admin": "Administrar la consola Justech, productos, empresas y seguridad.",
            "fiscal_admin": "Administrar configuración fiscal, alertas y permisos fiscales.",
            "fiscal_manager": "Supervisar operación fiscal y revalidaciones.",
            "fiscal_user": "Operar funciones fiscales cotidianas sin cambiar configuración crítica.",
            "finance_admin": "Administrar cobros, pagos, tesorería y retenciones operativas.",
            "finance_user": "Operar cobros, pagos y tesorería según permisos asignados.",
            "warranty_manager": "Administrar garantías, roles y parámetros del producto.",
            "warranty_user": "Registrar y dar seguimiento a garantías.",
            "auditor": "Consultar auditoría y trazabilidad sin operar.",
            "readonly": "Solo lectura de información Justech.",
            "none": "Sin rol funcional Justech asignado en la consola.",
        }
        for user in self:
            role = "none"
            for item in Matrix.role_catalog():
                group = item["group"]
                if group and group in user.all_group_ids:
                    role = item["code"]
                    break
            user.justech_admin_center_role = role
            user.justech_role_explanation = explanations.get(role, explanations["none"])

    def _inverse_justech_admin_center_role(self):
        for user in self:
            if user.justech_admin_center_role and user.justech_admin_center_role != "none":
                self.env["justech.admin.permission.matrix.service"].apply_role(
                    user, user.justech_admin_center_role, preview_only=False
                )

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
