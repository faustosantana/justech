from odoo import api, models, _


ROLE_CATALOG = [
    ("justech_admin", "Administrador Justech", ["justech_admin_center.group_justech_admin_center_manager"]),
    ("fiscal_admin", "Administrador Fiscal", ["justech_fiscal_admin.group_justech_fiscal_admin_manager"]),
    ("fiscal_manager", "Responsable Fiscal", ["justech_l10n_do_base.group_justech_do_fiscal_manager"]),
    ("fiscal_user", "Usuario Fiscal", ["justech_l10n_do_base.group_justech_do_fiscal_user"]),
    ("finance_admin", "Administrador Finanzas", []),
    ("finance_user", "Usuario Finanzas", []),
    ("warranty_manager", "Administrador Garantías", ["justech_warranty.group_warranty_manager"]),
    ("warranty_user", "Usuario Garantías", ["justech_warranty.group_warranty_user"]),
    ("auditor", "Auditor", ["justech_global_audit_log.group_justech_audit_manager", "justech_global_audit_log.group_audit_user"]),
    ("readonly", "Solo lectura", []),
]


ROLE_EXPLAIN = {
    "justech_admin": "Administrar la consola Justech, productos, empresas y seguridad.",
    "fiscal_admin": "Administrar configuración fiscal, alertas y permisos fiscales.",
    "fiscal_manager": "Supervisar operación fiscal y revalidaciones.",
    "fiscal_user": "Operar funciones fiscales cotidianas.",
    "finance_admin": "Administrar cobros, pagos, tesorería y retenciones operativas.",
    "finance_user": "Operar cobros, pagos y tesorería.",
    "warranty_manager": "Administrar garantías, roles y parámetros.",
    "warranty_user": "Registrar y dar seguimiento a garantías.",
    "auditor": "Consultar auditoría y trazabilidad.",
    "readonly": "Solo lectura de información Justech.",
}


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
        roles = self.role_catalog()
        parts = [
            '<div class="o_jac_matrix"><table class="table table-sm o_jac_table">',
            "<thead><tr><th>%s</th><th>%s</th><th>%s</th></tr></thead><tbody>"
            % (_("Rol"), _("Disponible"), _("Este rol permite")),
        ]
        for role in roles:
            parts.append(
                "<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                % (
                    role["label"],
                    _("Sí") if role["available"] or role["code"] in ("readonly", "finance_admin", "finance_user") else _("Pendiente de grupo"),
                    ROLE_EXPLAIN.get(role["code"], ""),
                )
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
