# -*- coding: utf-8 -*-
from email.utils import parseaddr

from odoo import models, tools


class MailMail(models.Model):
    _inherit = "mail.mail"

    def send(self, auto_commit=False, raise_exception=False, post_send_callback=None):
        if not self.env.context.get("justech_mail_skip_outgoing_policy"):
            self._justech_apply_outgoing_policy()
        return super().send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            post_send_callback=post_send_callback,
        )

    def _justech_apply_outgoing_policy(self):
        """Force system From + human Reply-To for configured domains.

        Microsoft 365 rejects Send-As when authenticating as
        notifications@ while the From header is a user mailbox.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("justech_mail.outgoing_policy_enabled", "True").lower() in ("0", "false", "no"):
            return

        force_from = (
            ICP.get_param(
                "justech_mail.force_from",
                "Notificaciones Justech <notifications@justech.do>",
            )
            or ""
        ).strip()
        if not force_from:
            return

        domains = {
            d.strip().lower()
            for d in (ICP.get_param("justech_mail.apply_domains", "justech.do") or "").split(",")
            if d.strip()
        }
        force_addr = (parseaddr(force_from)[1] or "").lower()

        for mail in self:
            if not mail.exists():
                continue
            msg = mail.mail_message_id
            original_from = (mail.email_from or (msg.email_from if msg else "") or "").strip()
            _, original_addr = parseaddr(original_from)
            original_addr = (original_addr or "").lower()

            if not self._justech_policy_applies(original_addr, force_addr, domains, mail):
                continue

            reply_name, reply_addr = mail._justech_resolve_reply_to(original_from, force_addr)
            if not reply_addr:
                reply_addr = force_addr
            reply_to = tools.formataddr((reply_name or "", reply_addr)) if reply_addr else force_from

            # mail.mail inherits mail.message → email_from / reply_to live on the message
            write_vals = {
                "email_from": force_from,
                "reply_to": reply_to,
            }
            if msg and "reply_to_force_new" in msg._fields:
                write_vals["reply_to_force_new"] = True
            mail.write(write_vals)

    def _justech_policy_applies(self, original_addr, force_addr, domains, mail):
        """Apply when From is already our domain / force mailbox / OdooBot / empty."""
        self.ensure_one()
        if not domains:
            return False
        if not original_addr:
            return True
        if original_addr == force_addr:
            return True
        if original_addr.endswith("@example.com"):
            return True
        if "@" not in original_addr:
            return True
        domain = original_addr.rsplit("@", 1)[-1]
        if domain in domains:
            return True
        # Notifications generated with alias aliases (info@, asistencia@) on same domain already covered.
        # External From (client helpdesk inbound notifications): still rewrite so SMTP auth succeeds,
        # Reply-To will prefer the Justech user who triggered the send.
        if mail.create_uid and mail.create_uid.partner_id and mail.create_uid.partner_id.email:
            uid_domain = mail.create_uid.partner_id.email.rsplit("@", 1)[-1].lower()
            if uid_domain in domains:
                return True
        return False

    def _justech_resolve_reply_to(self, original_from, force_addr):
        """Reply-To = human who generated the action (never OdooBot/catchall)."""
        self.ensure_one()
        bad = {
            "",
            force_addr,
            "odoobot@example.com",
            "catchall@justech.do",
            "admin@example.com",
        }
        shared_aliases = {
            "asistencia@justech.do",
            "info@justech.do",
            "noreply@justech.do",
            "notifications@justech.do",
        }

        name, addr = parseaddr(original_from or "")
        name = (name or "").strip()
        addr = (addr or "").strip().lower()

        def _ok(candidate):
            c = (candidate or "").strip().lower()
            return bool(c) and c not in bad and not c.endswith("@example.com")

        # Prefer personal mailbox from original From when not a shared alias
        if _ok(addr) and addr not in shared_aliases:
            return name, addr

        # Prefer the Odoo user that created/triggered the mail
        user = self.create_uid
        if user and user.partner_id and _ok(user.partner_id.email):
            return (user.partner_id.name or "").strip(), user.partner_id.email.strip().lower()

        # Message author partner
        author = self.author_id or (self.mail_message_id.author_id if self.mail_message_id else False)
        if author and _ok(author.email):
            return (author.name or "").strip(), author.email.strip().lower()

        # Fall back to original even if alias (better than catchall)
        if _ok(addr) or (addr and addr not in bad and not addr.endswith("@example.com")):
            return name, addr

        return "", ""
