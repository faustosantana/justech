from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .hellenia_permissions_ux_registry import (
    PERMISSIONS_UX_CATEGORIES,
    PERMISSIONS_UX_ITEMS,
    PROTECTED_PERMISSION_CODES,
)


class ResUsersPermissionsUx(models.Model):
    _inherit = "res.users"

    perm_ux_accounting = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
        ],
        string="Contabilidad",
        compute="_compute_permissions_ux_fields",
        inverse="_inverse_permissions_ux_fields",
        readonly=False,
    )
    perm_ux_bank = fields.Selection(
        selection=[("none", "Ninguno"), ("on", "Activo")],
        string="Banco",
        compute="_compute_permissions_ux_fields",
        inverse="_inverse_permissions_ux_fields",
        readonly=False,
    )
    perm_ux_multicurrency = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
        ],
        string="Multimoneda",
        compute="_compute_permissions_ux_fields",
        inverse="_inverse_permissions_ux_fields",
        readonly=False,
    )
    perm_ux_purchase = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
        ],
        string="Compras",
        compute="_compute_permissions_ux_fields",
        inverse="_inverse_permissions_ux_fields",
        readonly=False,
    )
    perm_ux_inventory = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
        ],
        string="Inventario",
        compute="_compute_permissions_ux_fields",
        inverse="_inverse_permissions_ux_fields",
        readonly=False,
    )
    perm_ux_dashboard = fields.Selection(
        selection=[("none", "Ninguno"), ("on", "Activo")],
        string="Tablero",
        compute="_compute_permissions_ux_fields",
        inverse="_inverse_permissions_ux_fields",
        readonly=False,
    )
    perm_ux_audit = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
        ],
        string="Auditoría",
        compute="_compute_permissions_ux_fields",
        inverse="_inverse_permissions_ux_fields",
        readonly=False,
    )
    perm_ux_governance = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
        ],
        string="Hellenia Governance",
        compute="_compute_permissions_ux_fields",
        inverse="_inverse_permissions_ux_fields",
        readonly=False,
    )
    perm_ux_justech_admin = fields.Selection(
        selection=[("none", "Ninguno"), ("on", "Activo")],
        string="Justech Admin",
        compute="_compute_permissions_ux_fields",
        readonly=True,
    )
    perm_ux_justech_platform = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
            ("internal", "Administrador interno"),
        ],
        string="Justech Platform",
        compute="_compute_permissions_ux_fields",
        readonly=True,
    )
    perm_ux_justech_admin_active = fields.Boolean(
        compute="_compute_permissions_ux_internal_flags",
    )
    perm_ux_justech_platform_active = fields.Boolean(
        compute="_compute_permissions_ux_internal_flags",
    )

    # ------------------------------------------------------------------ registry
    @api.model
    def _permissions_ux_registry(self):
        return PERMISSIONS_UX_ITEMS

    @api.model
    def _permissions_ux_categories(self):
        return PERMISSIONS_UX_CATEGORIES

    @api.model
    def _permissions_ux_level_selection(self):
        return [
            ("none", "Ninguno"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
            ("on", "Activo"),
            ("internal", "Administrador interno"),
        ]

    @api.model
    def _permissions_ux_item(self, code):
        for item in self._permissions_ux_registry():
            if item["code"] == code:
                return item
        return None

    @api.model
    def _permissions_ux_field_name(self, code):
        return f"perm_ux_{code}"

    def _permissions_ux_group_ids_for_privilege(self, privilege):
        if not privilege:
            return self.env["res.groups"]
        return self.env["res.groups"].search([("privilege_id", "=", privilege.id)])

    def _permissions_ux_resolve_groups(self, item, level_key):
        if not item or level_key == "none":
            return self.env["res.groups"]
        for key, _label, xmlids in item["levels"]:
            if key == level_key:
                groups = self.env["res.groups"]
                for xmlid in xmlids:
                    group = self.env.ref(xmlid, raise_if_not_found=False)
                    if group:
                        groups |= group
                return groups
        return self.env["res.groups"]

    def _permissions_ux_detect_level(self, user, item):
        if not item:
            return "none"
        privilege = self.env.ref(
            item["privilege_xmlid"], raise_if_not_found=False
        )
        if not privilege:
            return "none"
        privilege_groups = self._permissions_ux_group_ids_for_privilege(privilege)
        if not (user.group_ids & privilege_groups):
            return "none"
        best = "none"
        rank = {"none": 0, "user": 1, "on": 1, "manager": 2, "internal": 3}
        for level_key, _label, _xmlids in item["levels"]:
            if level_key == "none":
                continue
            target = self._permissions_ux_resolve_groups(item, level_key)
            if target and (user.group_ids & target):
                if rank.get(level_key, 0) >= rank.get(best, 0):
                    best = level_key
        return best

    @api.depends("group_ids")
    def _compute_permissions_ux_fields(self):
        for user in self:
            for item in self._permissions_ux_registry():
                field_name = self._permissions_ux_field_name(item["code"])
                user[field_name] = user._permissions_ux_detect_level(user, item)

    @api.depends("perm_ux_justech_admin", "perm_ux_justech_platform")
    def _compute_permissions_ux_internal_flags(self):
        for user in self:
            user.perm_ux_justech_admin_active = user.perm_ux_justech_admin != "none"
            user.perm_ux_justech_platform_active = user.perm_ux_justech_platform != "none"

    def _inverse_permissions_ux_fields(self):
        for user in self:
            for item in self._permissions_ux_registry():
                if item.get("protected"):
                    continue
                field_name = self._permissions_ux_field_name(item["code"])
                new_level = user[field_name]
                old_level = user._permissions_ux_detect_level(user, item)
                if new_level != old_level:
                    user._apply_permissions_ux_level(item["code"], new_level)

    def _apply_permissions_ux_level(self, code, level_key):
        self.ensure_one()
        item = self._permissions_ux_item(code)
        if not item:
            raise UserError(_("Permiso no disponible."))
        privilege = self.env.ref(
            item["privilege_xmlid"], raise_if_not_found=False
        )
        if not privilege:
            raise UserError(_("Permiso no instalado en esta instancia."))
        privilege_groups = self._permissions_ux_group_ids_for_privilege(privilege)
        target_groups = self._permissions_ux_resolve_groups(item, level_key)
        commands = [(3, gid) for gid in privilege_groups.ids]
        commands += [(4, gid) for gid in target_groups.ids]
        self.with_context(hellenia_permissions_ux_grant=True).write(
            {"group_ids": commands}
        )

    def _permissions_ux_admin_session_ok(self):
        svc = self.env["justech.admin.access.service"]
        return svc.is_session_valid(scope=svc.SCOPE_ADMIN)

    def _permissions_ux_wizard_action(self, code, level_key):
        self.ensure_one()
        item = self._permissions_ux_item(code)
        return {
            "type": "ir.actions.act_window",
            "name": _("Clave Administrativa Justech"),
            "res_model": "hellenia.permissions.internal.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_user_id": self.id,
                "default_permission_code": code,
                "default_target_level": level_key,
                "default_prompt_message": item["tooltip"] if item else "",
            },
        }

    def action_permissions_ux_activate_internal(self):
        self.ensure_one()
        code = self.env.context.get("permission_code")
        level_key = self.env.context.get("target_level", "on")
        item = self._permissions_ux_item(code)
        if not item or not item.get("protected"):
            raise UserError(_("Permiso interno no válido."))
        if self._permissions_ux_admin_session_ok():
            self._apply_permissions_ux_level(code, level_key)
            return {"type": "ir.actions.client", "tag": "reload"}
        return self._permissions_ux_wizard_action(code, level_key)

    def action_permissions_ux_deactivate_internal(self):
        self.ensure_one()
        code = self.env.context.get("permission_code")
        item = self._permissions_ux_item(code)
        if not item or not item.get("protected"):
            raise UserError(_("Permiso interno no válido."))
        self._apply_permissions_ux_level(code, "none")
        return {"type": "ir.actions.client", "tag": "reload"}

    @api.model
    def _permissions_ux_protected_group_ids(self):
        groups = self.env["res.groups"]
        for code in PROTECTED_PERMISSION_CODES:
            item = self._permissions_ux_item(code)
            if not item:
                continue
            privilege = self.env.ref(
                item["privilege_xmlid"], raise_if_not_found=False
            )
            if privilege:
                groups |= self._permissions_ux_group_ids_for_privilege(privilege)
        return groups

    @api.model
    def _permissions_ux_parse_group_commands(self, commands, current_group_ids):
        group_ids = set(current_group_ids.ids)
        for command in commands:
            if not command:
                continue
            op = command[0]
            if op == 6:
                group_ids = set(command[2])
            elif op == 4:
                group_ids.add(command[1])
            elif op == 3:
                group_ids.discard(command[1])
            elif op == 5:
                group_ids.clear()
        return group_ids

    def _permissions_ux_block_protected_group_writes(self, vals):
        if self.env.context.get("hellenia_permissions_ux_grant"):
            return
        protected = self._permissions_ux_protected_group_ids()
        if not protected:
            return
        protected_ids = set(protected.ids)
        for user in self:
            if "group_ids" not in vals:
                continue
            before = set(user.group_ids.ids)
            after = self._permissions_ux_parse_group_commands(
                vals["group_ids"], user.group_ids
            )
            added = after - before
            if added & protected_ids:
                raise AccessError(
                    _(
                        "Los permisos Justech Admin y Justech Platform solo pueden "
                        "activarse desde el Centro de Permisos con la Clave "
                        "Administrativa Justech."
                    )
                )

    def write(self, vals):
        self._permissions_ux_block_protected_group_writes(vals)
        return super().write(vals)

    def has_hellenia_permission(self, code, company=None):
        return self.env["hellenia.governance.service"].has_permission(
            code, user=self, company=company
        )

    def require_hellenia_permission(self, code, company=None):
        return self.env["hellenia.governance.service"].require_permission(
            code, user=self, company=company
        )
