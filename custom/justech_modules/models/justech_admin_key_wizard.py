from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JustechAdminKeyWizard(models.TransientModel):
    _name = "justech.admin.key.wizard"
    _description = "Justech Administrative Key Prompt"

    admin_key = fields.Char(string="Justech Administrative Key", required=True)
    scope = fields.Char(default="platform")
    target_action_xmlid = fields.Char(required=True)

    def action_verify(self):
        self.ensure_one()
        service = self.env["justech.admin.access.service"]
        if not service.user_has_key():
            return service._action_setup_key_required(
                self.target_action_xmlid, self.scope
            )
        if not self.admin_key:
            raise UserError(_("Enter the Justech Administrative Key."))
        service.open_session(self.admin_key, scope=self.scope)
        return service._resolve_action(self.target_action_xmlid)
