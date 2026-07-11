# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
"""Política centralizada de correo saliente — solo empresa Hellenia."""
from odoo import api, models
from odoo.tools.mail import email_normalize, formataddr


HELLENIA_MAIL_FROM_NAME = "Hellenia, S.R.L."
HELLENIA_MAIL_FROM_EMAIL = "info@helleniadr.com"


class HelleniaMailPolicyMixin(models.AbstractModel):
    _name = "hellenia.mail.policy.mixin"
    _description = "Helpers política de correo Hellenia"

    @api.model
    def _hellenia_mail_policy_applies(self, company=None):
        """True solo para Hellenia (no Justgroup ni otras empresas)."""
        company = company or self.env.company
        if not company:
            return False
        email = (company.email or "").lower().strip()
        name = (company.name or "").lower()
        return email.endswith("@helleniadr.com") or "hellenia" in name

    @api.model
    def _hellenia_mail_from(self):
        return formataddr((HELLENIA_MAIL_FROM_NAME, HELLENIA_MAIL_FROM_EMAIL))

    @api.model
    def _hellenia_partner_email(self, partner):
        if not partner or not partner.exists():
            return ""
        return email_normalize(partner.email or "") or (partner.email or "").strip()

    @api.model
    def _hellenia_is_technical_user(self, user):
        """Solo usuarios técnicos (OdooBot/public). NO usar _is_system():

        `_is_system()` es True para administradores humanos (Settings) y
        no deben excluirse del Reply-To.
        """
        if not user or not user.exists():
            return True
        if user._is_public():
            return True
        try:
            root = self.env.ref("base.user_root")
            if user.id == root.id:
                return True
        except Exception:
            pass
        login = (user.login or "").lower()
        return login in {"__system__", "odoobot", "public"}

    @api.model
    def _hellenia_is_technical_partner(self, partner):
        if not partner or not partner.exists():
            return True
        email = (self._hellenia_partner_email(partner) or "").lower()
        name = (partner.name or "").strip().lower()
        if not email:
            return True
        if email in {"odoobot@example.com", "public@example.com"}:
            return True
        if "odoobot" in name:
            return True
        return False

    @api.model
    def _hellenia_format_reply(self, partner):
        email = self._hellenia_partner_email(partner)
        if not email or self._hellenia_is_technical_partner(partner):
            return False
        name = (partner.name or "").strip() or HELLENIA_MAIL_FROM_NAME
        # Nunca permitir que el display name sea OdooBot
        if "odoobot" in name.lower():
            return False
        return formataddr((name, email))

    @api.model
    def _hellenia_reply_to_from_user(self, user=None, author_partner=None):
        """Reply-To = quien envió; nunca OdooBot; fallback info@helleniadr.com."""
        # 1) Usuario originador (incluye admins humanos)
        if user and not self._hellenia_is_technical_user(user) and user.partner_id:
            reply = self._hellenia_format_reply(user.partner_id)
            if reply:
                return reply
        # 2) Autor del mensaje
        if author_partner and author_partner.exists():
            reply = self._hellenia_format_reply(author_partner)
            if reply:
                return reply
        # 3) Fallback institucional (NUNCA OdooBot)
        return formataddr((HELLENIA_MAIL_FROM_NAME, HELLENIA_MAIL_FROM_EMAIL))

    @api.model
    def _hellenia_sanitize_reply_to(self, reply_to):
        """Si el Reply-To quedó en OdooBot/vacío, forzar fallback corporativo."""
        value = (reply_to or "").strip().lower()
        if not value or "odoobot" in value or "odoobot@example.com" in value:
            return formataddr((HELLENIA_MAIL_FROM_NAME, HELLENIA_MAIL_FROM_EMAIL))
        return reply_to

    @api.model
    def _hellenia_resolve_company_from_mail_vals(self, vals):
        """Intenta company del documento relacionado; si no, env.company."""
        company = self.env.company
        model = vals.get("model")
        res_id = vals.get("res_id")
        if model and res_id and model in self.env:
            try:
                record = self.env[model].browse(int(res_id)).exists()
                if record and "company_id" in record._fields and record.company_id:
                    return record.company_id
            except Exception:
                pass
        return company

    @api.model
    def _hellenia_apply_mail_policy_vals(self, vals):
        """Mutates vals in place for Hellenia From / Reply-To."""
        if not isinstance(vals, dict):
            return vals
        current_from = (vals.get("email_from") or "").lower()
        if "mailer-daemon" in current_from:
            return vals

        company = self._hellenia_resolve_company_from_mail_vals(vals)
        if not self._hellenia_mail_policy_applies(company):
            return vals

        vals["email_from"] = self._hellenia_mail_from()

        author = False
        if vals.get("author_id"):
            author = self.env["res.partner"].browse(vals["author_id"]).exists()
        user = self.env.user
        if self._hellenia_is_technical_user(user):
            user = False
        vals["reply_to"] = self._hellenia_sanitize_reply_to(
            self._hellenia_reply_to_from_user(user=user, author_partner=author or False)
        )
        return vals
