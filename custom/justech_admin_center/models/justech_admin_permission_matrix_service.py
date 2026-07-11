from odoo import api, models, _


ROLE_CATALOG = [
    # code, label, group xmlids (first match wins for mapping)
    ("justech_admin", "Administrador Justech", ["justech_admin_center.group_justech_admin_center_manager"]),
    ("fiscal_admin", "Administrador Fiscal", ["justech_fiscal_admin.group_justech_fiscal_admin_manager"]),
    ("fiscal_manager", "Responsable Fiscal", ["justech_l10n_do_base.group_justech_do_fiscal_manager"]),
    ("fiscal_user", "Usuario Fiscal", ["justech_l10n_do_base.group_justech_do_fiscal_user"]),
    ("treasury_manager", "Administrador de Tesorería", []),
    ("treasury_user", "Usuario de Tesorería", []),
    ("warranty_manager", "Administrador de Garantías", ["justech_warranty.group_warranty_manager"]),
    ("warranty_user", "Usuario de Garantías", ["justech_warranty.group_warranty_user"]),
    ("auditor", "Auditor", ["justech_global_audit_log.group_justech_audit_manager", "justech_global_audit_log.group_audit_user"]),
    ("readonly", "Solo lectura", []),
]


class JustechAdminPermissionMatrixService(models.AbstractModel):
    _name = "justech.admin.permission.matrix.service"
    _description = "Matriz de permisos funcionales Justech"

    @api.model
    def role_catalog(self):
        rows = []
        for code, label, xmlids in ROLE_CATALOG:
            group = self._resolve_group(xmlids)
            rows.append({"code": code, "label": label, "group": group, "available": bool(group)})
        return rows

    @api.model
    def _resolve_group(self, xmlids):
        for xid in xmlids:
            try:
                return self.env.ref(xid)
            except ValueError:
                continue
        return self.env["res.groups"]

    @api.model
    def render_html(self):
        modules = self.env["justech.admin.module"].sudo().search([])
        roles = self.role_catalog()
        parts = [
            '<div class="o_jac_matrix"><table class="table table-sm">',
            "<thead><tr><th>%s</th><th>%s</th><th>Leer</th><th>Operar</th><th>Aprobar</th><th>Administrar</th></tr></thead><tbody>"
            % (_("Función / Módulo"), _("Rol")),
        ]
        for mod in modules:
            for role in roles:
                if not role["available"] and role["code"] not in ("readonly", "justech_admin"):
                    continue
                read = "✓"
                operate = "✓" if role["code"] not in ("readonly",) else "—"
                approve = "✓" if role["code"] in ("fiscal_manager", "fiscal_admin", "justech_admin", "warranty_manager", "treasury_manager") else "—"
                admin = "✓" if role["code"] in ("justech_admin", "fiscal_admin", "warranty_manager", "treasury_manager") else "—"
                parts.append(
                    "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                    % (mod.functional_name, role["label"], read, operate, approve, admin)
                )
        parts.append("</tbody></table></div>")
        return "".join(parts)

    @api.model
    def apply_role(self, user, role_code, preview_only=False):
        """Map functional role to groups — additive, never silent."""
        catalog = {r["code"]: r for r in self.role_catalog()}
        role = catalog.get(role_code)
        if not role:
            return {"ok": False, "message": _("Rol desconocido")}
        before = user.group_ids.mapped("display_name")
        group = role["group"]
        after_groups = user.group_ids
        if group:
            after_groups = after_groups | group
        if preview_only:
            return {
                "ok": True,
                "before": ", ".join(before),
                "after": ", ".join((after_groups).mapped("display_name")),
                "group": group,
            }
        if group and group not in user.group_ids:
            user.sudo().write({"group_ids": [(4, group.id)]})
        return {"ok": True, "group": group}
