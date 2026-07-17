# -*- coding: utf-8 -*-
from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def get_mail_values(self, res_ids):
        """Inject company notification From from document company_id only."""
        result = super().get_mail_values(res_ids)
        if self.env.context.get("justech_mail_skip_outgoing_policy"):
            return result
        for res_id, values in (result or {}).items():
            if not self.model or self.model not in self.env:
                continue
            record = self.env[self.model].browse(res_id)
            if not record.exists() or "company_id" not in record._fields or not record.company_id:
                continue
            identity = record.company_id._get_company_mail_identity(
                reply_user=self.env.user if not self.env.user._is_public() else None
            )
            if identity.get("email_from"):
                values["email_from"] = identity["email_from"]
            if identity.get("reply_to") and not values.get("reply_to"):
                values["reply_to"] = identity["reply_to"]
        return result
