# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import api, models


class MailMail(models.Model):
    _name = "mail.mail"
    _inherit = ["mail.mail", "hellenia.mail.policy.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._hellenia_apply_mail_policy_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        """Impide que un write posterior deje Reply-To en OdooBot."""
        res = super().write(vals)
        if self.env.context.get("hellenia_skip_mail_policy"):
            return res
        if "reply_to" in vals or "email_from" in vals:
            for mail in self:
                company = self._hellenia_resolve_company_from_mail_vals(
                    {"model": mail.model, "res_id": mail.res_id}
                )
                if not self._hellenia_mail_policy_applies(company):
                    continue
                updates = {}
                expected_from = self._hellenia_mail_from()
                if mail.email_from != expected_from:
                    updates["email_from"] = expected_from
                safe_reply = self._hellenia_sanitize_reply_to(mail.reply_to)
                if (mail.reply_to or "") != safe_reply or "odoobot" in (
                    mail.reply_to or ""
                ).lower():
                    # Recalcular desde originador
                    safe_reply = self._hellenia_reply_to_from_user(
                        user=self._hellenia_origin_user(mail),
                        author_partner=mail.author_id,
                    )
                    safe_reply = self._hellenia_sanitize_reply_to(safe_reply)
                    updates["reply_to"] = safe_reply
                if updates:
                    super(MailMail, mail.with_context(hellenia_skip_mail_policy=True)).write(
                        updates
                    )
        return res

    def _hellenia_origin_user(self, mail):
        """Usuario que originó el correo (create_uid), nunca OdooBot/public."""
        for user in (mail.create_uid, self.env.user):
            if user and not self._hellenia_is_technical_user(user):
                return user
        return self.env["res.users"]

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None, **kwargs):
        """Red de seguridad: From corporativo + Reply-To del usuario (nunca OdooBot)."""
        if not self.env.context.get("hellenia_skip_mail_policy"):
            for mail in self:
                company = self._hellenia_resolve_company_from_mail_vals(
                    {"model": mail.model, "res_id": mail.res_id}
                )
                if not self._hellenia_mail_policy_applies(company):
                    continue
                expected_from = self._hellenia_mail_from()
                expected_reply = self._hellenia_sanitize_reply_to(
                    self._hellenia_reply_to_from_user(
                        user=self._hellenia_origin_user(mail),
                        author_partner=mail.author_id,
                    )
                )
                updates = {}
                if mail.email_from != expected_from:
                    updates["email_from"] = expected_from
                if (mail.reply_to or "") != expected_reply:
                    updates["reply_to"] = expected_reply
                if updates:
                    mail.with_context(hellenia_skip_mail_policy=True).write(updates)
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
            **kwargs,
        )
