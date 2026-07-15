# -*- coding: utf-8 -*-
import json
import logging
from email.utils import parseaddr

from odoo import models, tools

_logger = logging.getLogger(__name__)

# Default multi-company policies (no hardcoded branch logic beyond this seed).
# Extend via ir.config_parameter `justech_mail.company_policies` (JSON).
_DEFAULT_COMPANY_POLICIES = [
    {
        "name": "JUSTECH",
        "domains": ["justech.do"],
        "force_from": "Notificaciones Justech <notifications@justech.do>",
        "shared_aliases": [
            "asistencia@justech.do",
            "info@justech.do",
            "noreply@justech.do",
            "notifications@justech.do",
        ],
        "catchall_addrs": ["catchall@justech.do"],
    },
    {
        "name": "Just Office",
        "domains": ["just-offices.com"],
        "force_from": "Notificaciones Just Office <notificaciones@just-offices.com>",
        "shared_aliases": [
            "info@just-offices.com",
            "noreply@just-offices.com",
            "notificaciones@just-offices.com",
        ],
        "catchall_addrs": ["catchall@just-offices.com"],
    },
]


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
        """Force company notifications From + human Reply-To.

        Microsoft 365 rejects Send-As when SMTP auth mailbox differs from From.
        Company policies are data-driven so Plug Safe / Omni can be added later
        without code changes.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("justech_mail.outgoing_policy_enabled", "True").lower() in ("0", "false", "no"):
            return

        policies = self._justech_get_company_policies()
        if not policies:
            return

        for mail in self:
            if not mail.exists():
                continue
            policy = mail._justech_select_policy(policies)
            if not policy:
                continue

            force_from = (policy.get("force_from") or "").strip()
            if not force_from:
                continue
            force_addr = (parseaddr(force_from)[1] or "").lower()
            if not force_addr:
                continue

            msg = mail.mail_message_id
            original_from = (mail.email_from or (msg.email_from if msg else "") or "").strip()

            reply_name, reply_addr = mail._justech_resolve_reply_to(original_from, policy)
            if not reply_addr:
                # Company-local fallback only (never cross-company)
                reply_addr = mail._justech_company_fallback_email(policy) or force_addr
            reply_to = tools.formataddr((reply_name or "", reply_addr)) if reply_addr else force_from

            write_vals = {
                "email_from": force_from,
                "reply_to": reply_to,
            }
            if msg and "reply_to_force_new" in msg._fields:
                write_vals["reply_to_force_new"] = True
            mail.write(write_vals)

    def _justech_get_company_policies(self):
        """Load policies from JSON param; fall back to legacy keys / defaults."""
        ICP = self.env["ir.config_parameter"].sudo()
        raw = (ICP.get_param("justech_mail.company_policies") or "").strip()
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, list) and data:
                    return [p for p in data if isinstance(p, dict) and p.get("force_from")]
            except json.JSONDecodeError:
                _logger.warning("justech_mail.company_policies is not valid JSON; using defaults")

        # Legacy single-company params (Justech) remain supported
        legacy_from = (
            ICP.get_param(
                "justech_mail.force_from",
                "Notificaciones Justech <notifications@justech.do>",
            )
            or ""
        ).strip()
        legacy_domains = [
            d.strip().lower()
            for d in (ICP.get_param("justech_mail.apply_domains", "justech.do") or "").split(",")
            if d.strip()
        ]
        if legacy_from and legacy_domains:
            # Merge: legacy Justech + any default policies whose domains are not covered
            covered = set(legacy_domains)
            policies = [
                {
                    "name": "legacy",
                    "domains": legacy_domains,
                    "force_from": legacy_from,
                    "shared_aliases": [
                        "asistencia@justech.do",
                        "info@justech.do",
                        "noreply@justech.do",
                        "notifications@justech.do",
                    ],
                    "catchall_addrs": ["catchall@justech.do"],
                }
            ]
            for default in _DEFAULT_COMPANY_POLICIES:
                if set(default.get("domains") or []) - covered:
                    policies.append(default)
            return policies

        return list(_DEFAULT_COMPANY_POLICIES)

    def _justech_select_policy(self, policies):
        """Pick the policy for this mail without cross-company leakage."""
        self.ensure_one()
        msg = self.mail_message_id

        # 1) Explicit company on the message
        company = self.record_company_id
        if company:
            policy = self._justech_match_policy_for_company(company, policies)
            if policy:
                return policy

        # 2) Document company_id when model/res_id are set
        if self.model and self.res_id and self.model in self.env:
            try:
                record = self.env[self.model].sudo().browse(self.res_id)
                if record.exists() and "company_id" in record._fields and record.company_id:
                    policy = self._justech_match_policy_for_company(record.company_id, policies)
                    if policy:
                        return policy
            except Exception:  # noqa: BLE001 — never block send on lookup errors
                _logger.debug("company lookup failed for %s,%s", self.model, self.res_id, exc_info=True)

        # 3) Alias domain on the message
        alias_domain = False
        if msg and msg.record_alias_domain_id:
            alias_domain = (msg.record_alias_domain_id.name or "").strip().lower()
        if alias_domain:
            for policy in policies:
                if alias_domain in {d.lower() for d in (policy.get("domains") or [])}:
                    return policy

        # 4) Original From domain
        original_from = (self.email_from or (msg.email_from if msg else "") or "").strip()
        _, original_addr = parseaddr(original_from)
        original_addr = (original_addr or "").lower()
        if original_addr and "@" in original_addr:
            domain = original_addr.rsplit("@", 1)[-1]
            for policy in policies:
                if domain in {d.lower() for d in (policy.get("domains") or [])}:
                    return policy
            force_addrs = {
                (parseaddr(p.get("force_from") or "")[1] or "").lower()
                for p in policies
            }
            if original_addr in force_addrs:
                for policy in policies:
                    if (parseaddr(policy.get("force_from") or "")[1] or "").lower() == original_addr:
                        return policy

        # 5) Triggering user's email domain (same as previous Justech behaviour)
        if self.create_uid and self.create_uid.partner_id and self.create_uid.partner_id.email:
            uid_email = self.create_uid.partner_id.email.strip().lower()
            if "@" in uid_email:
                uid_domain = uid_email.rsplit("@", 1)[-1]
                matches = [
                    p for p in policies
                    if uid_domain in {d.lower() for d in (p.get("domains") or [])}
                ]
                if len(matches) == 1:
                    return matches[0]

        return False

    def _justech_match_policy_for_company(self, company, policies):
        """Match company email / website domain to a policy."""
        candidates = []
        for field_name in ("email", "catchall_email", "bounce_email"):
            if field_name in company._fields and company[field_name]:
                candidates.append(company[field_name])
        if company.partner_id and company.partner_id.email:
            candidates.append(company.partner_id.email)

        for value in candidates:
            _, addr = parseaddr(value or "")
            addr = (addr or "").lower()
            if addr and "@" in addr:
                domain = addr.rsplit("@", 1)[-1]
                for policy in policies:
                    if domain in {d.lower() for d in (policy.get("domains") or [])}:
                        return policy
        return False

    def _justech_company_fallback_email(self, policy):
        """Fallback Reply-To: company email matching policy domains, else force_from."""
        self.ensure_one()
        domains = {d.lower() for d in (policy.get("domains") or [])}
        company = self.record_company_id
        if not company and self.model and self.res_id and self.model in self.env:
            try:
                record = self.env[self.model].sudo().browse(self.res_id)
                if record.exists() and "company_id" in record._fields:
                    company = record.company_id
            except Exception:  # noqa: BLE001
                company = False
        if company and company.email:
            _, addr = parseaddr(company.email)
            addr = (addr or "").lower()
            if addr and "@" in addr and addr.rsplit("@", 1)[-1] in domains:
                return addr
        return (parseaddr(policy.get("force_from") or "")[1] or "").lower() or False

    def _justech_resolve_reply_to(self, original_from, policy):
        """Reply-To = human who generated the action (never OdooBot/catchall)."""
        self.ensure_one()
        force_addr = (parseaddr(policy.get("force_from") or "")[1] or "").lower()
        bad = {
            "",
            force_addr,
            "odoobot@example.com",
            "admin@example.com",
        }
        bad.update({(a or "").lower() for a in (policy.get("catchall_addrs") or [])})
        # Never use another company's force_from / catchall as Reply-To
        for other in self._justech_get_company_policies():
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
