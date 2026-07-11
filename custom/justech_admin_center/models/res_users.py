from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    justech_admin_center_role = fields.Selection(
        selection=[
            ("none", "Sin rol consola"),
            ("justech_admin", "Administrador Justech"),
            ("fiscal_admin", "Administrador Fiscal"),
            ("fiscal_manager", "Responsable Fiscal"),
            ("fiscal_user", "Usuario Fiscal"),
            ("treasury_manager", "Administrador de Tesorería"),
            ("treasury_user", "Usuario de Tesorería"),
            ("warranty_manager", "Administrador de Garantías"),
            ("warranty_user", "Usuario de Garantías"),
            ("auditor", "Auditor"),
            ("readonly", "Solo lectura"),
        ],
        string="Rol Justech (consola)",
        compute="_compute_justech_admin_center_role",
        inverse="_inverse_justech_admin_center_role",
        store=False,
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

    @api.depends_context("uid")
    def _compute_justech_admin_center_role(self):
        Matrix = self.env["justech.admin.permission.matrix.service"]
        for user in self:
            role = "none"
            for item in Matrix.role_catalog():
                group = item["group"]
                if group and group in user.all_group_ids:
                    role = item["code"]
                    break
            user.justech_admin_center_role = role

    def _inverse_justech_admin_center_role(self):
        # Apply via wizard preview in UI; direct inverse only for managers
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
            user.justech_cap_admin_console = bool(mgr and mgr in user.all_group_ids) or user.has_group("base.group_system")
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
                # protect last manager
                others = self.env["res.users"].sudo().search(
                    [("group_ids", "in", mgr.id), ("id", "!=", user.id)]
                )
                if others or user.has_group("base.group_system"):
                    user.sudo().write({"group_ids": [(3, mgr.id)]})

    def _inverse_cap_install(self):
        # Install capability tracks manager + system; no separate group in v1
        self._inverse_cap_admin_console()
