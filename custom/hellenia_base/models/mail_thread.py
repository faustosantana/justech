# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class MailThread(models.AbstractModel):
    _name = "mail.thread"
    _inherit = ["mail.thread", "hellenia.mail.policy.mixin"]

    def _notify_by_email_get_base_mail_values(
        self, message, recipients_data, additional_values=None
    ):
        """Asegura From corporativo en notificaciones por correo."""
        mail_values = super()._notify_by_email_get_base_mail_values(
            message, recipients_data, additional_values=additional_values
        )
        company = self.env.company
        if self and "company_id" in self._fields and self[0].company_id:
            company = self[0].company_id
        if not self._hellenia_mail_policy_applies(company):
            return mail_values
        mail_values["email_from"] = self._hellenia_mail_from()
        author = message.author_id if message else False
        user = self.env.user
        if self._hellenia_is_technical_user(user):
            user = False
        mail_values["reply_to"] = self._hellenia_sanitize_reply_to(
            self._hellenia_reply_to_from_user(
                user=user, author_partner=author or False
            )
        )
        return mail_values
