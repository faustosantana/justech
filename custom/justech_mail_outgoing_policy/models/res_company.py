# -*- coding: utf-8 -*-
import json
import logging
from email.utils import parseaddr

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)

# Seed policies keyed by domain. Extend via ICP `justech_mail.company_policies`.
# Domains must stay aligned with each company's mail.alias_domain.
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
            "customer-care@justech.do",
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
            "customer-care@just-offices.com",
        ],
        "catchall_addrs": ["catchall@just-offices.com"],
    },
    {
        "name": "PlugSafe",
        "domains": ["plugsafeservices.com"],
        "force_from": "Notificaciones PlugSafe <ventas@plugsafeservices.com>",
        "shared_aliases": [
            "info@plugsafeservices.com",
            "ventas@plugsafeservices.com",
            "noreply@plugsafeservices.com",
        ],
        "catchall_addrs": ["catchall@plugsafeservices.com"],
    },
    {
        "name": "Omni",
        "domains": ["solutionsomni.com"],
        "force_from": "Notificaciones Omni <info@solutionsomni.com>",
        "shared_aliases": [
            "info@solutionsomni.com",
            "noreply@solutionsomni.com",
        ],
        "catchall_addrs": ["catchall@solutionsomni.com"],
    },
]


def justech_load_company_policies(env):
    """Load company mail policies from ICP JSON or defaults (+ legacy merge)."""
    ICP = env["ir.config_parameter"].sudo()
    raw = (ICP.get_param("justech_mail.company_policies") or "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list) and data:
                return [p for p in data if isinstance(p, dict) and p.get("force_from")]
        except json.JSONDecodeError:
            _logger.warning("justech_mail.company_policies is not valid JSON; using defaults")

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
                    "customer-care@justech.do",
                ],
                "catchall_addrs": ["catchall@justech.do"],
            }
        ]
        for default in _DEFAULT_COMPANY_POLICIES:
            if set(default.get("domains") or []) - covered:
                policies.append(default)
        return policies

    return list(_DEFAULT_COMPANY_POLICIES)


class ResCompany(models.Model):
    _inherit = "res.company"

    justech_mail_notification_from = fields.Char(
        string="Mail notification From",
        compute="_compute_justech_mail_identity_fields",
    )
    justech_mail_domain = fields.Char(
        string="Mail identity domain",
        compute="_compute_justech_mail_identity_fields",
    )

    @api.depends(
        "name",
        "email",
        "alias_domain_id",
        "alias_domain_id.name",
        "partner_id.email",
    )
    def _compute_justech_mail_identity_fields(self):
        for company in self:
            identity = company._get_company_mail_identity()
            company.justech_mail_notification_from = identity.get("email_from") or False
            company.justech_mail_domain = identity.get("domain") or False

    def _justech_company_domains(self):
        """Domains owned by this company (alias_domain first, then email)."""
        self.ensure_one()
        domains = set()
        if self.alias_domain_id and self.alias_domain_id.name:
            domains.add(self.alias_domain_id.name.strip().lower())
        for value in (self.email, self.partner_id.email if self.partner_id else False):
            _, addr = parseaddr(value or "")
            addr = (addr or "").lower()
            if addr and "@" in addr:
                domains.add(addr.rsplit("@", 1)[-1])
        return domains

    def _justech_match_policy(self, policies=None):
        """Match policy by this company's domains — never by env.company."""
        self.ensure_one()
        policies = policies if policies is not None else justech_load_company_policies(self.env)
        company_domains = self._justech_company_domains()
        for policy in policies:
            policy_domains = {d.lower() for d in (policy.get("domains") or [])}
            if company_domains & policy_domains:
                return policy
        # Synthesize a minimal policy from the company's own alias domain / email
        domain = next(iter(company_domains), False)
        if not domain:
            return False
        display = (self.name or "Company").strip()
        email = False
        if self.email:
            email = (parseaddr(self.email)[1] or "").lower()
        if not email:
            email = f"noreply@{domain}"
        return {
            "name": display,
            "domains": [domain],
            "force_from": tools.formataddr((f"Notificaciones {display}", email)),
            "shared_aliases": [email] if email else [],
            "catchall_addrs": [f"catchall@{domain}"],
        }

    def _get_company_mail_identity(self, reply_user=None):
        """Single source of truth for outgoing mail identity of this company.

        Returns dict:
          company_id, display_name, domain, email_from, reply_to,
          alias_domain_id, logo, layout_company, smtp_domain,
          allowed_domains, shared_aliases, policy
        """
        self.ensure_one()
        policy = self._justech_match_policy() or {}
        domains = self._justech_company_domains()
        for d in policy.get("domains") or []:
            if d:
                domains.add(d.lower())
        domain = (
            (self.alias_domain_id.name or "").strip().lower()
            or (next(iter(domains), "") if domains else "")
        )
        email_from = (policy.get("force_from") or "").strip()
        if not email_from and self.email:
            email_from = self.email_formatted or tools.formataddr((self.name or "", self.email))
        if not email_from and domain:
            email_from = tools.formataddr(
                (f"Notificaciones {self.name or ''}".strip(), f"noreply@{domain}")
            )

        reply_to = False
        if reply_user and reply_user.partner_id and reply_user.partner_id.email:
            reply_to = tools.formataddr(
                (
                    (reply_user.partner_id.name or "").strip(),
                    reply_user.partner_id.email.strip(),
                )
            )

        smtp_domain = domain
        return {
            "company_id": self.id,
            "display_name": self.name,
            "domain": domain,
            "email_from": email_from,
            "reply_to": reply_to,
            "alias_domain_id": self.alias_domain_id,
            "logo": self.logo,
            "layout_company": self,
            "smtp_domain": smtp_domain,
            "allowed_domains": sorted(domains),
            "shared_aliases": list(policy.get("shared_aliases") or []),
            "policy": policy,
        }
