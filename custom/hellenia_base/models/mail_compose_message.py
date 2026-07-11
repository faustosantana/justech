# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class MailComposeMessage(models.TransientModel):
    _name = "mail.compose.message"
    _inherit = ["mail.compose.message", "hellenia.mail.policy.mixin"]

    def _prepare_mail_values_dynamic(self, res_ids):
        """Normaliza From/Reply-To en valores dinámicos del composer."""
        mail_values = super()._prepare_mail_values_dynamic(res_ids)
        if not self._hellenia_mail_policy_applies(self.env.company):
            return mail_values
        for _res_id, values in mail_values.items():
            if isinstance(values, dict):
                self._hellenia_apply_mail_policy_vals(values)
        return mail_values

    def _prepare_mail_values_static(self):
        mail_values = super()._prepare_mail_values_static()
        if self._hellenia_mail_policy_applies(self.env.company) and isinstance(
            mail_values, dict
        ):
            self._hellenia_apply_mail_policy_vals(mail_values)
        return mail_values
