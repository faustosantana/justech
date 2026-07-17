# -*- coding: utf-8 -*-
import logging

from odoo import api, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    @api.constrains("alias_id", "company_id")
    def _check_justech_alias_matches_company(self):
        for team in self:
            if not team.company_id or not team.alias_id:
                continue
            company_domain = team.company_id.alias_domain_id
            alias_domain = team.alias_id.alias_domain_id
            if company_domain and alias_domain and company_domain != alias_domain:
                raise ValidationError(
                    _(
                        "Helpdesk team «%(team)s» alias domain %(alias)s does not match "
                        "company %(company)s domain %(expected)s. "
                        "Document company_id is the source of truth for mail identity."
                    )
                    % {
                        "team": team.display_name,
                        "alias": alias_domain.name,
                        "company": team.company_id.display_name,
                        "expected": company_domain.name,
                    }
                )

    def _justech_align_alias_domain(self):
        """Align team alias_domain_id to company.alias_domain_id (idempotent)."""
        for team in self:
            if not team.company_id or not team.company_id.alias_domain_id or not team.alias_id:
                continue
            expected = team.company_id.alias_domain_id
            if team.alias_id.alias_domain_id != expected:
                _logger.info(
                    "Aligning helpdesk.team id=%s alias_domain %s → %s",
                    team.id,
                    team.alias_id.alias_domain_id.name if team.alias_id.alias_domain_id else None,
                    expected.name,
                )
                team.alias_id.sudo().write({"alias_domain_id": expected.id})
