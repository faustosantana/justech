# -*- coding: utf-8 -*-
import logging
from email.utils import parseaddr

from odoo import models, tools

from .res_company import justech_load_company_policies

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = "mail.mail"

    def send(self, auto_commit=False, raise_exception=False, post_send_callback=None):
        if not self.env.context.get("justech_mail_skip_outgoing_policy"):
            self._justech_apply_outgoing_policy()
        # Drop mails blocked by cross-company identity validation
        to_send = self.filtered(lambda m: m.state != "cancel")
        blocked = self - to_send
        if blocked:
            _logger.warning(
                "justech_mail_outgoing_policy: blocked %s mail(s) (cross-company identity)",
                len(blocked),
            )
        if not to_send:
            return True
        return super(MailMail, to_send).send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            post_send_callback=post_send_callback,
        )

    def _justech_resolve_document_company(self):
        """Document company_id is the only source of truth — never env.company."""
        self.ensure_one()
        if self.record_company_id:
            return self.record_company_id
        if self.model and self.res_id and self.model in self.env:
            try:
                record = self.env[self.model].sudo().browse(self.res_id)
                if record.exists() and "company_id" in record._fields and record.company_id:
                    return record.company_id
            except Exception:  # noqa: BLE001
                _logger.debug(
                    "company lookup failed for %s,%s",
                    self.model,
                    self.res_id,
                    exc_info=True,
                )
        return self.env["res.company"]

    def _justech_foreign_domain(self, addr_domain, company, all_policies):
        """True if addr_domain belongs to another company's policy domains."""
        if not addr_domain or not company:
            return False
        allowed = set(company._get_company_mail_identity().get("allowed_domains") or [])
        if addr_domain in allowed:
            return False
        foreign = set()
        for policy in all_policies:
            for d in policy.get("domains") or []:
                foreign.add(d.lower())
        foreign -= allowed
        return addr_domain in foreign

    def _justech_block_mail(self, reason):
        self.ensure_one()
        _logger.warning(
            "justech_mail_outgoing_policy BLOCK mail_id=%s model=%s res_id=%s: %s",
            self.id,
            self.model,
            self.res_id,
            reason,
        )
        vals = {
            "state": "cancel",
            "failure_reason": reason[:1024] if reason else "cross-company mail identity",
        }
        # failure_type exists on mail.mail in recent Odoo
        if "failure_type" in self._fields:
            vals["failure_type"] = "unknown"
        self.write(vals)

    def _justech_apply_outgoing_policy(self):
        """Force company notifications From + human Reply-To (company-first)."""
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("justech_mail.outgoing_policy_enabled", "True").lower() in (
            "0",
            "false",
            "no",
        ):
            return

        all_policies = justech_load_company_policies(self.env)

        for mail in self:
            if not mail.exists():
                continue

            company = mail._justech_resolve_document_company()
            if not company:
                # No document company → do not invent identity from env.company / alias
                continue

            identity = company._get_company_mail_identity(reply_user=mail.create_uid)
            policy = identity.get("policy") or {}
            force_from = (identity.get("email_from") or "").strip()
            if not force_from:
                continue
            force_addr = (parseaddr(force_from)[1] or "").lower()
            if not force_addr:
                continue

            msg = mail.mail_message_id
            original_from = (mail.email_from or (msg.email_from if msg else "") or "").strip()
            _, original_addr = parseaddr(original_from)
            original_addr = (original_addr or "").lower()
            original_domain = (
                original_addr.rsplit("@", 1)[-1] if original_addr and "@" in original_addr else ""
            )

            # Helpdesk: block when team alias belongs to another company
            if mail.model == "helpdesk.ticket" and mail.res_id and "helpdesk.ticket" in mail.env:
                ticket = mail.env["helpdesk.ticket"].sudo().browse(mail.res_id)
                if ticket.exists() and ticket.team_id and ticket.team_id.alias_id:
                    team = ticket.team_id
                    team_domain = (
                        (team.alias_id.alias_domain_id.name or "").strip().lower()
                        if team.alias_id.alias_domain_id
                        else ""
                    )
                    company_domain = (identity.get("domain") or "").strip().lower()
                    if team_domain and company_domain and team_domain != company_domain:
                        mail._justech_block_mail(
                            "Helpdesk team alias domain %r != company domain %r "
                            "(team_id=%s company_id=%s)"
                            % (team_domain, company_domain, team.id, company.id)
                        )
                        continue

            # Warn on foreign From domain, then company-first rewrite (document wins)
            if mail._justech_foreign_domain(original_domain, company, all_policies):
                _logger.warning(
                    "justech_mail_outgoing_policy: rewriting foreign From domain %r → company %s (%s)",
                    original_domain,
                    company.name,
                    force_from,
                )

            reply_name, reply_addr = mail._justech_resolve_reply_to(original_from, policy, company)
            if not reply_addr:
                reply_addr = mail._justech_company_fallback_email(policy, company) or force_addr
            reply_to = tools.formataddr((reply_name or "", reply_addr)) if reply_addr else force_from

            write_vals = {
                "email_from": force_from,
                "reply_to": reply_to,
            }
            if msg and "reply_to_force_new" in msg._fields:
                write_vals["reply_to_force_new"] = True
            # Keep record_company_id aligned with document company
            if "record_company_id" in mail._fields and mail.record_company_id != company:
                write_vals["record_company_id"] = company.id
            mail.write(write_vals)

    def _justech_company_fallback_email(self, policy, company=None):
        self.ensure_one()
        domains = {d.lower() for d in (policy.get("domains") or [])}
        company = company or self._justech_resolve_document_company()
        if company and company.email:
            _, addr = parseaddr(company.email)
            addr = (addr or "").lower()
            if addr and "@" in addr and addr.rsplit("@", 1)[-1] in domains:
                return addr
        return (parseaddr(policy.get("force_from") or "")[1] or "").lower() or False

    def _justech_resolve_reply_to(self, original_from, policy, company=None):
        """Reply-To = human who generated the action (never OdooBot/catchall/other company)."""
        self.ensure_one()
        force_addr = (parseaddr(policy.get("force_from") or "")[1] or "").lower()
        bad = {
            "",
            force_addr,
            "odoobot@example.com",
            "admin@example.com",
        }
        bad.update({(a or "").lower() for a in (policy.get("catchall_addrs") or [])})
        for other in justech_load_company_policies(self.env):
            other_force = (parseaddr(other.get("force_from") or "")[1] or "").lower()
            if other_force:
                bad.add(other_force)
            bad.update({(a or "").lower() for a in (other.get("catchall_addrs") or [])})

        shared_aliases = {(a or "").lower() for a in (policy.get("shared_aliases") or [])}

        name, addr = parseaddr(original_from or "")
        name = (name or "").strip()
        addr = (addr or "").strip().lower()

        def _ok(candidate):
            c = (candidate or "").strip().lower()
            return bool(c) and c not in bad and not c.endswith("@example.com")

        # Prefer personal mailbox from original From when not a shared alias
        if _ok(addr) and addr not in shared_aliases:
            return name, addr

        user = self.create_uid
        if user and user.partner_id and _ok(user.partner_id.email):
            return (user.partner_id.name or "").strip(), user.partner_id.email.strip().lower()

        author = self.author_id or (self.mail_message_id.author_id if self.mail_message_id else False)
        if author and _ok(author.email):
            return (author.name or "").strip(), author.email.strip().lower()

        if _ok(addr) or (addr and addr not in bad and not addr.endswith("@example.com")):
            return name, addr

        return "", ""
