from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelleniaPermissionsInternalWizard(models.TransientModel):
    _name = "hellenia.permissions.internal.wizard"
    _description = "Autorización Clave Administrativa — permisos internos"

    user_id = fields.Many2one("res.users", required=True, readonly=True)
    permission_code = fields.Selection(
        selection=lambda self: self._permission_selection(),
        required=True,
        readonly=True,
    )
    target_level = fields.Selection(
        selection=lambda self: self._level_selection(),
        required=True,
        readonly=True,
    )
    admin_key = fields.Char(string="Clave Administrativa Justech", required=True)
    prompt_message = fields.Text(
        string="Mensaje",
        readonly=True,
        default=lambda self: _(
            "Este permiso es exclusivo de Justech. "
            "Introduzca la Clave Administrativa para autorizar la activación."
        ),
    )

    @api.model
    def _permission_selection(self):
        return [
            ("justech_admin", "Justech Admin"),
            ("justech_platform", "Justech Platform"),
        ]

    @api.model
    def _level_selection(self):
        return self.env["res.users"]._permissions_ux_level_selection()

    def action_confirm(self):
        self.ensure_one()
        if not self.admin_key:
            raise UserError(_("Introduzca la Clave Administrativa Justech."))
        svc = self.env["justech.admin.access.service"]
        svc.open_session(self.admin_key, scope=svc.SCOPE_ADMIN)
        self.user_id.with_context(
            hellenia_permissions_ux_grant=True,
        )._apply_permissions_ux_level(self.permission_code, self.target_level)
        return {"type": "ir.actions.act_window_close"}
